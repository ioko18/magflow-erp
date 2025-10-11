"""Advanced Rate Limiting Service for MagFlow ERP.

This module provides intelligent API rate limiting with adaptive throttling,
load balancing, and performance optimization for eMAG marketplace integration.
"""

import asyncio
import logging
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.core.dependency_injection import ServiceBase, ServiceContext

logger = logging.getLogger(__name__)


class RateLimitStrategy(str, Enum):
    """Rate limiting strategies."""

    FIXED = "fixed"  # Fixed limits
    ADAPTIVE = "adaptive"  # Adaptive based on load
    BURST = "burst"  # Allow bursts
    SLIDING_WINDOW = "sliding_window"  # Sliding window
    TOKEN_BUCKET = "token_bucket"  # Token bucket algorithm


class LoadLevel(str, Enum):
    """System load levels."""

    LOW = "low"  # Low load - can increase limits
    NORMAL = "normal"  # Normal load - standard limits
    HIGH = "high"  # High load - reduced limits
    CRITICAL = "critical"  # Critical load - minimal limits


@dataclass
class RateLimitConfig:
    """Advanced rate limiting configuration."""

    # Base limits (per minute)
    orders_requests_per_minute: int = 720
    products_requests_per_minute: int = 180
    default_requests_per_minute: int = 60

    # Time windows (seconds)
    window_size_seconds: int = 60

    # Burst configuration
    burst_enabled: bool = True
    burst_window_seconds: int = 10
    burst_multiplier: float = 2.0  # 2x normal rate for bursts

    # Adaptive configuration
    adaptive_enabled: bool = True
    load_check_interval_seconds: int = 30
    performance_threshold_ms: int = 1000  # Response time threshold

    # Backoff configuration
    backoff_enabled: bool = True
    backoff_multiplier: float = 1.5
    backoff_max_delay_seconds: int = 60

    # Queue configuration
    queue_enabled: bool = True
    max_queue_size: int = 1000
    queue_timeout_seconds: int = 30

    # Health monitoring
    health_check_enabled: bool = True
    health_check_interval_seconds: int = 10
    error_rate_threshold: float = 0.05  # 5% error rate threshold


@dataclass
class RateLimitWindow:
    """Rate limit tracking window."""

    window_start: float
    request_count: int = 0
    burst_count: int = 0
    errors: int = 0
    total_response_time: float = 0.0


@dataclass
class RequestMetrics:
    """Request performance metrics."""

    timestamp: float
    response_time_ms: float
    success: bool
    endpoint: str
    user_id: str | None = None


@dataclass
class LoadMetrics:
    """System load metrics."""

    timestamp: float
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    active_connections: int = 0
    queue_size: int = 0
    average_response_time: float = 0.0
    error_rate: float = 0.0
    throughput: int = 0  # requests per second


