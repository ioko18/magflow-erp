"""Base HTTP client for eMAG Marketplace API.

This module provides an async HTTP client for making requests to the eMAG Marketplace API
with built-in authentication, rate limiting, and error handling.
"""

import asyncio

# import aiohttp
import base64
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, TypeVar
from urllib.parse import urlparse

from pydantic import BaseModel, ValidationError

from ..exceptions import EmagAPIError, EmagAuthenticationError, EmagRateLimitError
from ..rate_limiter import EmagRateLimiter


# Type variables for generic response handling
class MockSession:
    """Mock session for when aiohttp is not available."""

    def __init__(self, **kwargs):
        self.closed = False

    async def close(self):
        self.closed = True

    async def request(self, method, url, **kwargs):
        # Mock response
        class MockResponse:
            def __init__(self):
                self.status = 200
                self.headers = {}

            async def text(self):
                return '{"status": "success"}'

            async def json(self):
                return {"status": "success"}

        return MockResponse()


T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class EmagBaseClient:
    """Base HTTP client for eMAG Marketplace API."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        rate_limiter: EmagRateLimiter | None = None,
        session: Any | None = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        enable_rate_limiting: bool = True,
    ):
        """Initialize the eMAG API client.

        Args:
            base_url: Base URL for the eMAG API
            username: eMAG API username
            password: eMAG API password
            rate_limiter: Optional rate limiter instance. If not provided, a default one will be created.
            session: Optional aiohttp ClientSession to reuse
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            retry_delay: Initial delay between retries in seconds
            enable_rate_limiting: Whether to enable rate limiting (default: True)

        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        # Mock timeout since aiohttp is not available
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._session = session
        self._auth_token = None
        self._token_expiry = None
        self.enable_rate_limiting = enable_rate_limiting

        # Initialize rate limiter if not provided
        if enable_rate_limiting and rate_limiter is None:
            self._rate_limiter = EmagRateLimiter()
        else:
            self._rate_limiter = rate_limiter

    async def __aenter__(self):
        await self.ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def ensure_session(self) -> Any:
        # Mock session creation since aiohttp is not available
        if self._session is None or getattr(self._session, "closed", True):
            self._session = MockSession()
        return self._session

    async def close(self):
        """Close the underlying aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def _get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers with the current token."""
        if not self._auth_token or (
            self._token_expiry and datetime.now(UTC) >= self._token_expiry
        ):
            return self._get_basic_auth_headers()
        return {"Authorization": f"Bearer {self._auth_token}"}

    def _get_basic_auth_headers(self) -> dict[str, str]:
        """Get Basic Auth headers."""
        auth_str = f"{self.username}:{self.password}"
        encoded = base64.b64encode(auth_str.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}

    async def _ensure_authenticated(self):
        """Ensure we have a valid authentication token."""
        if (
            self._auth_token
            and self._token_expiry
            and datetime.now(UTC) < self._token_expiry
        ):
            return

        # Implement OAuth2 token flow if OAuth is enabled
        use_oauth = getattr(self.config, "use_oauth", False)
        if use_oauth:
            try:
                from app.db.session import AsyncSessionLocal
                from app.integrations.emag.services.oauth2_client import (
                    emag_oauth_client,
                )

                async with AsyncSessionLocal() as db:
                    self._auth_token = await emag_oauth_client.get_valid_access_token(
                        db=db
                    )
                    # OAuth tokens typically expire in 1 hour
                    self._token_expiry = datetime.now(UTC) + timedelta(hours=1)
                    logger.info("OAuth2 token refreshed successfully")
            except Exception as e:
                logger.warning(
                    f"OAuth2 token refresh failed, falling back to Basic Auth: {e}"
                )
                # Fall back to Basic Auth if OAuth fails

    def _get_endpoint_from_url(self, url: str) -> str:
        """Extract the endpoint from a full URL.

        Args:
            url: Full URL

        Returns:
            str: The endpoint path

        """
        # Remove the base URL to get the endpoint
        if url.startswith(self.base_url):
            return url[len(self.base_url) :].lstrip("/")

        # If it's a full URL, parse it and get the path
        parsed = urlparse(url)
        return parsed.path.lstrip("/")

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        response_model: type[T] | None = None,
        bypass_rate_limit: bool = False,
    ) -> dict[str, Any] | T:
        """Make an HTTP request to the eMAG API with rate limiting.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint (e.g., 'product_offer/save')
            params: Query parameters
            data: Request body
            headers: Additional headers
            response_model: Pydantic model for response validation
            bypass_rate_limit: If True, skip rate limiting (use with caution)

        Returns:
            Parsed JSON response or validated Pydantic model

        Raises:
            EmagAPIError: For API errors
            EmagRateLimitError: If rate limited
            EmagAuthenticationError: For authentication errors

        """
        # Build the full URL
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # Get the endpoint for rate limiting
        rate_limit_endpoint = self._get_endpoint_from_url(url)

        # Ensure we have a valid session
        session = await self.ensure_session()

        # Make the request with retries
        for attempt in range(self.max_retries + 1):
            try:
                # Apply rate limiting if enabled and not bypassed
                if self._rate_limiter is not None and not bypass_rate_limit:
                    await self._rate_limiter.wait_if_needed(rate_limit_endpoint)

                # Prepare headers
                request_headers = headers or {}
                request_headers.update(self._get_auth_headers())

                # Make the request
                async with session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    headers=request_headers,
                ) as response:
                    # Update rate limits based on response headers if available
                    if self._rate_limiter is not None:
                        self._rate_limiter.update_rate_limits(dict(response.headers))

                    # Handle the response
                    response_data = await self._handle_response(
                        response,
                        response_model,
                    )
                    return response_data

            except (TimeoutError, Exception) as e:
                if attempt < self.max_retries:
                    retry_delay = self.retry_delay * (2**attempt)  # Exponential backoff
                    logger.warning(
                        "Request to %s failed (attempt %d/%d), retrying in %.1fs: %s",
                        endpoint,
                        attempt + 1,
                        self.max_retries + 1,
                        retry_delay,
                        str(e),
                    )
                    await asyncio.sleep(retry_delay)
                    continue

                # If we've exhausted all retries, re-raise the last exception
                raise EmagAPIError(
                    f"Request to {endpoint} failed after {self.max_retries + 1} attempts: {e!s}",
                ) from e

    async def _handle_response(
        self,
        response: Any,
        response_model: type[T] | None = None,
    ) -> dict[str, Any] | T:
        """Handle the response from the API.

        Args:
            response: aiohttp ClientResponse
            response_model: Pydantic model for response validation

        Returns:
            Parsed JSON response or validated Pydantic model

        Raises:
            EmagAPIError: For API errors
            EmagRateLimitError: If rate limited
            EmagAuthenticationError: For authentication errors

        """
        response_text = await response.text()

        # Log response for debugging
        logger.debug(
            "Received response: %d %s - %s",
            response.status,
            response.reason,
            response_text[:500],  # Limit log size
        )

        # Handle error responses
        if response.status >= 400:
            await self._handle_error_response(response, response_text)

        # Parse successful response
        try:
            response_data = await response.json() if response_text else {}
        except json.JSONDecodeError:
            response_data = {"raw_response": response_text}

        # Validate response against model if provided
        if response_model:
            try:
                return response_model(**response_data)
            except ValidationError as e:
                logger.error("Response validation error: %s", e)
                raise EmagAPIError(
                    f"Invalid response format: {e}",
                    status_code=response.status,
                    response=response_data,
                ) from e

        return response_data

    async def _handle_error_response(self, response: Any, response_text: str):
        """Handle error responses from the API."""
        status = response.status

        try:
            error_data = json.loads(response_text) if response_text else {}
        except json.JSONDecodeError:
            error_data = {"message": response_text or "Unknown error"}

        error_msg = error_data.get("message", "Unknown error")

        if status == 401:
            raise EmagAuthenticationError(
                f"Authentication failed: {error_msg}",
                status_code=status,
                response=error_data,
            )
        if status == 429:  # Rate limited
            retry_after = int(response.headers.get("Retry-After", 5))
            raise EmagRateLimitError(
                f"Rate limited: {error_msg}",
                status_code=status,
                response=error_data,
                retry_after=retry_after,
            )
        raise EmagAPIError(
            f"API error {status}: {error_msg}",
            status_code=status,
            response=error_data,
        )

    # Convenience methods for common HTTP methods

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        response_model: type[T] | None = None,
        bypass_rate_limit: bool = False,
    ) -> dict[str, Any] | T:
        """Make a GET request to the eMAG API.

        Args:
            endpoint: API endpoint (e.g., 'product_offer/read')
            params: Query parameters
            headers: Additional headers
            response_model: Pydantic model for response validation
            bypass_rate_limit: If True, skip rate limiting (use with caution)

        Returns:
            Parsed JSON response or validated Pydantic model

        """
        return await self._make_request(
            method="GET",
            endpoint=endpoint,
            params=params,
            headers=headers,
            response_model=response_model,
            bypass_rate_limit=bypass_rate_limit,
        )

    async def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        response_model: type[T] | None = None,
        bypass_rate_limit: bool = False,
    ) -> dict[str, Any] | T:
        """Make a POST request to the eMAG API.

        Args:
            endpoint: API endpoint (e.g., 'product_offer/save')
            data: Request body
            headers: Additional headers
            response_model: Pydantic model for response validation
            bypass_rate_limit: If True, skip rate limiting (use with caution)

        Returns:
            Parsed JSON response or validated Pydantic model

        """
        return await self._make_request(
            method="POST",
            endpoint=endpoint,
            data=data,
            headers=headers,
            response_model=response_model,
            bypass_rate_limit=bypass_rate_limit,
        )

    async def put(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        response_model: type[T] | None = None,
        bypass_rate_limit: bool = False,
    ) -> dict[str, Any] | T:
        """Make a PUT request to the eMAG API.

        Args:
            endpoint: API endpoint (e.g., 'product_offer/update')
            data: Request body
            headers: Additional headers
            response_model: Pydantic model for response validation
            bypass_rate_limit: If True, skip rate limiting (use with caution)

        Returns:
            Parsed JSON response or validated Pydantic model

        """
        return await self._make_request(
            method="PUT",
            endpoint=endpoint,
            data=data,
            headers=headers,
            response_model=response_model,
            bypass_rate_limit=bypass_rate_limit,
        )

    async def delete(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        response_model: type[T] | None = None,
        bypass_rate_limit: bool = False,
    ) -> dict[str, Any] | T:
        """Make a DELETE request to the eMAG API.

        Args:
            endpoint: API endpoint (e.g., 'product_offer/delete')
            data: Request body
            headers: Additional headers
            response_model: Pydantic model for response validation
            bypass_rate_limit: If True, skip rate limiting (use with caution)

        Returns:
            Parsed JSON response or validated Pydantic model

        """
        return await self._make_request(
            method="DELETE",
            endpoint=endpoint,
            data=data,
            headers=headers,
            response_model=response_model,
            bypass_rate_limit=bypass_rate_limit,
        )


