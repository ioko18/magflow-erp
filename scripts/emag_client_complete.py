"""Complete eMAG API client implementation with rate limiting and error handling."""

import asyncio
import base64
import json
import time
from collections import deque
from enum import Enum
from typing import Any, Dict, Optional, Type, TypeVar, cast, Deque
import aiohttp

# Type variable for response models
T = TypeVar("T")


class EmagAccountType(str, Enum):
    """eMAG account types."""

    MAIN = "main"
    FBE = "fbe"


class EmagAccountConfig:
    """Configuration for a single eMAG account."""

    def __init__(
        self,
        username: str,
        password: str,
        warehouse_id: int,
        ip_whitelist_name: str,
        callback_base: str,
    ):
        self.username = username
        self.password = password
        self.warehouse_id = warehouse_id
        self.ip_whitelist_name = ip_whitelist_name
        self.callback_base = callback_base


class EmagSettings:
    """eMAG API settings with rate limiting configuration."""

    def __init__(self):
        self.api_base_url = "https://marketplace-api.emag.pl/api-3"
        self.api_timeout = 30
        self.rate_limit_orders = 12  # requests per second for order endpoints
        self.rate_limit_other = 3  # requests per second for other endpoints
        self.retry_attempts = 3  # number of retry attempts for failed requests
        self.retry_delay = 1.0  # initial delay between retries in seconds
        self.jitter = 0.1  # jitter factor for retry delay

    def get_account_config(self, account_type: EmagAccountType) -> EmagAccountConfig:
        """Get configuration for the specified account type."""
        if account_type == EmagAccountType.MAIN:
            return EmagAccountConfig(
                username="test_main_user",
                password="test_main_pass",
                warehouse_id=1,
                ip_whitelist_name="test_whitelist",
                callback_base="https://test.com/emag",
            )
        else:  # FBE
            return EmagAccountConfig(
                username="test_fbe_user",
                password="test_fbe_pass",
                warehouse_id=2,
                ip_whitelist_name="test_fbe_whitelist",
                callback_base="https://test.com/emag/fbe",
            )


class RateLimiter:
    """Rate limiter for eMAG API requests with separate limits for order and other endpoints."""

    def __init__(self, orders_per_second: int, other_per_second: int):
        self.orders_per_second = orders_per_second
        self.other_per_second = other_per_second
        self.order_requests: Deque[float] = deque()
        self.other_requests: Deque[float] = deque()
        self.lock = asyncio.Lock()

    async def wait_if_needed(self, is_order_endpoint: bool = False) -> None:
        """Wait if rate limit would be exceeded for the given endpoint type."""
        async with self.lock:
            now = time.time()

            # Clean up old requests (older than 1 second)
            cutoff = now - 1.0

            if is_order_endpoint:
                while self.order_requests and self.order_requests[0] < cutoff:
                    self.order_requests.popleft()

                # If we've hit the rate limit, wait until the oldest request is older than 1 second
                if len(self.order_requests) >= self.orders_per_second:
                    sleep_time = 1.0 - (now - self.order_requests[0])
                    if sleep_time > 0:
                        await asyncio.sleep(sleep_time)

                self.order_requests.append(time.time())
            else:
                while self.other_requests and self.other_requests[0] < cutoff:
                    self.other_requests.popleft()

                if len(self.other_requests) >= self.other_per_second:
                    sleep_time = 1.0 - (now - self.other_requests[0])
                    if sleep_time > 0:
                        await asyncio.sleep(sleep_time)

                self.other_requests.append(time.time())


