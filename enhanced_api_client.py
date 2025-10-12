#!/usr/bin/env python3
"""
Enhanced API Rate Limiting and Retry System for eMAG Sync
Provides intelligent rate limiting, exponential backoff, and circuit breaker patterns
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

class RateLimitStrategy(Enum):
    """Rate limiting strategies"""
    FIXED_WINDOW = "fixed_window"      # Traditional fixed window
    SLIDING_WINDOW = "sliding_window"  # Sliding window counter
    TOKEN_BUCKET = "token_bucket"      # Token bucket algorithm
    ADAPTIVE = "adaptive"              # Adaptive based on response codes

class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, requests blocked
    HALF_OPEN = "half_open" # Testing if service recovered

@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests_per_second: float = 3.0
    burst_limit: int = 10
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    adaptive_enabled: bool = True
    backoff_factor: float = 2.0
    max_backoff_seconds: float = 300.0

@dataclass
class RetryConfig:
    """Retry configuration"""
    max_attempts: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on_429: bool = True
    retry_on_5xx: bool = True
    retry_on_network: bool = True

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    expected_exception: tuple = (Exception,)
    success_threshold: int = 3

@dataclass
class RequestMetrics:
    """Request metrics for adaptive rate limiting"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limited_requests: int = 0
    last_request_time: datetime | None = None
    response_times: list[float] = field(default_factory=list)