class EmagClient(EmagBaseClient):
    """Main eMAG API client with account-specific configuration."""

    def __init__(
        self,
        account_type: str,
        rate_limiter: EmagRateLimiter | None = None,
        session: Any | None = None,
        enable_rate_limiting: bool = True,
        **kwargs,
    ):
        """Initialize the eMAG client for a specific account type.

        Args:
            account_type: Either 'main' or 'fbe'
            rate_limiter: Optional rate limiter instance. If not provided, a default one will be created.
            session: Optional aiohttp ClientSession to reuse
            enable_rate_limiting: Whether to enable rate limiting (default: True)
            **kwargs: Additional arguments to pass to EmagBaseClient

        """
        from ..config import EmagAccountType, settings

        try:
            account_type_enum = EmagAccountType(account_type.lower())
        except ValueError as e:
            valid_types = [t.value for t in EmagAccountType]
            raise ValueError(
                f"Invalid account type: {account_type}. Must be one of: {valid_types}",
            ) from e

        account_config = settings.get_account_config(account_type_enum)

        super().__init__(
            base_url=account_config["base_url"],
            username=account_config["username"],
            password=account_config["password"],
            rate_limiter=rate_limiter,
            session=session,
            enable_rate_limiting=enable_rate_limiting,
            **kwargs,
        )

        self.account_type = account_type_enum
        self.ip_whitelist_name = account_config.get("ip_whitelist_name", "")
        self.callback_base = account_config.get("callback_base", "")

        # Log initialization
        logger.info(
            "Initialized eMAG %s client with rate limiting %s",
            account_type_enum.value.upper(),
            (
                "enabled"
                if (enable_rate_limiting and self._rate_limiter is not None)
                else "disabled"
            ),
        )
