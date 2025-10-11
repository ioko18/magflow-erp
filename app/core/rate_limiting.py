"""Simple in-app rate limiting utilities used by tests.

This module provides a minimal, self-contained implementation to support
unit and integration tests without requiring a real Redis backend.

It exposes:
- EXCLUDED_PATHS: list[str]
- RATE_LIMITS: dict[str, tuple[int, int]]  (limit, window_seconds)
- PATH_RATE_LIMITS: dict[str, str]         (path prefix -> rate limit key)
- get_rate_limit_key_for_path(path: str) -> str
- should_rate_limit(request: fastapi.Request) -> bool
- init_rate_limiter(app: fastapi.FastAPI) -> None

The middleware installed by init_rate_limiter applies per-process counters
stored in app.state._rate_limit_counters, sufficient for tests driven
by FastAPI TestClient.
"""

from __future__ import annotations

import time

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.problem import Problem
from app.middleware.correlation_id import get_correlation_id

# Paths that should not be rate limited
EXCLUDED_PATHS = [
    "/health/live",
    "/health/ready",
    "/health/startup",
    "/health",  # generic health root if used
    "/metrics",
]

# Named rate limits: name -> (limit, window_seconds)
RATE_LIMITS: dict[str, tuple[int, int]] = {
    "default": (100, 60),  # 100 requests / 60 seconds - increased for development
    "auth": (50, 60),  # 50 requests / 60 seconds - increased for development
    "read": (200, 60),  # 200 requests / 60 seconds - increased for development
    "health": (100, 60),  # Allow more health checks
    "emag": (
        500,
        60,
    ),  # 500 requests / 60 seconds for eMAG endpoints - much higher for development
    "admin": (
        getattr(settings, "RATE_LIMIT_ADMIN_LIMIT", 1000),
        getattr(settings, "RATE_LIMIT_ADMIN_WINDOW", 60),
    ),
}

# Path prefix mapping to a named rate limit
PATH_RATE_LIMITS: dict[str, str] = {
    "/api/v1/auth/": "auth",
    "/api/v1/products": "read",
    "/api/v1/health/": "health",
    "/api/v1/emag/": "emag",  # Higher rate limit for eMAG endpoints
    # Test-specific paths
    "/api/v1/test/auth": "auth",
    "/api/v1/test/read": "read",
    "/api/v1/admin/": "admin",
}


def get_rate_limit_key_for_path(path: str) -> str:
    for prefix, key in PATH_RATE_LIMITS.items():
        if path.startswith(prefix):
            return key
    return "default"


def should_rate_limit(request: Request, *, rate_limit_health: bool) -> bool:
    path = request.url.path

    if not rate_limit_health:
        if path in EXCLUDED_PATHS:
            return False
        if path.startswith("/health/"):
            return False
        if "/health" in path:
            return False

    # Always skip metrics regardless of config
    return not path.startswith("/metrics")


def _get_counter_key(
    path: str, window_seconds: int, *, method: str | None = None
) -> str:
    """Return the counter key for a given request path within a window.

    Including both the resolved rate limit name and the concrete request path
    ensures endpoints that share the same rate limit group (for example, all
    admin endpoints) do not unintentionally consume each other's quota.
    """

    # One counter per named key, HTTP method, exact path and rounded window
    name = get_rate_limit_key_for_path(path)
    window_start = int(time.time() // window_seconds) * window_seconds
    method_part = (method or "").upper()
    safe_path = path.replace(":", "_")
    return f"{name}:{method_part}:{safe_path}:{window_start}"


def init_rate_limiter(app: FastAPI, *, rate_limit_health: bool = False) -> None:
    if not getattr(settings, "RATE_LIMIT_ENABLED", True):
        return
    if not hasattr(app.state, "_rate_limit_counters"):
        app.state._rate_limit_counters = {}
    app.state._rate_limit_health = rate_limit_health

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        # Skip excluded paths
        rate_limit_health_flag = getattr(app.state, "_rate_limit_health", False)
        if not should_rate_limit(request, rate_limit_health=rate_limit_health_flag):
            response: Response = await call_next(request)
            # Explicitly ensure no rate limit headers for excluded paths
            if "X-RateLimit-Limit" in response.headers:
                del response.headers["X-RateLimit-Limit"]
            if "X-RateLimit-Remaining" in response.headers:
                del response.headers["X-RateLimit-Remaining"]
            return response

        # Determine limit/window for the path
        key_name = get_rate_limit_key_for_path(request.url.path)
        limit, window_seconds = RATE_LIMITS.get(key_name, RATE_LIMITS["default"])
        counter_key = _get_counter_key(
            request.url.path,
            window_seconds,
            method=request.method,
        )

        # Get current count
        counters: dict[str, int] = app.state._rate_limit_counters
        count = counters.get(counter_key, 0)

        # If over limit, reject with 429 and Retry-After
        if count >= limit:
            retry_after = 1  # minimal value for tests; not strictly accurate
            correlation_id = get_correlation_id()
            problem = Problem.from_status(
                status_code=429,
                detail="Too many requests, please try again later.",
                instance=str(request.url),
                correlation_id=correlation_id,
            )
            problem.retry_after = retry_after
            problem_dict = problem.to_dict()

            headers = {
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
            }
            if correlation_id:
                headers["X-Correlation-ID"] = correlation_id

            return JSONResponse(
                status_code=429,
                content=problem_dict,
                headers=headers,
                media_type="application/problem+json",
            )

        # Increment count and proceed
        counters[counter_key] = count + 1
        response: Response = await call_next(request)
        # Attach headers
        remaining = max(0, limit - counters[counter_key])
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        correlation_id = get_correlation_id()
        if correlation_id and "X-Correlation-ID" not in response.headers:
            response.headers["X-Correlation-ID"] = correlation_id
        return response


# Minimal async rate limiter used by services during tests
class RateLimiter:
    """Compatibility wrapper mimicking fastapi_limiter's RateLimiter.
    Provides an async __call__ that does nothing, allowing existing code to await it.
    Also provides an async acquire() for compatibility.
    """

    def __init__(
        self,
        limit: int | None = None,
        window_seconds: int | None = None,
        *,
        times: int | None = None,
        seconds: int | None = None,
    ) -> None:
        # Compatibility: if times/seconds provided, use them as limit/window_seconds
        if times is not None:
            limit = times
        if seconds is not None:
            window_seconds = seconds
        self.limit = limit or RATE_LIMITS["default"][0]
        self.window_seconds = window_seconds or RATE_LIMITS["default"][1]

    async def acquire(self) -> None:
        """Legacy method kept for compatibility; does nothing."""
        return None

    async def __call__(self, request, response=None) -> None:
        """Async callable interface used in code; no-op implementation."""
        await self.acquire()
        return None


_default_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    global _default_rate_limiter
    if _default_rate_limiter is None:
        _default_rate_limiter = RateLimiter()
    return _default_rate_limiter
