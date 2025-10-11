"""Rate limiting implementation for eMAG API.

This module provides rate limiting functionality that respects eMAG's API rate limits:
- Orders: ≤ 12 req/s (720/min)
- Other resources: ≤ 3 req/s (180/min)

Features:
- Thread-safe implementation using asyncio.Lock
- Support for different rate limits per endpoint category
- Automatic rate limit reset after time window
- Metrics collection for monitoring
- Configurable retry behavior
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from ..exceptions import EmagRateLimitError

# Type aliases
# RateLimitMetrics = Dict[str, Dict[str, int]]  # Removed due to redefinition


logger = logging.getLogger(__name__)


@dataclass
class RateLimitMetrics:
    """Tracks metrics for rate limiting."""

    total_requests: int = 0
    rate_limited_requests: int = 0
    retry_attempts: int = 0
    errors: dict[str, int] = field(default_factory=lambda: defaultdict(int))


@dataclass
class RateLimit:
    """Represents a rate limit configuration.

    Attributes:
        max_requests: Maximum number of requests allowed in the time window
        per_seconds: Time window in seconds
        current_requests: Current number of requests in the window
        reset_time: Timestamp when the current window resets
        metrics: Track rate limiting metrics

    """

    max_requests: int  # Maximum number of requests
    per_seconds: int  # Time window in seconds
    current_requests: int = 0
    reset_time: float = 0.0
    metrics: RateLimitMetrics = field(default_factory=RateLimitMetrics)

    def is_exceeded(self) -> tuple[bool, float]:
        """Check if the rate limit has been exceeded.

        Returns:
            Tuple[bool, float]: (is_exceeded, retry_after_seconds)

        """
        now = time.time()
        if now > self.reset_time:
            self.current_requests = 0
            self.reset_time = now + self.per_seconds
            return False, 0.0

        remaining = self.max_requests - self.current_requests
        if remaining <= 0:
            retry_after = self.reset_time - now
            self.metrics.rate_limited_requests += 1
            return True, retry_after

        return False, 0.0

    def increment(self):
        """Increment the request counter and update metrics."""
        now = time.time()
        if now > self.reset_time:
            self.current_requests = 0
            self.reset_time = now + self.per_seconds
        self.current_requests += 1
        self.metrics.total_requests += 1

    def get_retry_after(self) -> float:
        """Get the number of seconds until the rate limit resets."""
        now = time.time()
        return max(0.0, self.reset_time - now)


class EmagRateLimiter:
    """Rate limiter for eMAG API that respects different rate limits for different endpoints.

    This class provides thread-safe rate limiting for eMAG API endpoints with different
    rate limits for different endpoint categories. It tracks metrics and provides
    detailed error information.

    Attributes:
        DEFAULT_RATE_LIMIT: Default rate limit for non-order endpoints (3 req/s)
        ORDER_RATE_LIMIT: Rate limit for order-related endpoints (12 req/s)
        ORDER_ENDPOINTS: Set of endpoint prefixes that should use the order rate limit

    """

    # Default rate limits (requests per second)
    DEFAULT_RATE_LIMIT = 3  # 3 req/s (180/min) for most endpoints
    ORDER_RATE_LIMIT = 12  # 12 req/s (720/min) for order-related endpoints

    # Default retry configuration
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 0.1  # 100ms initial delay

    # Endpoint patterns that have different rate limits
    ORDER_ENDPOINTS = {
        "order/",
        "orders/",
        "awb/",
        "shipment/",
        "rma/",
        "return/",
        "invoice/",
        "customer-invoice/",
    }

    def __init__(self, max_retries: int = None, retry_delay: float = None):
        """Initialize the rate limiter.

        Args:
            max_retries: Maximum number of retry attempts when rate limited
            retry_delay: Initial delay between retries in seconds

        """
        self.rate_limits: dict[str, RateLimit] = {}
        self.lock = asyncio.Lock()
        self.max_retries = max_retries or self.DEFAULT_MAX_RETRIES
        self.retry_delay = retry_delay or self.DEFAULT_RETRY_DELAY
        self.metrics = RateLimitMetrics()

        # Initialize rate limits
        self.rate_limits["default"] = RateLimit(
            max_requests=self.DEFAULT_RATE_LIMIT,
            per_seconds=1,  # Per-second rate limiting
            metrics=RateLimitMetrics(),
        )
        self.rate_limits["orders"] = RateLimit(
            max_requests=self.ORDER_RATE_LIMIT,
            per_seconds=1,  # Per-second rate limiting
            metrics=RateLimitMetrics(),
        )

    def _get_rate_limit_key(self, endpoint: str) -> str:
        """Get the rate limit key for the given endpoint.

        Args:
            endpoint: The API endpoint path

        Returns:
            str: The rate limit key ('orders' or 'default')

        Raises:
            ValueError: If the endpoint is empty or None

        """
        if not endpoint:
            raise ValueError("Endpoint cannot be empty")

        endpoint = endpoint.lower().strip("/")
        for order_endpoint in self.ORDER_ENDPOINTS:
            if endpoint.startswith(order_endpoint):
                return "orders"
        return "default"

    async def acquire(
        self,
        endpoint: str,
        max_retries: int | None = None,
        retry_delay: float | None = None,
    ) -> float:
        """Acquire a rate limit token for the given endpoint with retry logic.

        Args:
            endpoint: The API endpoint being called
            max_retries: Maximum number of retry attempts (overrides instance default)
            retry_delay: Initial delay between retries in seconds (overrides instance default)

        Returns:
            float: The number of seconds to wait before making the request (0 if no wait needed)

        Raises:
            EmagRateLimitError: If rate limited after max retries

        """
        max_retries = max_retries if max_retries is not None else self.max_retries
        retry_delay = retry_delay if retry_delay is not None else self.retry_delay

        for attempt in range(max_retries + 1):
            wait_time = await self._try_acquire(endpoint)
            if wait_time <= 0:
                return 0.0

            self.metrics.retry_attempts += 1

            if attempt < max_retries:
                # Exponential backoff with jitter
                delay = min(
                    retry_delay * (2**attempt) * (0.8 + 0.4 * (time.time() % 1)),
                    30.0,  # Max 30 seconds delay
                )
                logger.debug(
                    "Rate limited on %s (attempt %d/%d), waiting %.2fs",
                    endpoint,
                    attempt + 1,
                    max_retries,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                error_msg = (
                    f"Rate limit exceeded for {endpoint} after {max_retries} retries"
                )
                self.metrics.errors["rate_limit_exceeded"] += 1
                raise EmagRateLimitError(error_msg, wait_time)

        return 0.0  # Should never reach here

    async def _try_acquire(self, endpoint: str) -> float:
        """Try to acquire a rate limit token (non-blocking).

        Args:
            endpoint: The API endpoint being called

        Returns:
            float: Number of seconds to wait (0 if no wait needed)

        Raises:
            RuntimeError: If rate limiting is disabled

        """
        if not self.rate_limits:
            return 0.0

        key = self._get_rate_limit_key(endpoint)

        async with self.lock:
            rate_limit = self.rate_limits[key]
            is_exceeded, wait_time = rate_limit.is_exceeded()
            if is_exceeded:
                return wait_time

            rate_limit.increment()
            return 0.0

    async def wait_if_needed(self, endpoint: str, **kwargs) -> None:
        """Wait if needed to respect rate limits for the given endpoint.

        This is a convenience method that wraps acquire() and handles the waiting.

        Args:
            endpoint: The API endpoint being called
            **kwargs: Additional arguments to pass to acquire()

        Raises:
            EmagRateLimitError: If rate limited after max retries

        """
        wait_time = await self.acquire(endpoint, **kwargs)
        if wait_time > 0:
            await asyncio.sleep(wait_time)

    def get_metrics(self) -> dict[str, Any]:
        """Get current rate limiting metrics.

        Returns:
            Dict containing metrics for each rate limit key and global metrics

        """
        metrics = {
            "global": {
                "total_requests": self.metrics.total_requests,
                "retry_attempts": self.metrics.retry_attempts,
                "errors": dict(self.metrics.errors),
            },
            "endpoints": {},
        }

        for key, rate_limit in self.rate_limits.items():
            metrics["endpoints"][key] = {
                "max_requests": rate_limit.max_requests,
                "per_seconds": rate_limit.per_seconds,
                "current_requests": rate_limit.current_requests,
                "reset_in": max(0, rate_limit.reset_time - time.time()),
                "total_requests": rate_limit.metrics.total_requests,
                "rate_limited_requests": rate_limit.metrics.rate_limited_requests,
            }

        return metrics

    def update_rate_limits(self, headers: dict[str, str]) -> None:
        """Update rate limits based on API response headers.

        Args:
            headers: Response headers from the API

        """
        # eMAG API might include rate limit headers in the future
        # This is a placeholder for when that happens

    def get_status(self) -> dict[str, dict[str, int]]:
        """Get the current rate limit status.

        Returns:
            Dict containing rate limit status for each endpoint type

        """
        status = {}
        now = time.time()

        for key, rate_limit in self.rate_limits.items():
            remaining = max(0, rate_limit.max_requests - rate_limit.current_requests)
            reset_in = max(0.0, rate_limit.reset_time - now)

            status[key] = {
                "limit": rate_limit.max_requests,
                "remaining": remaining,
                "reset_in": reset_in,
                "used": rate_limit.current_requests,
                "window_seconds": rate_limit.per_seconds,
            }

        return status
