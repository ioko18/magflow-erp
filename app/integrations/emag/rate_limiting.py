"""Rate limiting utilities for the eMAG API.

This module provides rate limiting functionality to ensure we stay within the eMAG API rate limits.
"""

import asyncio
import logging
import time

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """A rate limiter that enforces rate limits for the eMAG API.

    The eMAG API has the following rate limits:
    - Orders: ≤ 12 req/s (720/min)
    - Other resources: ≤ 3 req/s (180/min)
    """

    def __init__(self, requests_per_second: float = 3.0):
        """Initialize the rate limiter.

        Args:
            requests_per_second: Maximum number of requests per second

        """
        self.rate = requests_per_second
        self.tokens = self.rate
        self.updated_at = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire a token from the rate limiter.

        This will block until a token is available.
        """
        async with self.lock:
            now = time.monotonic()
            time_passed = now - self.updated_at
            self.updated_at = now

            # Add tokens based on time passed
            self.tokens += time_passed * self.rate

            # Cap tokens at the rate limit
            self.tokens = min(self.tokens, self.rate)

            # If no tokens available, wait until one is available
            if self.tokens < 1.0:
                sleep_time = (1.0 - self.tokens) / self.rate
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                self.tokens = 0.0
            else:
                self.tokens -= 1.0

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass


# Global rate limiters
DEFAULT_RATE_LIMITER = RateLimiter(requests_per_second=3.0)
ORDERS_RATE_LIMITER = RateLimiter(requests_per_second=12.0)


def get_rate_limiter(resource_type: str = "default") -> RateLimiter:
    """Get the appropriate rate limiter for the given resource type.

    Args:
        resource_type: Type of resource being accessed (e.g., 'orders')

    Returns:
        RateLimiter: The appropriate rate limiter

    """
    if resource_type.lower() == "orders":
        return ORDERS_RATE_LIMITER
    return DEFAULT_RATE_LIMITER


def rate_limited(retry_errors: bool = True):
    """Decorator to apply rate limiting to a function.

    Args:
        retry_errors: Whether to retry on rate limit errors

    Returns:
        Decorated function with rate limiting

    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get the resource type from the function signature or use default
            resource_type = kwargs.pop("resource_type", "default")
            limiter = get_rate_limiter(resource_type)

            # Apply retry logic if enabled
            if retry_errors:

                @retry(
                    stop=stop_after_attempt(3),
                    wait=wait_exponential(multiplier=1, min=4, max=10),
                    retry=retry_if_exception_type((RateLimitError, ConnectionError)),
                    before_sleep=before_sleep_log(logger, logging.WARNING),
                )
                async def limited_func():
                    async with limiter:
                        return await func(*args, **kwargs)

                return await limited_func()
            async with limiter:
                return await func(*args, **kwargs)

        return wrapper

    return decorator


class RateLimitError(Exception):
    """Exception raised when rate limits are exceeded."""
