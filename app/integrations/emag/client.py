"""eMAG API client with authentication, rate limiting, and retry logic.

This module provides an asynchronous client for interacting with the eMAG Marketplace API,
with built-in support for authentication, rate limiting, and automatic retries.
"""

import base64
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Generic, TypeVar, cast
from urllib.parse import urljoin

import aiohttp
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from .config import EmagAccountType, EmagSettings, get_settings
from .exceptions import (
    EmagAPIError,
    EmagAuthError,
    EmagError,
    EmagNonRetryableError,
    EmagRateLimitError,
    EmagRetryableError,
)
from .rate_limiting import RateLimiter

# Type variable for response data
T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    initial_delay: float = 0.5  # seconds
    max_delay: float = 30.0  # seconds
    jitter: float = 0.1  # 10% jitter
    retry_status_codes: tuple[int, ...] = (429, 500, 502, 503, 504)


class EmagAPIClient(Generic[T]):
    """eMAG API client with built-in authentication, rate limiting, and retries.

    Features:
    - Automatic authentication with token refresh
    - Rate limiting based on eMAG API quotas
    - Automatic retries for transient failures
    - Circuit breaker for repeated failures
    - Detailed error handling with Problem Details (RFC 9457)
    - Request/response logging
    - Async context manager support
    """

    def __init__(
        self,
        account_type: EmagAccountType = EmagAccountType.MAIN,
        settings: EmagSettings | None = None,
        retry_config: RetryConfig | None = None,
    ):
        """Initialize the eMAG API client.

        Args:
            account_type: The type of eMAG account (MAIN or FBE)
            settings: Optional EmagSettings instance. If not provided, will load from environment.
            retry_config: Optional configuration for retry behavior

        """
        self.settings = settings or get_settings()
        self.account_type = account_type
        self.account_config = self.settings.get_account_config(account_type)
        self.retry_config = retry_config or RetryConfig()

        # Initialize rate limiter with account-specific settings
        self._rate_limiter = RateLimiter(
            requests_per_second=max(
                self.settings.rate_limit_orders,
                self.settings.rate_limit_other,
            ),
        )

        self._session: aiohttp.ClientSession | None = None
        self._auth_token: str | None = None
        self._logger = logging.getLogger(f"emag.{account_type.value}")
        self._circuit_state = {
            "open": False,
            "opened_at": None,
            "failure_count": 0,
            "last_failure": None,
        }

    @property
    def base_url(self) -> str:
        """Get the base URL for the API."""
        return self.settings.api_base_url

    @property
    def session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp ClientSession."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                base_url=self.base_url,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=aiohttp.ClientTimeout(
                    total=self.settings.api_timeout,
                    connect=5.0,
                    sock_connect=5.0,
                    sock_read=30.0,
                ),
            )
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self) -> "EmagAPIClient[T]":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def _get_auth_token(self) -> str:
        """Get or refresh the authentication token."""
        if self._auth_token:
            return self._auth_token

        auth_str = f"{self.account_config.username}:{self.account_config.password}"
        self._auth_token = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        return self._auth_token

    def _check_circuit_breaker(self) -> None:
        """Check if the circuit breaker is open and should be tripped."""
        if not self._circuit_state["open"]:
            return

        # If circuit is open, check if we should try to close it
        opened_at = self._circuit_state.get("opened_at")
        if opened_at:
            if opened_at.tzinfo is None:
                opened_at = opened_at.replace(tzinfo=UTC)
                self._circuit_state["opened_at"] = opened_at

            retry_after = min(
                300,  # Max 5 minutes
                2 ** (self._circuit_state["failure_count"] - 1),  # Exponential backoff
            )

            if (datetime.now(UTC) - opened_at) < timedelta(
                seconds=retry_after
            ):
                raise EmagNonRetryableError(
                    "Circuit breaker is open",
                    status_code=503,
                    details={"retry_after": retry_after},
                )

            # Half-open the circuit
            self._circuit_state["open"] = False

    def _record_failure(self) -> None:
        """Record a failed request and update circuit breaker state."""
        self._circuit_state["failure_count"] += 1
        self._circuit_state["last_failure"] = datetime.now(UTC)

        # Trip the circuit if we've had too many failures
        if self._circuit_state["failure_count"] >= 5:  # Threshold configurable
            self._circuit_state["open"] = True
            self._circuit_state["opened_at"] = datetime.now(UTC)

    def _record_success(self) -> None:
        """Record a successful request and reset circuit breaker state."""
        self._circuit_state.update(
            {"failure_count": 0, "open": False, "opened_at": None},
        )

    @retry(
        retry=retry_if_exception_type(EmagRetryableError),
        stop=stop_after_attempt(3),  # Configurable
        wait=wait_exponential_jitter(initial=0.5, max=30.0, jitter=0.1),
        before_sleep=before_sleep_log(logging.getLogger("emag.retry"), logging.WARNING),
        reraise=True,
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        response_model: type[T] | None = None,
        is_order_endpoint: bool = False,
        **kwargs: Any,
    ) -> T:
        """Make an authenticated request to the eMAG API with rate limiting and retries.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint path (e.g., '/order/read')
            data: Request body data (will be JSON-serialized)
            params: Query parameters
            response_model: Pydantic model to parse the response into
            is_order_endpoint: Whether this is an order-related endpoint (different rate limits)
            **kwargs: Additional arguments to pass to aiohttp.ClientSession.request

        Returns:
            Parsed response data as the specified model or raw dict if no model provided

        Raises:
            EmagAuthError: If authentication fails
            EmagRateLimitError: If rate limits are exceeded
            EmagAPIError: For other API errors
            aiohttp.ClientError: For network-related errors
            params: Query parameters
            response_model: Pydantic model to parse the response into
            is_order_endpoint: Whether this is an order-related endpoint (for rate limiting)

        Returns:
            Parsed response data

            EmagError: For any API errors

        """
        url = urljoin(self.base_url, endpoint)

        # Check circuit breaker first
        self._check_circuit_breaker()

        # Get rate limit key based on endpoint type
        _rate_limit_key = "orders" if is_order_endpoint else "other"

        # Apply rate limiting with jitter
        # Use secrets for cryptographically secure random jitter
        random_gen = secrets.SystemRandom()
        _jitter = 1.0 + (random_gen.random() * 0.1)  # 0-10% jitter
        await self._rate_limiter.acquire()

        # Get auth token
        try:
            auth_token = await self._get_auth_token()
        except Exception as e:
            self._logger.error(f"Authentication failed: {e!s}")
            self._record_failure()
            raise EmagAuthError("Authentication failed") from e

        # Prepare headers
        headers = {
            "Authorization": f"Basic {auth_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Request-ID": str(uuid.uuid4()),
            "X-Client-Id": self.account_config.username,
        }
        headers.update(kwargs.pop("headers", {}))

        # Make the request
        url = urljoin(self.base_url, endpoint.lstrip("/"))

        try:
            start_time = datetime.now(UTC)

            async with self.session.request(
                method,
                url,
                json=data,
                params=params,
                headers=headers,
                **kwargs,
            ) as response:
                # Log request metrics
                duration = (datetime.now(UTC) - start_time).total_seconds()
                self._logger.debug(
                    "%s %s - %d (%.3fs)",
                    method.upper(),
                    url,
                    response.status,
                    duration,
                )

                # Handle error responses
                if response.status >= 400:
                    error_text = await response.text()

                    if response.status == 401:
                        self._auth_token = None  # Force token refresh on next request
                        self._record_failure()
                        raise EmagAuthError(
                            "Authentication failed. Please check your credentials.",
                        )
                    if response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", "1"))
                        error = EmagRateLimitError("Rate limit exceeded")
                        error.details["retry_after"] = retry_after
                        self._record_failure()
                        raise error
                    try:
                        error_data = await response.json()
                        error_msg = error_data.get("message", error_text)
                        if error_data.get("isError", False):
                            error_messages = error_data.get(
                                "messages",
                                [{"message": "Unknown error from eMAG API"}],
                            )
                            if isinstance(error_messages, list) and error_messages:
                                first_msg = error_messages[0]
                                if isinstance(first_msg, dict):
                                    error_msg = first_msg.get(
                                        "message", "Unknown error"
                                    )
                                else:
                                    error_msg = str(first_msg)
                            elif isinstance(error_messages, dict):
                                error_msg = error_messages.get(
                                    "message", "Unknown error"
                                )
                            else:
                                error_msg = str(error_messages)
                    except ValueError:
                        error_msg = error_text

                    # For server errors, raise a retryable error
                    if 500 <= response.status < 600:
                        self._record_failure()
                        raise EmagRetryableError(
                            f"Server error: {error_msg}",
                            status_code=response.status,
                        )
                    self._record_failure()
                    raise EmagAPIError(
                        f"API error: {error_msg}",
                        status_code=response.status,
                    )

                # Parse successful response
                try:
                    response_data = await response.json()
                except ValueError as e:
                    self._record_failure()
                    raise EmagError(f"Failed to parse JSON response: {e}") from e

                # VALIDARE CRITICĂ: Verifică isError conform API v4.4.8
                if isinstance(response_data, dict):
                    is_error = response_data.get("isError", False)
                    if is_error:
                        error_messages = response_data.get("messages", [])
                        error_msg = "API returned isError=true without details"

                        if isinstance(error_messages, list) and error_messages:
                            first_msg = error_messages[0]
                            if isinstance(first_msg, dict):
                                error_msg = first_msg.get(
                                    "message",
                                    "Unknown API error",
                                )
                            else:
                                error_msg = str(first_msg)
                        elif isinstance(error_messages, dict):
                            error_msg = error_messages.get("message", error_msg)
                        elif error_messages:
                            error_msg = str(error_messages)

                        self._logger.error(f"eMAG API Error: {error_msg}")
                        self._record_failure()
                        raise EmagAPIError(
                            f"eMAG API error: {error_msg}",
                            status_code=400,
                            details=response_data,
                        )

                    self._logger.debug("✅ eMAG API response validated: isError=false")

                # Log the response
                self._logger.debug("API response: %s", response_data)

                self._record_success()

                # Validate and parse response if a model is provided
                if response_model:
                    try:
                        if isinstance(response_data, dict):
                            return response_model(**response_data)
                        if isinstance(response_data, list):
                            return cast(
                                "T",
                                [response_model(**item) for item in response_data],
                            )
                        return cast("T", response_model(response_data))
                    except Exception as e:
                        raise EmagError(
                            f"Failed to parse response into {response_model.__name__}: {e}",
                        ) from e

                return cast("T", response_data)

        except aiohttp.ClientError as e:
            self._logger.error("Network error during API request: %s", str(e))
            self._record_failure()
            raise EmagError(f"Network error: {e!s}") from e
        except EmagError:
            self._record_failure()
            raise
        except Exception as e:
            self._logger.exception("Unexpected error during API request")
            self._record_failure()
            raise EmagError(f"Unexpected error: {e!s}") from e

    # Convenience methods for common HTTP methods

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        response_model: type[T] | None = None,
        is_order_endpoint: bool = False,
    ) -> T:
        """Make a GET request."""
        return await self._make_request(
            "GET",
            endpoint,
            params=params,
            response_model=response_model,
            is_order_endpoint=is_order_endpoint,
        )

    async def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        response_model: type[T] | None = None,
        is_order_endpoint: bool = False,
    ) -> T:
        """Make a POST request."""
        return await self._make_request(
            "POST",
            endpoint,
            data=data,
            params=params,
            response_model=response_model,
            is_order_endpoint=is_order_endpoint,
        )

    async def put(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        response_model: type[T] | None = None,
        is_order_endpoint: bool = False,
    ) -> T:
        """Make a PUT request."""
        return await self._make_request(
            "PUT",
            endpoint,
            data=data,
            params=params,
            response_model=response_model,
            is_order_endpoint=is_order_endpoint,
        )

    async def delete(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        response_model: type[T] | None = None,
        is_order_endpoint: bool = False,
    ) -> T:
        """Make a DELETE request."""
        return await self._make_request(
            "DELETE",
            endpoint,
            params=params,
            response_model=response_model,
            is_order_endpoint=is_order_endpoint,
        )

    async def get_paginated(
        self,
        endpoint: str,
        response_model: type[T],
        cursor: str | None = None,
        limit: int = 100,
        is_order_endpoint: bool = False,
        **kwargs: Any,
    ) -> T:
        """Make a GET request with cursor-based pagination support.

        Args:
            endpoint: API endpoint path
            response_model: Pydantic model for the response items
            cursor: Optional cursor for pagination
            limit: Maximum number of items to return per page
            is_order_endpoint: Whether this is an order-related endpoint
            **kwargs: Additional parameters to pass to the request

        Returns:
            Response object with pagination metadata

        Raises:
            EmagError: If there's an error with the request

        """
        params = kwargs.pop("params", {})
        if cursor:
            params["cursor"] = cursor
        if limit:
            params["limit"] = min(limit, 1000)  # Enforce max limit

        response = await self.get(
            endpoint=endpoint,
            params=params,
            response_model=response_model,
            is_order_endpoint=is_order_endpoint,
            **kwargs,
        )

        return response

    async def iterate_all_pages(
        self,
        endpoint: str,
        response_model: type[T],
        limit: int = 100,
        is_order_endpoint: bool = False,
        **kwargs: Any,
    ) -> T:
        """Iterate through all pages of a paginated endpoint.

        Args:
            endpoint: API endpoint path
            response_model: Pydantic model for the response items
            limit: Number of items to fetch per page
            is_order_endpoint: Whether this is an order-related endpoint
            **kwargs: Additional parameters to pass to each request

        Yields:
            Items from each page of results

        """
        cursor = None

        while True:
            response = await self.get_paginated(
                endpoint=endpoint,
                response_model=response_model,
                cursor=cursor,
                limit=limit,
                is_order_endpoint=is_order_endpoint,
                **kwargs,
            )

            # Yield results from current page
            if hasattr(response, "results") and response.results:
                for item in response.results:
                    yield item

            # Check if there are more pages
            if not hasattr(response, "has_next_page") or not response.has_next_page():
                break

            # Update cursor for next page
            if hasattr(response, "next_cursor") and response.next_cursor:
                cursor = response.next_cursor
            else:
                break
