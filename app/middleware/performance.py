"""
Performance Monitoring Middleware

Tracks request performance and identifies slow endpoints.
"""

import contextlib
import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.cache import get_redis
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware to monitor request performance."""

    def __init__(self, app, slow_request_threshold: float = 1.0):
        """
        Initialize performance monitoring middleware.

        Args:
            app: FastAPI application
            slow_request_threshold: Threshold in seconds for slow requests
        """
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold
        self._redis = None

    async def _get_redis(self):
        """Get Redis client lazily."""
        if self._redis is None:
            with contextlib.suppress(Exception):
                self._redis = await get_redis()
        return self._redis

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and track performance.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Add performance header
        response.headers["X-Process-Time"] = str(duration)

        # Log slow requests
        if duration > self.slow_request_threshold:
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path} "
                f"took {duration:.2f}s"
            )

        # Track metrics in Redis
        await self._track_metrics(
            method=request.method,
            path=request.url.path,
            duration=duration,
            status_code=response.status_code,
        )

        return response

    async def _track_metrics(
        self, method: str, path: str, duration: float, status_code: int
    ):
        """
        Track request metrics in Redis.

        Args:
            method: HTTP method
            path: Request path
            duration: Request duration
            status_code: Response status code
        """
        try:
            redis = await self._get_redis()
            if not redis:
                return

            # Create metric key
            endpoint_key = f"{method}:{path}"

            # Track request count
            await redis.incr(f"metrics:requests:{endpoint_key}")

            # Track total duration (for average calculation)
            await redis.incrbyfloat(f"metrics:duration:{endpoint_key}", duration)

            # Track status codes
            await redis.incr(f"metrics:status:{status_code}")

            # Track slow requests
            if duration > self.slow_request_threshold:
                await redis.incr(f"metrics:slow:{endpoint_key}")

            # Set expiry (keep metrics for 24 hours)
            await redis.expire(f"metrics:requests:{endpoint_key}", 86400)
            await redis.expire(f"metrics:duration:{endpoint_key}", 86400)
            await redis.expire(f"metrics:slow:{endpoint_key}", 86400)

        except Exception as e:
            # Don't fail the request if metrics tracking fails
            logger.debug(f"Failed to track metrics: {e}")

    async def get_endpoint_stats(self, method: str, path: str) -> dict:
        """
        Get statistics for a specific endpoint.

        Args:
            method: HTTP method
            path: Request path

        Returns:
            Dictionary with endpoint statistics
        """
        try:
            redis = await self._get_redis()
            if not redis:
                return {}

            endpoint_key = f"{method}:{path}"

            # Get metrics
            request_count = await redis.get(f"metrics:requests:{endpoint_key}")
            total_duration = await redis.get(f"metrics:duration:{endpoint_key}")
            slow_count = await redis.get(f"metrics:slow:{endpoint_key}")

            request_count = int(request_count) if request_count else 0
            total_duration = float(total_duration) if total_duration else 0.0
            slow_count = int(slow_count) if slow_count else 0

            avg_duration = total_duration / request_count if request_count > 0 else 0.0

            return {
                "endpoint": endpoint_key,
                "request_count": request_count,
                "avg_duration": round(avg_duration, 3),
                "slow_requests": slow_count,
                "slow_percentage": (
                    round((slow_count / request_count) * 100, 2)
                    if request_count > 0
                    else 0.0
                ),
            }

        except Exception as e:
            logger.error(f"Failed to get endpoint stats: {e}")
            return {}
