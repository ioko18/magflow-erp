"""Base eMAG Service.

Provides common functionality for all eMAG integration services including:
- Rate limiting
- Error handling with retries
- API client initialization
- Logging and monitoring
- Response validation
"""

import asyncio
import time
from abc import ABC
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

import structlog
from app.integrations.emag.emag_api_client import EmagAPIClient
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.emag_monitoring import log_emag_request

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""

    pass


class EmagAPIError(Exception):
    """Base exception for eMAG API errors."""

    pass


class BaseEmagService(ABC):
    """Base service class for eMAG integration.

    Provides common functionality that all eMAG services need:
    - Automatic rate limiting per endpoint type
    - Retry logic with exponential backoff
    - Structured logging and monitoring
    - Error handling and validation

    Usage:
        class MyEmagService(BaseEmagService):
            def __init__(self, account_type: str = "main"):
                super().__init__(
                    account_type=account_type,
                    service_name="my_emag_service",
                    rate_limit=10  # requests per second
                )

            async def my_method(self):
                result = await self.make_request(
                    endpoint="product_offer/read",
                    method="POST",
                    data={"id": 123}
                )
                return result
    """

    def __init__(
        self,
        account_type: str = "main",
        service_name: str = "emag_service",
        rate_limit: int | None = None,
    ):
        """Initialize base eMAG service.

        Args:
            account_type: Account type ("main" or "fbe")
            service_name: Name of the service for logging
            rate_limit: Requests per second limit (None = no limit)
        """
        self.account_type = account_type
        self.service_name = service_name
        self.rate_limit = rate_limit or settings.EMAG_RATE_LIMIT_OTHER

        # Initialize API client
        self.client = EmagAPIClient(account_type=account_type)

        # Rate limiting state
        self._last_request_time = 0.0
        self._request_count = 0
        self._rate_limit_window_start = time.time()

        # Logger with service context
        self.logger = logger.bind(service=service_name, account_type=account_type)

        self.logger.info(f"Initialized {service_name} for {account_type} account")

    async def _apply_rate_limit(self) -> None:
        """Apply rate limiting before making a request."""
        if not self.rate_limit:
            return

        current_time = time.time()
        window_duration = 1.0  # 1 second window

        # Reset counter if we're in a new window
        if current_time - self._rate_limit_window_start >= window_duration:
            self._request_count = 0
            self._rate_limit_window_start = current_time

        # Check if we've exceeded the limit
        if self._request_count >= self.rate_limit:
            # Calculate how long to wait
            wait_time = window_duration - (current_time - self._rate_limit_window_start)
            if wait_time > 0:
                self.logger.debug(
                    f"Rate limit reached, waiting {wait_time:.2f}s",
                    rate_limit=self.rate_limit,
                    request_count=self._request_count,
                )
                await asyncio.sleep(wait_time)
                # Reset after waiting
                self._request_count = 0
                self._rate_limit_window_start = time.time()

        self._request_count += 1
        self._last_request_time = time.time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True,
    )
    async def make_request(
        self,
        endpoint: str,
        method: str = "POST",
        data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an API request with rate limiting, retries, and monitoring.

        Args:
            endpoint: API endpoint (e.g., "product_offer/read")
            method: HTTP method (default: POST)
            data: Request payload
            **kwargs: Additional arguments for the API client

        Returns:
            API response as dictionary

        Raises:
            EmagAPIError: If the API returns an error
            RateLimitExceeded: If rate limit is exceeded
        """
        # Apply rate limiting
        await self._apply_rate_limit()

        # Log request
        self.logger.info(
            f"Making request to {endpoint}",
            endpoint=endpoint,
            method=method,
        )

        start_time = time.time()

        try:
            # Make the actual request
            response = await self.client._request(
                endpoint=endpoint, data=data or {}, **kwargs
            )

            # Calculate response time
            response_time = (time.time() - start_time) * 1000  # ms

            # Log successful request
            log_emag_request(
                method=method,
                endpoint=endpoint,
                status_code=200,
                response_time=response_time,
                account_type=self.account_type,
                success=not response.get("isError", False),
            )

            # Validate response
            if response.get("isError"):
                error_messages = response.get("messages", [])
                self.logger.error(
                    f"eMAG API error for {endpoint}",
                    endpoint=endpoint,
                    errors=error_messages,
                )
                raise EmagAPIError(f"API error: {error_messages}")

            self.logger.info(
                f"Request to {endpoint} completed successfully",
                endpoint=endpoint,
                response_time_ms=response_time,
            )

            return response

        except Exception as e:
            response_time = (time.time() - start_time) * 1000

            # Log failed request
            log_emag_request(
                method=method,
                endpoint=endpoint,
                status_code=500,
                response_time=response_time,
                account_type=self.account_type,
                success=False,
            )

            self.logger.error(
                f"Request to {endpoint} failed",
                endpoint=endpoint,
                error=str(e),
                response_time_ms=response_time,
            )

            raise

    def validate_response(
        self,
        response: dict[str, Any],
        required_fields: list[str] | None = None,
    ) -> bool:
        """Validate API response structure.

        Args:
            response: API response to validate
            required_fields: List of required fields in the response

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(response, dict):
            self.logger.error("Response is not a dictionary")
            return False

        if response.get("isError"):
            self.logger.error(
                "Response contains error", errors=response.get("messages", [])
            )
            return False

        if required_fields:
            results = response.get("results", {})
            missing_fields = [
                field for field in required_fields if field not in results
            ]
            if missing_fields:
                self.logger.error(
                    "Response missing required fields", missing_fields=missing_fields
                )
                return False

        return True

    async def close(self) -> None:
        """Close the API client and cleanup resources."""
        await self.client.close()
        self.logger.info(f"{self.service_name} closed")


def with_rate_limit(rate_limit: int):
    """Decorator to apply rate limiting to a method.

    Usage:
        @with_rate_limit(rate_limit=10)
        async def my_method(self):
            # This method will be rate limited to 10 calls per second
            pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(self: BaseEmagService, *args: Any, **kwargs: Any) -> T:
            # Temporarily override rate limit
            original_rate_limit = self.rate_limit
            self.rate_limit = rate_limit

            try:
                await self._apply_rate_limit()
                result = await func(self, *args, **kwargs)
                return cast(T, result)
            finally:
                # Restore original rate limit
                self.rate_limit = original_rate_limit

        return cast(Callable[..., T], wrapper)

    return decorator


def with_retry(max_attempts: int = 3, backoff: float = 2.0):
    """Decorator to add retry logic to a method.

    Usage:
        @with_retry(max_attempts=5, backoff=3.0)
        async def my_method(self):
            # This method will retry up to 5 times with 3s backoff
            pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=backoff, min=2, max=30),
            retry=retry_if_exception_type(
                (ConnectionError, TimeoutError, EmagAPIError)
            ),
            reraise=True,
        )
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            result = await func(*args, **kwargs)
            return cast(T, result)

        return cast(Callable[..., T], wrapper)

    return decorator
