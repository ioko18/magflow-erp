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
    "auth": (5, 60),      # 5 requests / 60 seconds
    "read": (20, 60),     # 20 requests / 60 seconds
}

# Path prefix mapping to a named rate limit
PATH_RATE_LIMITS: Dict[str, str] = {
    "/api/v1/auth/": "auth",
    "/api/v1/products": "read",
    # Test-specific paths
    "/api/v1/test/auth": "auth",
    "/api/v1/test/read": "read",
}


def get_rate_limit_key_for_path(path: str) -> str:
    for prefix, key in PATH_RATE_LIMITS.items():
        if path.startswith(prefix):
            return key
    return "default"


def should_rate_limit(request: Request) -> bool:
    path = request.url.path
    # Exact or prefix match for excluded health endpoints
    if path in EXCLUDED_PATHS:
        return False
    if path.startswith("/health/"):
        return False
    # Exclude any route that contains '/health' (covers /api/v1/health/* as well)
    if "/health" in path:
        return False
    return True


def _get_counter_key(path: str, window_seconds: int) -> str:
    # One counter per named key and rounded time window
    name = get_rate_limit_key_for_path(path)
    window_start = int(time.time() // window_seconds) * window_seconds
    return f"{name}:{window_start}"


def init_rate_limiter(app: FastAPI) -> None:
    if not hasattr(app.state, "_rate_limit_counters"):
        app.state._rate_limit_counters = {}

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        # Skip excluded paths
        if not should_rate_limit(request):
            response: Response = await call_next(request)
            # Explicitly ensure no rate limit headers for excluded paths
            response.headers.pop("X-RateLimit-Limit", None)
            response.headers.pop("X-RateLimit-Remaining", None)
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
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too Many Requests",
                    "rate_limit": key_name,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        # Increment count and proceed
        counters[counter_key] = count + 1
        response: Response = await call_next(request)
        # Attach headers
        remaining = max(0, limit - counters[counter_key])
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    return None


# Minimal async rate limiter used by services during tests
class RateLimiter:
    """A minimal no-op async rate limiter for testing.

    Provides an `acquire()` coroutine compatible with production interfaces.
    """

    def __init__(self, limit: int | None = None, window_seconds: int | None = None) -> None:
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
