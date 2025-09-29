"""
Enhanced eMAG API Client with improved error handling and retry logic.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import aiohttp
from aiohttp import ClientSession, ClientResponseError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

logger = logging.getLogger(__name__)


class EmagApiError(Exception):
    """Base exception for eMAG API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[dict] = None,
    ):
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class EmagApiClient:
    """eMAG API client with retry and rate limiting support."""

    # Default retry policy (can be overridden in __init__)
    _default_retry_policy = {
        "stop": stop_after_attempt(3),
        "wait": wait_exponential(multiplier=1, min=4, max=10),
        "retry": retry_if_exception_type(
            (
                aiohttp.ClientError,
                asyncio.TimeoutError,
            )
        ),
        "before_sleep": before_sleep_log(logger, logging.WARNING),
        "reraise": True,
    }

    def __init__(
        self,
        username: str,
        password: str,
        base_url: str = "https://marketplace-api.emag.ro/api-3",
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """Initialize the eMAG API client.

        Args:
            username: eMAG API username/email
            password: eMAG API password
            base_url: Base URL for the eMAG API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.username = username
        self.password = password
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self._session: Optional[ClientSession] = None
        self._auth = aiohttp.BasicAuth(username, password)

        # Configure retry policy
        self.retry_policy = self._default_retry_policy.copy()
        self.retry_policy["stop"] = stop_after_attempt(max_retries)

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def start(self):
        """Initialize the HTTP session."""
        if self._session is None or self._session.closed:
            self._session = ClientSession(
                auth=self._auth,
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an HTTP request with retry logic."""
        if self._session is None or self._session.closed:
            await self.start()

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            async with self._session.request(method, url, **kwargs) as response:
                response.raise_for_status()

                # Handle empty responses
                content = await response.text()
                if not content.strip():
                    return {}

                data = await response.json()

                # Check for eMAG API errors
                if isinstance(data, dict) and data.get("isError", False):
                    error_msg = data.get("messages", ["Unknown error"])[0]
                    raise EmagApiError(
                        f"eMAG API error: {error_msg}",
                        status_code=response.status,
                        response=data,
                    )

                return data

        except ClientResponseError as e:
            error_msg = str(e)
            try:
                error_data = await response.json()
                if (
                    isinstance(error_data, dict)
                    and "messages" in error_data
                    and error_data["messages"]
                ):
                    error_msg = error_data["messages"][0]
                elif isinstance(error_data, dict) and "message" in error_data:
                    error_msg = error_data["message"]
                elif isinstance(error_data, str):
                    error_msg = error_data
            except (
                aiohttp.ClientError,
                ValueError,
                KeyError,
                IndexError,
            ) as parse_error:
                logger.warning(f"Failed to parse error response: {parse_error}")

            raise EmagApiError(
                f"HTTP {e.status}: {error_msg}",
                status_code=e.status,
                response=getattr(e, "response", None),
            ) from e

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            raise EmagApiError(f"Request failed: {str(e)}") from e

    async def get_products(
        self, page: int = 1, items_per_page: int = 100, filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get a list of products from eMAG."""
        params = {
            "currentPage": page,
            "itemsPerPage": items_per_page,
        }
        
        # Add filters if provided
        if filters:
            # Handle status filter
            if "status" in filters:
                status_value = filters["status"]
                if status_value == "all":
                    # Don't add status filter to get all products
                    pass
                elif status_value == "active":
                    params["status"] = 1  # eMAG uses 1 for active
                elif status_value == "inactive":
                    params["status"] = 0  # eMAG uses 0 for inactive
                else:
                    params["status"] = status_value
            
            # Add other filters
            for key, value in filters.items():
                if key != "status":  # Already handled above
                    params[key] = value
        
        return await self._request("GET", "product_offer/read", params=params)

    async def get_orders(
        self,
        status: str = "new",
        page: int = 1,
        items_per_page: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get a list of orders from eMAG.

        Args:
            status: Order status filter (e.g., 'new', 'in_progress', 'delivered')
            page: Page number for pagination
            items_per_page: Number of items per page
            start_date: Filter orders created after this date
            end_date: Filter orders created before this date

        Returns:
            Dictionary containing the API response
        """
        params = {
            "status": status,
            "currentPage": page,
            "itemsPerPage": items_per_page,
        }
        return await self._request("GET", "order/read", params=params)

    async def update_stock(self, product_id: str, quantity: int) -> Dict[str, Any]:
        """Update product stock in eMAG."""
        data = [
            {
                "id": product_id,
                "sale_stock": quantity,
            }
        ]
        return await self._request("POST", "stock_offer/save", json=data)


# Example usage:
# async def example():
#     async with EmagApiClient('username', 'password') as client:
#         try:
#             products = await client.get_products()
#             print(f"Found {len(products.get('results', []))} products")
#         except EmagApiError as e:
#             print(f"Error: {e}")