class AdvancedRateLimiter(ServiceBase):
    """Advanced rate limiter with intelligent throttling."""

    def __init__(self, context: ServiceContext):
        super().__init__(context)
        self.config = RateLimitConfig()
        self._load_rate_limit_config()

        # Rate limiting data structures
        self.request_windows: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.burst_windows: dict[str, RateLimitWindow] = {}
        self.user_requests: dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.endpoint_requests: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=200)
        )

        # Performance tracking
        self.request_metrics: deque = deque(maxlen=10000)
        self.load_metrics: deque = deque(maxlen=1000)
        self.current_load_level: LoadLevel = LoadLevel.NORMAL

        # Queues for rate limited requests
        self.request_queue: asyncio.Queue = asyncio.Queue(
            maxsize=self.config.max_queue_size
        )
        self.queue_processor_task: asyncio.Task | None = None

        # Health monitoring
        self.is_healthy: bool = True
        self.last_health_check: float = 0

    def _load_rate_limit_config(self):
        """Load rate limiting configuration from settings."""
        settings = self.context.settings

        # Base limits
        if hasattr(settings, "emag_orders_requests_per_minute"):
            self.config.orders_requests_per_minute = (
                settings.emag_orders_requests_per_minute
            )
        if hasattr(settings, "emag_products_requests_per_minute"):
            self.config.products_requests_per_minute = (
                settings.emag_products_requests_per_minute
            )

        # Adaptive features
        if hasattr(settings, "rate_limit_adaptive_enabled"):
            self.config.adaptive_enabled = settings.rate_limit_adaptive_enabled
        if hasattr(settings, "rate_limit_burst_enabled"):
            self.config.burst_enabled = settings.rate_limit_burst_enabled

        logger.info("Advanced Rate Limiter configured")

    async def initialize(self):
        """Initialize rate limiter."""
        await super().initialize()

        # Start background tasks
        self.queue_processor_task = asyncio.create_task(self._process_request_queue())
        asyncio.create_task(self._monitor_load())
        asyncio.create_task(self._health_check_loop())

        logger.info("Advanced Rate Limiter initialized")

    async def check_rate_limit(
        self,
        user_id: str,
        endpoint: str,
        request_type: str = "default",
    ) -> dict[str, Any]:
        """Check if request is within rate limits."""
        try:
            current_time = time.time()

            # Determine limits based on request type
            limits = self._get_limits_for_request_type(request_type)

            # Check user-specific limits
            user_allowed, user_wait_time = await self._check_user_rate_limit(
                user_id,
                current_time,
                limits,
            )

            if not user_allowed:
                return {
                    "allowed": False,
                    "wait_time_seconds": user_wait_time,
                    "reason": "user_rate_limit",
                    "retry_after": user_wait_time,
                }

            # Check endpoint-specific limits
            (
                endpoint_allowed,
                endpoint_wait_time,
            ) = await self._check_endpoint_rate_limit(
                endpoint,
                current_time,
                limits,
            )

            if not endpoint_allowed:
                return {
                    "allowed": False,
                    "wait_time_seconds": endpoint_wait_time,
                    "reason": "endpoint_rate_limit",
                    "retry_after": endpoint_wait_time,
                }

            # Check global limits
            global_allowed, global_wait_time = await self._check_global_rate_limit(
                request_type,
                current_time,
                limits,
            )

            if not global_allowed:
                return {
                    "allowed": False,
                    "wait_time_seconds": global_wait_time,
                    "reason": "global_rate_limit",
                    "retry_after": global_wait_time,
                }

            # Check burst limits
            burst_allowed, burst_wait_time = await self._check_burst_limit(
                user_id,
                current_time,
            )

            if not burst_allowed:
                return {
                    "allowed": False,
                    "wait_time_seconds": burst_wait_time,
                    "reason": "burst_rate_limit",
                    "retry_after": burst_wait_time,
                }

            return {"allowed": True, "wait_time_seconds": 0}

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Allow request on error to prevent blocking
            return {"allowed": True, "wait_time_seconds": 0}

    def _get_limits_for_request_type(self, request_type: str) -> dict[str, int]:
        """Get rate limits for specific request type."""
        base_limits = {
            "orders": {
                "requests_per_minute": self.config.orders_requests_per_minute,
                "burst_multiplier": 3.0,
            },
            "products": {
                "requests_per_minute": self.config.products_requests_per_minute,
                "burst_multiplier": 2.0,
            },
            "inventory": {
                "requests_per_minute": self.config.products_requests_per_minute * 0.5,
                "burst_multiplier": 1.5,
            },
            "default": {
                "requests_per_minute": self.config.default_requests_per_minute,
                "burst_multiplier": 2.0,
            },
        }

        limits = base_limits.get(request_type, base_limits["default"])

        # Apply adaptive limits based on load
        if self.config.adaptive_enabled:
            limits = self._apply_adaptive_limits(limits)

        return limits

    def _apply_adaptive_limits(self, base_limits: dict[str, Any]) -> dict[str, Any]:
        """Apply adaptive limits based on system load."""
        adaptive_limits = base_limits.copy()

        # Adjust based on load level
        load_multiplier = {
            LoadLevel.LOW: 1.3,  # Increase by 30%
            LoadLevel.NORMAL: 1.0,  # No change
            LoadLevel.HIGH: 0.7,  # Decrease by 30%
            LoadLevel.CRITICAL: 0.4,  # Decrease by 60%
        }.get(self.current_load_level, 1.0)

        adaptive_limits["requests_per_minute"] = int(
            adaptive_limits["requests_per_minute"] * load_multiplier,
        )

        return adaptive_limits

    async def _check_user_rate_limit(
        self,
        user_id: str,
        current_time: float,
        limits: dict[str, Any],
    ) -> tuple[bool, float]:
        """Check user-specific rate limits."""
        try:
            user_window = self.user_requests[user_id]
            requests_per_minute = limits["requests_per_minute"]

            # Clean old requests (older than 1 minute)
            cutoff_time = current_time - 60
            while user_window and user_window[0] < cutoff_time:
                user_window.popleft()

            # Check if within limits
            if len(user_window) < requests_per_minute:
                user_window.append(current_time)
                return True, 0

            # Calculate wait time
            oldest_request = user_window[0]
            wait_time = 60 - (current_time - oldest_request)

            return False, max(0, wait_time)

        except Exception as e:
            logger.error(f"User rate limit check failed: {e}")
            return True, 0  # Allow on error

    async def _check_endpoint_rate_limit(
        self,
        endpoint: str,
        current_time: float,
        limits: dict[str, Any],
    ) -> tuple[bool, float]:
        """Check endpoint-specific rate limits."""
        try:
            endpoint_window = self.endpoint_requests[endpoint]
            requests_per_minute = limits["requests_per_minute"]

            # Clean old requests
            cutoff_time = current_time - 60
            while endpoint_window and endpoint_window[0] < cutoff_time:
                endpoint_window.popleft()

            # Check if within limits
            if len(endpoint_window) < requests_per_minute:
                endpoint_window.append(current_time)
                return True, 0

            # Calculate wait time
            oldest_request = endpoint_window[0]
            wait_time = 60 - (current_time - oldest_request)

            return False, max(0, wait_time)

        except Exception as e:
            logger.error(f"Endpoint rate limit check failed: {e}")
            return True, 0  # Allow on error

    async def _check_global_rate_limit(
        self,
        request_type: str,
        current_time: float,
        limits: dict[str, Any],
    ) -> tuple[bool, float]:
        """Check global rate limits for request type."""
        try:
            global_key = f"global_{request_type}"
            global_window = self.request_windows[global_key]
            requests_per_minute = limits["requests_per_minute"]

            # Clean old requests
            cutoff_time = current_time - 60
            while global_window and global_window[0] < cutoff_time:
                global_window.popleft()

            # Check if within limits
            if len(global_window) < requests_per_minute:
                global_window.append(current_time)
                return True, 0

            # Calculate wait time
            oldest_request = global_window[0]
            wait_time = 60 - (current_time - oldest_request)

            return False, max(0, wait_time)

        except Exception as e:
            logger.error(f"Global rate limit check failed: {e}")
            return True, 0  # Allow on error

    async def _check_burst_limit(
        self,
        user_id: str,
        current_time: float,
    ) -> tuple[bool, float]:
        """Check burst rate limits."""
        if not self.config.burst_enabled:
            return True, 0

        try:
            # Initialize burst window if needed
            if user_id not in self.burst_windows:
                self.burst_windows[user_id] = RateLimitWindow(
                    window_start=current_time,
                    request_count=0,
                    burst_count=0,
                )

            burst_window = self.burst_windows[user_id]

            # Reset window if expired
            if (
                current_time - burst_window.window_start
                > self.config.burst_window_seconds
            ):
                burst_window.window_start = current_time
                burst_window.request_count = 0
                burst_window.burst_count = 0

            # Check burst limits
            burst_limit = int(
                self.config.default_requests_per_minute
                * self.config.burst_multiplier
                / 6
            )  # Per 10 seconds

            if burst_window.burst_count < burst_limit:
                burst_window.request_count += 1
                burst_window.burst_count += 1
                return True, 0

            # Calculate wait time
            wait_time = self.config.burst_window_seconds - (
                current_time - burst_window.window_start
            )

            return False, max(0, wait_time)

        except Exception as e:
            logger.error(f"Burst limit check failed: {e}")
            return True, 0  # Allow on error

    async def record_request_metrics(
        self,
        user_id: str,
        endpoint: str,
        response_time_ms: float,
        success: bool,
    ):
        """Record request metrics for monitoring."""
        try:
            metrics = RequestMetrics(
                timestamp=time.time(),
                response_time_ms=response_time_ms,
                success=success,
                endpoint=endpoint,
                user_id=user_id,
            )

            self.request_metrics.append(metrics)

            # Update load metrics
            await self._update_load_metrics(metrics)

        except Exception as e:
            logger.error(f"Failed to record request metrics: {e}")

    async def _update_load_metrics(self, metrics: RequestMetrics):
        """Update system load metrics."""
        try:
            current_time = time.time()

            # Calculate load metrics for last 60 seconds
            recent_metrics = [
                m for m in self.request_metrics if current_time - m.timestamp <= 60
            ]

            if recent_metrics:
                load_metrics = LoadMetrics(
                    timestamp=current_time,
                    average_response_time=statistics.mean(
                        m.response_time_ms for m in recent_metrics
                    ),
                    error_rate=sum(1 for m in recent_metrics if not m.success)
                    / len(recent_metrics),
                    throughput=len(recent_metrics),
                )

                self.load_metrics.append(load_metrics)

                # Update current load level
                await self._update_load_level(load_metrics)

        except Exception as e:
            logger.error(f"Failed to update load metrics: {e}")

    async def _update_load_level(self, metrics: LoadMetrics):
        """Update current system load level."""
        try:
            # Simple load level determination based on metrics
            if (
                metrics.error_rate > 0.1
                or metrics.average_response_time > 2000
                or self.request_queue.qsize() > self.config.max_queue_size * 0.8
            ):
                new_level = LoadLevel.CRITICAL
            elif (
                metrics.error_rate > 0.05
                or metrics.average_response_time > 1000
                or self.request_queue.qsize() > self.config.max_queue_size * 0.5
            ):
                new_level = LoadLevel.HIGH
            elif metrics.error_rate < 0.01 and metrics.average_response_time < 500:
                new_level = LoadLevel.LOW
            else:
                new_level = LoadLevel.NORMAL

            if new_level != self.current_load_level:
                logger.info(
                    f"Load level changed: {self.current_load_level} -> {new_level}"
                )
                self.current_load_level = new_level

                # Log load level change
                await self.log_load_level_change(new_level, metrics)

        except Exception as e:
            logger.error(f"Failed to update load level: {e}")

    async def log_load_level_change(self, new_level: LoadLevel, metrics: LoadMetrics):
        """Log load level changes."""
        try:
            logger.info(
                f"System load level changed to {new_level.value.upper()} - "
                f"Avg response: {metrics.average_response_time:.1f}ms, "
                f"Error rate: {metrics.error_rate:.2%}, "
                f"Queue size: {self.request_queue.qsize()}",
            )

            # Could trigger alerts or scaling actions here
            if new_level in [LoadLevel.HIGH, LoadLevel.CRITICAL]:
                # Trigger scaling or alerting
                pass

        except Exception as e:
            logger.error(f"Failed to log load level change: {e}")

    async def _monitor_load(self):
        """Background task to monitor system load."""
        while True:
            try:
                await asyncio.sleep(self.config.load_check_interval_seconds)

                # Get current metrics
                current_metrics = (
                    list(self.request_metrics)[-100:] if self.request_metrics else []
                )

                if current_metrics:
                    avg_response_time = statistics.mean(
                        m.response_time_ms for m in current_metrics
                    )
                    error_rate = sum(1 for m in current_metrics if not m.success) / len(
                        current_metrics
                    )

                    # Log performance metrics
                    logger.debug(
                        f"Performance metrics - Response time: {avg_response_time:.1f}ms, "
                        f"Error rate: {error_rate:.2%}",
                    )

            except Exception as e:
                logger.error(f"Load monitoring failed: {e}")

    async def _health_check_loop(self):
        """Background task for health checks."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval_seconds)
                await self._perform_health_check()

            except Exception as e:
                logger.error(f"Health check failed: {e}")

    async def _perform_health_check(self):
        """Perform system health check."""
        try:
            current_time = time.time()
            recent_metrics = [
                m for m in self.request_metrics if current_time - m.timestamp <= 60
            ]

            if recent_metrics:
                error_rate = sum(1 for m in recent_metrics if not m.success) / len(
                    recent_metrics
                )
                avg_response_time = statistics.mean(
                    m.response_time_ms for m in recent_metrics
                )

                # Determine health status
                if (
                    error_rate > self.config.error_rate_threshold
                    or avg_response_time > self.config.performance_threshold_ms * 2
                ):
                    self.is_healthy = False
                    logger.warning(
                        f"Rate limiter unhealthy - Error rate: {error_rate:.2%}, "
                        f"Avg response time: {avg_response_time:.1f}ms",
                    )
                else:
                    self.is_healthy = True

            self.last_health_check = current_time

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.is_healthy = False

    async def _process_request_queue(self):
        """Process queued requests during high load."""
        while True:
            try:
                # Get request from queue with timeout
                try:
                    queue_item = await asyncio.wait_for(
                        self.request_queue.get(),
                        timeout=1.0,
                    )
                except TimeoutError:
                    continue

                user_id, endpoint, request_type, future = queue_item

                # Process the request
                try:
                    result = await self.check_rate_limit(
                        user_id, endpoint, request_type
                    )
                    future.set_result(result)
                except Exception as e:
                    future.set_exception(e)
                finally:
                    self.request_queue.task_done()

            except Exception as e:
                logger.error(f"Queue processing failed: {e}")

    async def queue_request(
        self,
        user_id: str,
        endpoint: str,
        request_type: str = "default",
    ) -> dict[str, Any]:
        """Queue request for processing during high load."""
        if not self.config.queue_enabled:
            return await self.check_rate_limit(user_id, endpoint, request_type)

        try:
            # Create future for result
            future = asyncio.Future()

            # Add to queue
            await self.request_queue.put((user_id, endpoint, request_type, future))

            # Wait for result
            result = await asyncio.wait_for(
                future,
                timeout=self.config.queue_timeout_seconds,
            )

            return result

        except TimeoutError:
            return {
                "allowed": False,
                "wait_time_seconds": 30,
                "reason": "queue_timeout",
                "retry_after": 30,
            }
        except Exception as e:
            logger.error(f"Queue request failed: {e}")
            return {"allowed": False, "reason": "queue_error"}

    async def get_rate_limit_status(
        self,
        user_id: str | None = None,
        endpoint: str | None = None,
    ) -> dict[str, Any]:
        """Get current rate limiting status."""
        try:
            current_time = time.time()

            status = {
                "is_healthy": self.is_healthy,
                "current_load_level": self.current_load_level.value,
                "queue_size": self.request_queue.qsize(),
                "last_health_check": self.last_health_check,
                "adaptive_limits_enabled": self.config.adaptive_enabled,
                "burst_limits_enabled": self.config.burst_enabled,
                "limits": {
                    "orders": self.config.orders_requests_per_minute,
                    "products": self.config.products_requests_per_minute,
                    "default": self.config.default_requests_per_minute,
                },
            }

            # Add user-specific info
            if user_id:
                user_requests = list(self.user_requests[user_id])
                cutoff_time = current_time - 60
                recent_requests = [r for r in user_requests if r > cutoff_time]
                status["user_requests_in_last_minute"] = len(recent_requests)

            # Add endpoint-specific info
            if endpoint:
                endpoint_requests = list(self.endpoint_requests[endpoint])
                cutoff_time = current_time - 60
                recent_requests = [r for r in endpoint_requests if r > cutoff_time]
                status["endpoint_requests_in_last_minute"] = len(recent_requests)

            return status

        except Exception as e:
            logger.error(f"Failed to get rate limit status: {e}")
            return {"error": str(e)}

    async def cleanup_old_data(self):
        """Clean up old rate limiting data."""
        try:
            current_time = time.time()
            cutoff_time = current_time - 300  # 5 minutes ago

            # Clean up user requests
            for user_id in list(self.user_requests.keys()):
                user_requests = self.user_requests[user_id]
                while user_requests and user_requests[0] < cutoff_time:
                    user_requests.popleft()
                if not user_requests:
                    del self.user_requests[user_id]

            # Clean up endpoint requests
            for endpoint in list(self.endpoint_requests.keys()):
                endpoint_requests = self.endpoint_requests[endpoint]
                while endpoint_requests and endpoint_requests[0] < cutoff_time:
                    endpoint_requests.popleft()
                if not endpoint_requests:
                    del self.endpoint_requests[endpoint]

            # Clean up burst windows
            expired_users = []
            for user_id, burst_window in self.burst_windows.items():
                if current_time - burst_window.window_start > 300:
                    expired_users.append(user_id)

            for user_id in expired_users:
                del self.burst_windows[user_id]

            logger.debug("Cleaned up old rate limiting data")

        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