class EnhancedRateLimiter:
    """Enhanced rate limiter with multiple strategies"""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._tokens: float = config.burst_limit
        self._last_update: float = time.time()
        self._lock = asyncio.Lock()
        self._metrics = RequestMetrics()

        # Adaptive rate limiting
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._current_rate = config.requests_per_second

    async def acquire(self) -> bool:
        """Acquire permission to make a request"""
        async with self._lock:
            return await self._try_acquire()

    async def _try_acquire(self) -> bool:
        """Internal acquire method"""
        now = time.time()

        if self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return await self._token_bucket_acquire(now)
        elif self.config.strategy == RateLimitStrategy.FIXED_WINDOW:
            return await self._fixed_window_acquire(now)
        elif self.config.strategy == RateLimitStrategy.ADAPTIVE:
            return await self._adaptive_acquire(now)
        else:
            return await self._token_bucket_acquire(now)  # Default

    async def _token_bucket_acquire(self, now: float) -> bool:
        """Token bucket rate limiting"""
        time_passed = now - self._last_update
        self._last_update = now

        # Add tokens based on time passed
        tokens_to_add = time_passed * self._current_rate
        self._tokens = min(self._tokens + tokens_to_add, self.config.burst_limit)

        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True

        return False

    async def _fixed_window_acquire(self, now: float) -> bool:
        """Fixed window rate limiting"""
        # Simple implementation - would need window tracking in production
        return await self._token_bucket_acquire(now)

    async def _adaptive_acquire(self, now: float) -> bool:
        """Adaptive rate limiting based on success/failure rates"""
        # Adjust rate based on recent performance
        if self._consecutive_failures > 3:
            self._current_rate = max(self._current_rate * 0.5, 0.1)
            self._consecutive_failures = 0
        elif self._consecutive_successes > 5:
            self._current_rate = min(self._current_rate * 1.2, self.config.requests_per_second)
            self._consecutive_successes = 0

        return await self._token_bucket_acquire(now)

    def record_success(self, response_time: float):
        """Record successful request"""
        self._metrics.successful_requests += 1
        self._metrics.response_times.append(response_time)
        self._consecutive_successes += 1
        self._consecutive_failures = 0

        # Keep only recent response times
        if len(self._metrics.response_times) > 100:
            self._metrics.response_times = self._metrics.response_times[-100:]

    def record_failure(self, is_rate_limited: bool = False):
        """Record failed request"""
        self._metrics.failed_requests += 1
        if is_rate_limited:
            self._metrics.rate_limited_requests += 1

        self._consecutive_failures += 1
        self._consecutive_successes = 0

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics"""
        return {
            "total_requests": self._metrics.total_requests,
            "successful_requests": self._metrics.successful_requests,
            "failed_requests": self._metrics.failed_requests,
            "rate_limited_requests": self._metrics.rate_limited_requests,
            "current_rate": self._current_rate,
            "success_rate": (self._metrics.successful_requests /
                           max(self._metrics.total_requests, 1)),
            "avg_response_time": (sum(self._metrics.response_times) /
                                max(len(self._metrics.response_times), 1))
        }

class RetryManager:
    """Enhanced retry manager with exponential backoff and jitter"""

    def __init__(self, config: RetryConfig):
        self.config = config

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if we should retry based on exception type and attempt count"""
        if attempt >= self.config.max_attempts:
            return False

        # Check if exception is retryable
        if isinstance(exception, Exception):
            # Network errors
            if self.config.retry_on_network:
                if any(err_type in str(type(exception).__name__) for err_type in
                       ['ConnectionError', 'Timeout', 'Network']):
                    return True

            # HTTP 429 (Too Many Requests)
            if self.config.retry_on_429 and hasattr(exception, 'status'):
                if getattr(exception, 'status', None) == 429:
                    return True

            # HTTP 5xx errors
            if self.config.retry_on_5xx and hasattr(exception, 'status'):
                status = getattr(exception, 'status', None)
                if status and 500 <= status < 600:
                    return True

        return False

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt"""
        # Exponential backoff: base_delay * (exponential_base ^ attempt)
        delay = self.config.base_delay * (self.config.exponential_base ** attempt)

        # Cap at max_delay
        delay = min(delay, self.config.max_delay)

        # Add jitter to prevent thundering herd
        if self.config.jitter:
            import random
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)

        return delay

    async def execute_with_retry(self, func, *args, **kwargs):
        """Execute function with retry logic"""
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                start_time = time.time()
                result = await func(*args, **kwargs)
                response_time = time.time() - start_time

                logger.info(f"Request succeeded on attempt {attempt + 1} in {response_time:.2f}s")
                return result

            except Exception as e:
                last_exception = e
                logger.warning(f"Request failed on attempt {attempt + 1}: {e}")

                if not self.should_retry(e, attempt + 1):
                    logger.error(f"Max retries exceeded or non-retryable error: {e}")
                    raise e

                delay = self.calculate_delay(attempt)
                logger.info(f"Retrying in {delay:.2f} seconds (attempt {attempt + 2}/{self.config.max_attempts})")
                await asyncio.sleep(delay)

        # If we get here, all retries failed
        logger.error(f"All {self.config.max_attempts} retry attempts failed")
        raise last_exception

class CircuitBreaker:
    """Circuit breaker pattern implementation"""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: datetime | None = None
        self._lock = asyncio.Lock()

    async def call(self, func, *args, **kwargs):
        """Execute function through circuit breaker"""
        async with self._lock:
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.success_count = 0
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
                else:
                    raise Exception("Circuit breaker is OPEN - service unavailable")

            try:
                result = await func(*args, **kwargs)

                async with self._lock:
                    if self.state == CircuitBreakerState.HALF_OPEN:
                        self.success_count += 1
                        if self.success_count >= self.config.success_threshold:
                            self._reset()
                            logger.info("Circuit breaker reset to CLOSED")

                return result

            except self.config.expected_exception as e:
                async with self._lock:
                    self.failure_count += 1
                    self.last_failure_time = datetime.utcnow()

                    if (self.state == CircuitBreakerState.CLOSED and
                        self.failure_count >= self.config.failure_threshold):
                        self.state = CircuitBreakerState.OPEN
                        logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

                    elif self.state == CircuitBreakerState.HALF_OPEN:
                        self.state = CircuitBreakerState.OPEN
                        logger.warning("Circuit breaker reopened due to failure in HALF_OPEN state")

                raise e

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit breaker"""
        if self.last_failure_time is None:
            return True

        time_since_failure = datetime.utcnow() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.config.recovery_timeout

    def _reset(self):
        """Reset circuit breaker to closed state"""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        logger.info("Circuit breaker reset to CLOSED state")

    def get_status(self) -> dict[str, Any]:
        """Get circuit breaker status"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None
        }

class EnhancedEMAGClient:
    """Enhanced eMAG API client with advanced rate limiting and retry logic"""

    def __init__(self,
                 rate_limit_config: RateLimitConfig | None = None,
                 retry_config: RetryConfig | None = None,
                 circuit_breaker_config: CircuitBreakerConfig | None = None):
        self.rate_limiter = EnhancedRateLimiter(rate_limit_config or RateLimitConfig())
        self.retry_manager = RetryManager(retry_config or RetryConfig())
        self.circuit_breaker = CircuitBreaker(circuit_breaker_config or CircuitBreakerConfig())

        self._session: aiohttp.ClientSession | None = None
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()

    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                connector=aiohttp.TCPConnector(limit=10, limit_per_host=5)
            )

    async def make_request(self, method: str, url: str, **kwargs) -> Any:
        """Make HTTP request with enhanced error handling and rate limiting"""

        async def _execute_request():
            await self._ensure_session()

            # Apply rate limiting
            if not await self.rate_limiter.acquire():
                raise Exception("Rate limit exceeded")

            start_time = time.time()

            try:
                async with self._session.request(method, url, **kwargs) as response:
                    response_time = time.time() - start_time

                    # Record metrics
                    if response.status == 200:
                        self.rate_limiter.record_success(response_time)
                    else:
                        self.rate_limiter.record_failure(response.status == 429)

                    # Handle different status codes
                    if response.status == 429:
                        raise Exception(f"Rate limited: {response.status}")

                    response.raise_for_status()
                    return await response.json()

            except Exception as e:
                response_time = time.time() - start_time
                self.rate_limiter.record_failure("rate_limit" in str(e))
                raise e

        # Apply circuit breaker and retry logic
        return await self.circuit_breaker.call(
            lambda: self.retry_manager.execute_with_retry(_execute_request)
        )

    async def get_product_offers(self, page: int = 1, items_per_page: int = 100) -> dict:
        """Get product offers with enhanced error handling"""
        url = "https://marketplace-api.emag.ro/api-3/product_offer/read"

        payload = {
            "data": {
                "currentPage": page,
                "itemsPerPage": items_per_page
            }
        }

        # Get credentials from environment
        username = os.getenv('EMAG_API_USERNAME')
        password = os.getenv('EMAG_API_PASSWORD')

        if not username or not password:
            raise ValueError("eMAG credentials not found in environment")

        return await self.make_request(
            "POST",
            url,
            json=payload,
            auth=aiohttp.BasicAuth(username, password)
        )

    def get_rate_limiter_metrics(self) -> dict[str, Any]:
        """Get rate limiter metrics"""
        return self.rate_limiter.get_metrics()

    def get_circuit_breaker_status(self) -> dict[str, Any]:
        """Get circuit breaker status"""
        return self.circuit_breaker.get_status()

# Global client instance
_enhanced_client = None

async def get_enhanced_emag_client() -> EnhancedEMAGClient:
    """Get or create enhanced eMAG client"""
    global _enhanced_client
    if _enhanced_client is None:
        _enhanced_client = EnhancedEMAGClient(
            rate_limit_config=RateLimitConfig(
                requests_per_second=3.0,
                burst_limit=10,
                strategy=RateLimitStrategy.ADAPTIVE,
                adaptive_enabled=True
            ),
            retry_config=RetryConfig(
                max_attempts=5,
                base_delay=1.0,
                max_delay=60.0,
                retry_on_429=True,
                retry_on_5xx=True,
                retry_on_network=True
            ),
            circuit_breaker_config=CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60.0,
                success_threshold=3
            )
        )
    return _enhanced_client

# Export for easy usage
__all__ = [
    'EnhancedEMAGClient',
    'RateLimitConfig',
    'RetryConfig',
    'CircuitBreakerConfig',
    'RateLimitStrategy',
    'CircuitBreakerState',
    'get_enhanced_emag_client'
]
