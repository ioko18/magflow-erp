"""
eMAG API Rate Limiter.

Rate limiting implementation conforming to eMAG API v4.4.8 specifications (Section 2.3).
- Orders: 12 requests/second (720 requests/minute)
- Other operations: 3 requests/second (180 requests/minute)
"""

import asyncio
import logging
import secrets
import time
from collections import deque

from app.core.emag_constants import RateLimits
from app.core.emag_errors import RateLimitError

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket algorithm for rate limiting."""

    def __init__(self, rate: float, capacity: int):
        """
        Initialize token bucket.

        Args:
            rate: Token refill rate (tokens per second)
            capacity: Maximum bucket capacity
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens from bucket.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired, False otherwise
        """
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update

            # Refill tokens based on elapsed time
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    async def wait_for_token(self, tokens: int = 1, timeout: float | None = None):
        """
        Wait until tokens are available.

        Args:
            tokens: Number of tokens needed
            timeout: Maximum wait time in seconds

        Raises:
            RateLimitError: If timeout is exceeded
        """
        start_time = time.time()

        while True:
            if await self.acquire(tokens):
                return

            # Check timeout
            if timeout and (time.time() - start_time) >= timeout:
                raise RateLimitError(
                    remaining_seconds=int(tokens / self.rate),
                    message="Rate limit timeout exceeded",
                )

            # Wait a bit before trying again
            await asyncio.sleep(0.1)

    def get_available_tokens(self) -> float:
        """Get current number of available tokens."""
        now = time.time()
        elapsed = now - self.last_update
        return min(self.capacity, self.tokens + elapsed * self.rate)


class SlidingWindowCounter:
    """Sliding window counter for tracking requests per minute."""

    def __init__(self, window_size: int = 60):
        """
        Initialize sliding window counter.

        Args:
            window_size: Window size in seconds
        """
        self.window_size = window_size
        self.requests = deque()
        self._lock = asyncio.Lock()

    async def add_request(self):
        """Add a request to the window."""
        async with self._lock:
            now = time.time()
            self.requests.append(now)
            self._cleanup(now)

    async def get_count(self) -> int:
        """Get number of requests in current window."""
        async with self._lock:
            now = time.time()
            self._cleanup(now)
            return len(self.requests)

    def _cleanup(self, now: float):
        """Remove requests outside the window."""
        cutoff = now - self.window_size
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()


class EmagRateLimiter:
    """
    Rate limiter conforming to eMAG API v4.4.8 specifications.

    Implements:
    - 12 requests/second for orders (720/minute)
    - 3 requests/second for other operations (180/minute)
    - Global limit tracking per minute
    - Jitter to avoid thundering herd
    """

    def __init__(self):
        """Initialize rate limiter with eMAG API limits."""
        # Token buckets for per-second limits
        self.orders_bucket = TokenBucket(
            rate=RateLimits.ORDERS_RPS,
            capacity=RateLimits.ORDERS_RPS * 2,  # Allow some burst
        )
        self.other_bucket = TokenBucket(
            rate=RateLimits.OTHER_RPS,
            capacity=RateLimits.OTHER_RPS * 2,  # Allow some burst
        )

        # Sliding window counters for per-minute limits
        self.orders_window = SlidingWindowCounter(window_size=60)
        self.other_window = SlidingWindowCounter(window_size=60)

        # Statistics
        self.stats = {
            "orders_requests": 0,
            "other_requests": 0,
            "rate_limit_hits": 0,
            "total_wait_time": 0.0,
        }
        self._stats_lock = asyncio.Lock()

    async def acquire(
        self, operation_type: str = "other", timeout: float | None = 30.0
    ):
        """
        Acquire rate limit token for an operation.

        Args:
            operation_type: Type of operation ("orders" or "other")
            timeout: Maximum wait time in seconds

        Raises:
            RateLimitError: If rate limit cannot be acquired within timeout
        """
        is_orders = operation_type.lower() == "orders"
        bucket = self.orders_bucket if is_orders else self.other_bucket
        window = self.orders_window if is_orders else self.other_window
        rpm_limit = RateLimits.ORDERS_RPM if is_orders else RateLimits.OTHER_RPM

        start_time = time.time()

        # Check per-minute limit
        current_count = await window.get_count()
        if current_count >= rpm_limit:
            wait_time = 60 - (time.time() % 60)
            logger.warning(
                f"Per-minute rate limit reached for {operation_type}. "
                f"Waiting {wait_time:.1f}s..."
            )
            await self._record_rate_limit_hit()

            if timeout and wait_time > timeout:
                raise RateLimitError(
                    remaining_seconds=int(wait_time),
                    message=f"Per-minute rate limit exceeded for {operation_type}",
                )

            await asyncio.sleep(wait_time)

        # Acquire token from bucket (per-second limit)
        try:
            await bucket.wait_for_token(tokens=1, timeout=timeout)
        except RateLimitError:
            await self._record_rate_limit_hit()
            raise

        # Add jitter to avoid thundering herd
        # Use secrets for cryptographically secure random jitter
        random_gen = secrets.SystemRandom()
        jitter = random_gen.uniform(0, RateLimits.JITTER_MAX)
        await asyncio.sleep(jitter)

        # Record request
        await window.add_request()

        # Update statistics
        wait_time = time.time() - start_time
        await self._update_stats(operation_type, wait_time)

        logger.debug(
            f"Rate limit acquired for {operation_type} (waited {wait_time:.3f}s)"
        )

    async def _update_stats(self, operation_type: str, wait_time: float):
        """Update rate limiter statistics."""
        async with self._stats_lock:
            if operation_type.lower() == "orders":
                self.stats["orders_requests"] += 1
            else:
                self.stats["other_requests"] += 1
            self.stats["total_wait_time"] += wait_time

    async def _record_rate_limit_hit(self):
        """Record a rate limit hit."""
        async with self._stats_lock:
            self.stats["rate_limit_hits"] += 1

    async def get_stats(self) -> dict:
        """
        Get rate limiter statistics.

        Returns:
            Dictionary with statistics
        """
        async with self._stats_lock:
            orders_count = await self.orders_window.get_count()
            other_count = await self.other_window.get_count()

            return {
                **self.stats,
                "current_orders_rpm": orders_count,
                "current_other_rpm": other_count,
                "orders_rpm_usage": orders_count / RateLimits.ORDERS_RPM,
                "other_rpm_usage": other_count / RateLimits.OTHER_RPM,
                "orders_tokens_available": self.orders_bucket.get_available_tokens(),
                "other_tokens_available": self.other_bucket.get_available_tokens(),
            }

    async def reset_stats(self):
        """Reset statistics."""
        async with self._stats_lock:
            self.stats = {
                "orders_requests": 0,
                "other_requests": 0,
                "rate_limit_hits": 0,
                "total_wait_time": 0.0,
            }

    def get_usage_percentage(self, operation_type: str = "other") -> float:
        """
        Get current usage percentage of rate limit.

        Args:
            operation_type: Type of operation ("orders" or "other")

        Returns:
            Usage percentage (0.0 to 1.0)
        """
        is_orders = operation_type.lower() == "orders"
        bucket = self.orders_bucket if is_orders else self.other_bucket

        available = bucket.get_available_tokens()
        capacity = bucket.capacity

        return 1.0 - (available / capacity)


# Global rate limiter instance
_rate_limiter: EmagRateLimiter | None = None


def get_rate_limiter() -> EmagRateLimiter:
    """
    Get global rate limiter instance.

    Returns:
        EmagRateLimiter instance
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = EmagRateLimiter()
    return _rate_limiter


async def rate_limited_request(operation_type: str = "other", timeout: float = 30.0):
    """
    Decorator/context manager for rate-limited requests.

    Args:
        operation_type: Type of operation ("orders" or "other")
        timeout: Maximum wait time for rate limit

    Example:
        await rate_limited_request("orders")
        result = await emag_api.get_orders()
    """
    limiter = get_rate_limiter()
    await limiter.acquire(operation_type, timeout)