class EmagAPIError(Exception):
    """Base exception for eMAG API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        self.message = message
        super().__init__(self.message)


class EmagAuthError(EmagAPIError):
    """Authentication error (401)."""

    pass


class EmagRateLimitError(EmagAPIError):
    """Rate limit exceeded (429)."""

    pass


class EmagValidationError(EmagAPIError):
    """Validation error (400)."""

    pass


class EmagNotFoundError(EmagAPIError):
    """Resource not found (404)."""

    pass


class EmagClient:
    """eMAG API client with rate limiting and error handling."""

    def __init__(
        self,
        account_type: EmagAccountType = EmagAccountType.MAIN,
        settings: Optional[EmagSettings] = None,
        session: Optional[aiohttp.ClientSession] = None,
    ):
        self.settings = settings or EmagSettings()
        self.account_type = account_type
        self.account_config = self.settings.get_account_config(account_type)
        self.rate_limiter = RateLimiter(
            orders_per_second=self.settings.rate_limit_orders,
            other_per_second=self.settings.rate_limit_other,
        )
        self._session = session
        self._auth_token: Optional[str] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp ClientSession."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.settings.api_timeout)
            )
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def _get_auth_token(self) -> str:
        """Get or refresh the authentication token."""
        if self._auth_token:
            return self._auth_token

        auth_str = f"{self.account_config.username}:{self.account_config.password}"
        self._auth_token = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        return self._auth_token

    def _prepare_headers(
        self, headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Prepare headers for API requests."""
        default_headers = {
            "Authorization": f"Basic {self._get_auth_token()}",
            "X-Client-Id": self.account_config.username,
            "X-Client-IP": self.account_config.ip_whitelist_name or "0.0.0.0",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if headers:
            default_headers.update(headers)

        return default_headers

    def _build_url(self, endpoint: str) -> str:
        """Build the full URL for an API endpoint."""
        base_url = self.settings.api_base_url.rstrip("/")
        endpoint = endpoint.lstrip("/")
        return f"{base_url}/{endpoint}"

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        response_model: Optional[Type[T]] = None,
        is_order_endpoint: bool = False,
        retry_count: int = 0,
    ) -> T:
        """Make an authenticated request to the eMAG API with rate limiting and retries."""
        # Wait for rate limiting
        await self.rate_limiter.wait_if_needed(is_order_endpoint)

        # Prepare URL and headers
        url = self._build_url(endpoint)
        request_headers = self._prepare_headers(headers)

        # Log the request
        self._log_request(method, url, request_headers, data, params)

        # Make the request with retries
        session = await self._get_session()

        try:
            async with session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=request_headers,
                timeout=aiohttp.ClientTimeout(total=self.settings.api_timeout),
            ) as response:
                # Log the response
                response_data = await self._handle_response(response)
                self._log_response(response.status, response.headers, response_data)

                # Parse and validate the response
                if response_model:
                    if isinstance(response_data, dict):
                        return response_model(**response_data)
                    elif isinstance(response_data, list):
                        return [response_model(**item) for item in response_data]  # type: ignore
                    else:
                        return response_model(response_data)  # type: ignore

                return cast(T, response_data)

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if retry_count < self.settings.retry_attempts:
                # Exponential backoff with jitter
                delay = self.settings.retry_delay * (2**retry_count)
                jitter = (
                    delay
                    * self.settings.jitter
                    * (2 * (0.5 - (hash(f"{time.time()}") % 1000) / 1000))
                )
                await asyncio.sleep(delay + jitter)
                return await self._make_request(
                    method,
                    endpoint,
                    data,
                    params,
                    headers,
                    response_model,
                    is_order_endpoint,
                    retry_count + 1,
                )
            raise EmagAPIError(
                f"Request failed after {self.settings.retry_attempts} attempts: {str(e)}"
            )

    async def _handle_response(self, response: aiohttp.ClientResponse) -> Any:
        """Handle the API response and raise appropriate exceptions."""
        try:
            response_data = await response.json() if response.content_length else {}
        except (ValueError, aiohttp.ContentTypeError):
            response_data = {}

        if response.status == 401:
            self._auth_token = None  # Force token refresh on next request
            raise EmagAuthError(
                "Authentication failed. Please check your credentials.", 401
            )

        if response.status == 429:
            retry_after = int(response.headers.get("Retry-After", "1"))
            raise EmagRateLimitError(
                f"Rate limit exceeded. Please try again in {retry_after} seconds.", 429
            )

        if response.status == 400:
            error_msg = response_data.get("message", "Bad Request")
            raise EmagValidationError(error_msg, 400)

        if response.status == 404:
            raise EmagNotFoundError("The requested resource was not found.", 404)

        if response.status >= 400:
            error_msg = response_data.get(
                "message", f"API request failed with status {response.status}"
            )
            raise EmagAPIError(error_msg, response.status)

        return response_data

    # Convenience methods for common HTTP methods

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        response_model: Optional[Type[T]] = None,
        is_order_endpoint: bool = False,
    ) -> T:
        """Make a GET request."""
        return await self._make_request(
            "GET",
            endpoint,
            params=params,
            headers=headers,
            response_model=response_model,
            is_order_endpoint=is_order_endpoint,
        )

    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        response_model: Optional[Type[T]] = None,
        is_order_endpoint: bool = False,
    ) -> T:
        """Make a POST request."""
        return await self._make_request(
            "POST",
            endpoint,
            data=data,
            params=params,
            headers=headers,
            response_model=response_model,
            is_order_endpoint=is_order_endpoint,
        )

    async def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        response_model: Optional[Type[T]] = None,
        is_order_endpoint: bool = False,
    ) -> T:
        """Make a PUT request."""
        return await self._make_request(
            "PUT",
            endpoint,
            data=data,
            params=params,
            headers=headers,
            response_model=response_model,
            is_order_endpoint=is_order_endpoint,
        )

    async def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        response_model: Optional[Type[T]] = None,
        is_order_endpoint: bool = False,
    ) -> T:
        """Make a DELETE request."""
        return await self._make_request(
            "DELETE",
            endpoint,
            params=params,
            headers=headers,
            response_model=response_model,
            is_order_endpoint=is_order_endpoint,
        )

    # Helper methods for logging

    def _log_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        data: Any = None,
        params: Any = None,
    ) -> None:
        """Log the request details."""
        print("\n=== Request ===")
        print(f"{method} {url}")

        if params:
            print("Query Params:")
            for k, v in params.items():
                print(f"  {k}: {v}")

        print("Headers:")
        for k, v in headers.items():
            if k.lower() == "authorization":
                v = "Basic [REDACTED]"
            print(f"  {k}: {v}")

        if data is not None:
            print("Body:")
            print(json.dumps(data, indent=2, ensure_ascii=False))

    def _log_response(
        self, status_code: int, headers: Dict[str, str], data: Any = None
    ) -> None:
        """Log the response details."""
        print(f"\n=== Response ({status_code}) ===")
        print("Headers:")
        for k, v in headers.items():
            print(f"  {k}: {v}")

        if data is not None:
            print("Body:")
            print(json.dumps(data, indent=2, ensure_ascii=False))


# Example usage
async def main():
    """Example usage of the eMAG client."""
    async with EmagClient(account_type=EmagAccountType.MAIN) as client:
        try:
            # Example GET request
            response = await client.get(
                "/category/read", params={"page": 1, "per_page": 10}
            )
            print("Categories:", response)

            # Example POST request
            # new_product = await client.post(
            #     "/product_offer/save",
            #     data={"name": "Test Product", "price": 100, "stock": 10},
            #     is_order_endpoint=True
            # )
            # print("Created product:", new_product)

        except EmagAPIError as e:
            print(f"API Error: {e.status_code} - {e.message}")
        except Exception as e:
            print(f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
