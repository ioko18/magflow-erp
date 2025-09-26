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
from typing import Dict, Tuple

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

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
RATE_LIMITS: Dict[str, Tuple[int, int]] = {
    "default": (10, 60),  # 10 requests / 60 seconds
    "auth": (5, 60),  # 5 requests / 60 seconds
    "read": (20, 60),  # 20 requests / 60 seconds
    "health": (5, 60),  # Allow fewer health checks when enabled
}

# Path prefix mapping to a named rate limit
PATH_RATE_LIMITS: Dict[str, str] = {
    "/api/v1/auth/": "auth",
    "/api/v1/products": "read",
    "/api/v1/health/": "health",
    # Test-specific paths
    "/api/v1/test/auth": "auth",
    "/api/v1/test/read": "read",
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
    if path.startswith("/metrics"):
        return False

    return True


def _get_counter_key(path: str, window_seconds: int) -> str:
    # One counter per named key and rounded time window
    name = get_rate_limit_key_for_path(path)
    window_start = int(time.time() // window_seconds) * window_seconds
    return f"{name}:{window_start}"


def init_rate_limiter(app: FastAPI, *, rate_limit_health: bool = False) -> None:
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
        counter_key = _get_counter_key(request.url.path, window_seconds)

        # Get current count
        counters: Dict[str, int] = app.state._rate_limit_counters
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
    """A minimal no-op async rate limiter for testing.

    Provides an `acquire()` coroutine compatible with production interfaces.
    """

    def __init__(
        self,
        limit: int | None = None,
        window_seconds: int | None = None,
    ) -> None:
        self.limit = limit or RATE_LIMITS["default"][0]
        self.window_seconds = window_seconds or RATE_LIMITS["default"][1]

    async def acquire(self) -> None:
        # No-op in tests; real implementation would coordinate with Redis
        return None


_default_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    global _default_rate_limiter
    if _default_rate_limiter is None:
        _default_rate_limiter = RateLimiter()
    return _default_rate_limiter
