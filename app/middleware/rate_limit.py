"""Rate limiting middleware for FastAPI.

This module provides rate limiting functionality based on IP address
and configurable limits per endpoint or globally.
"""

import asyncio
import time
from collections import defaultdict
from typing import Dict, Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

print("[RATE LIMIT] Middleware module loaded")  # Debug print


class RateLimiter:
    """In-memory rate limiter using sliding window algorithm.

    For production use, consider Redis-based rate limiting for distributed systems.
    """

    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
        self.cleanup_task: Optional[asyncio.Task] = None

    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """Check if request is allowed based on rate limit.

        Args:
            key: Unique identifier (e.g., IP address)
            limit: Maximum requests allowed in window
            window: Time window in seconds

        Returns:
            bool: True if request is allowed, False if rate limited

        """
        now = time.time()
        window_start = now - window

        # Remove old requests outside the window
        self.requests[key] = [
            req_time for req_time in self.requests[key] if req_time > window_start
        ]

        # Check if under limit
        if len(self.requests[key]) < limit:
            self.requests[key].append(now)
            return True

        return False

    def get_remaining_requests(self, key: str, limit: int, window: int) -> int:
        """Get remaining requests allowed in current window."""
        now = time.time()
        window_start = now - window

        # Clean old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key] if req_time > window_start
        ]

        return max(0, limit - len(self.requests[key]))

    def get_reset_time(self, key: str, window: int) -> float:
        """Get time until rate limit resets."""
        if not self.requests[key]:
            return 0

        now = time.time()
        oldest_request = min(self.requests[key])
        reset_time = (oldest_request + window) - now
        return max(0, reset_time)


# Global rate limiter instance
rate_limiter = RateLimiter()


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request.

    Checks X-Forwarded-For header first (for proxies/load balancers),
    then falls back to direct client IP.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take first IP if multiple are present
        return forwarded_for.split(",")[0].strip()

    return request.client.host if request.client else "unknown"


def should_skip_rate_limit(request: Request) -> bool:
    """Determine if rate limiting should be skipped for this request.

    Skip rate limiting for:
    - Health check endpoints
    - Static assets
    - Admin endpoints (if configured)
    """
    path = request.url.path

    # Skip health checks
    if path.startswith("/health") or path.startswith("/api/v1/health"):
        return True

    # Skip metrics endpoints
    if path.startswith("/metrics"):
        return True

    # Skip OpenAPI docs in development
    if settings.APP_ENV == "development" and (
        path.startswith("/docs") or path.startswith("/openapi")
    ):
        return True

    return False


async def rate_limit_middleware(request: Request, call_next):
    """FastAPI middleware for rate limiting.

    Applies rate limiting based on client IP address with configurable limits.
    """
    print(f"[RATE LIMIT] Checking {request.method} {request.url.path}")  # Debug print

    # Skip rate limiting for certain endpoints
    if should_skip_rate_limit(request):
        print(f"[RATE LIMIT] Skipping {request.url.path}")  # Debug print
        return await call_next(request)

    client_ip = get_client_ip(request)

    # Use different limits for different endpoint types
    path = request.url.path
    if path.startswith("/api/v1/auth"):
        # Stricter limits for auth endpoints
        limit = 10  # 10 requests per window
        window = 60  # 1 minute window
    elif path.startswith("/api/v1/admin"):
        # Stricter limits for admin endpoints
        limit = 30  # 30 requests per window
        window = 60  # 1 minute window
    else:
        # Default limits for other endpoints
        limit = settings.RATE_LIMIT_PER_WINDOW
        window = settings.RATE_LIMIT_WINDOW

    # Check rate limit
    if not rate_limiter.is_allowed(client_ip, limit, window):
        reset_time = rate_limiter.get_reset_time(client_ip, window)

        logger.warning(
            f"Rate limit exceeded for IP {client_ip} on {request.method} {path}",
        )

        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Too Many Requests",
                "message": "Rate limit exceeded. Please try again later.",
                "retry_after": int(reset_time),
                "limit": limit,
                "window_seconds": window,
            },
            headers={
                "Retry-After": str(int(reset_time)),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time() + reset_time)),
            },
        )

    # Get remaining requests for response headers
    remaining = rate_limiter.get_remaining_requests(client_ip, limit, window)
    reset_time = rate_limiter.get_reset_time(client_ip, window)

    # Call next middleware/endpoint
    response = await call_next(request)

    # Add rate limit headers to response
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(int(time.time() + reset_time))

    return response
