"""Fixed eMAG API Client with proper authentication and endpoints."""

import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, TypeVar

import aiohttp
import backoff

logger = logging.getLogger(__name__)

T = TypeVar("T")


class EmagAccountType(str, Enum):
    """eMAG account types."""

    MAIN = "main"
    FBE = "fbe"


class EmagAPIError(Exception):
    """Custom exception for eMAG API errors."""

    def __init__(
        self,
        message: str,
        status_code: int = None,
        response_data: dict = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class RateLimitTracker:
    """Track rate limits for eMAG API endpoints."""

    def __init__(self):
        self.limits = {
            "orders": 12,
            "offers": 3,
            "rma": 5,
            "invoices": 3,
            "other": 3,
        }
        self.buckets: dict[str, dict] = {}

    def can_make_request(self, endpoint: str) -> bool:
        """Check if we can make a request."""
        category = (
            "orders"
            if "order" in endpoint
            else (
                "offers"
                if "offer" in endpoint or "product" in endpoint
                else "invoices"
                if "invoice" in endpoint
                else "other"
            )
        )

        now = datetime.now(UTC)
        bucket = self.buckets.setdefault(category, {"count": 0, "window_start": now})

        if now - bucket["window_start"] >= timedelta(seconds=1):
            bucket["count"] = 0
            bucket["window_start"] = now

        return bucket["count"] < self.limits[category]

    def record_request(self, endpoint: str):
        """Record a request."""
        category = (
            "orders"
            if "order" in endpoint
            else (
                "offers"
                if "offer" in endpoint or "product" in endpoint
                else "invoices"
                if "invoice" in endpoint
                else "other"
            )
        )

        bucket = self.buckets.setdefault(
            category,
            {"count": 0, "window_start": datetime.now(UTC)},
        )
        bucket["count"] += 1


class EmagClient:
    """Fixed async eMAG API client with proper authentication."""

    def __init__(self, account_type: EmagAccountType = EmagAccountType.MAIN):
        self.account_type = account_type
        self.base_url = "https://marketplace-api.emag.ro/api-3"
        self.session: aiohttp.ClientSession | None = None
        self.rate_limiter = RateLimitTracker()

        # Load credentials from environment
        self.username = os.getenv("EMAG_API_USERNAME") or os.getenv(
            "EMAG_MAIN_USERNAME",
        )
        self.password = os.getenv("EMAG_API_PASSWORD") or os.getenv(
            "EMAG_MAIN_PASSWORD",
        )

        if not self.username or not self.password:
            raise ValueError("eMAG credentials not found in environment variables")

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def connect(self):
        """Initialize HTTP session."""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
            )
            logger.info("Connected to eMAG API")

    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError, EmagAPIError),
        max_tries=3,
        max_time=30,
        jitter=backoff.random_jitter,
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        response_model: type[T] | None = None,
    ) -> T:
        """Make authenticated request to eMAG API."""
        if not self.session:
            raise RuntimeError("eMAG client not connected")

        # Rate limiting
        if not self.rate_limiter.can_make_request(endpoint):
            await asyncio.sleep(0.1)

        # Prepare URL
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # Prepare authentication
        auth = aiohttp.BasicAuth(self.username, self.password)

        try:
            async with self.session.request(
                method=method,
                url=url,
                auth=auth,
                json=data,
                params=params,
            ) as response:
                self.rate_limiter.record_request(endpoint)

                # Handle HTTP errors
                if response.status >= 400:
                    error_data = (
                        await response.json() if response.content_length else {}
                    )
                    raise EmagAPIError(
                        f"eMAG API error: {response.status}",
                        status_code=response.status,
                        response_data=error_data,
                    )

                # Parse response
                response_data = await response.json()

                # Check for eMAG API errors
                if response_data.get("isError") is True:
                    error_messages = response_data.get("messages", ["Unknown error"])
                    raise EmagAPIError(
                        f"eMAG API returned error: {error_messages}",
                        response_data=response_data,
                    )

                return response_data

        except aiohttp.ClientError as e:
            logger.error(f"eMAG API request failed: {e!s}")
            raise EmagAPIError(f"Network error: {e!s}") from e

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        response_model: type[T] | None = None,
    ) -> T:
        """Make GET request."""
        return await self._make_request(
            "GET",
            endpoint,
            params=params,
            response_model=response_model,
        )

    async def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        response_model: type[T] | None = None,
    ) -> T:
        """Make POST request."""
        return await self._make_request(
            "POST",
            endpoint,
            data=data,
            response_model=response_model,
        )

    async def fetch_product_offers(
        self,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Fetch product offers using correct eMAG API format."""
        # Use the correct payload format: {"id": "product_id"} or {"id": ""}
        payload = filters or {"id": ""}
        return await self.post("product_offer/read", data=payload)

    async def get_product_details(self, product_id: str) -> dict[str, Any]:
        """Get details for a specific product."""
        payload = {"id": product_id}
        response = await self.post("product_offer/read", data=payload)

        if "results" in response and len(response["results"]) > 0:
            return response["results"][0]
        return {}

    async def test_connection(self) -> dict[str, Any]:
        """Test connection to eMAG API."""
        try:
            # Try to get product offers with empty ID
            response = await self.post("product_offer/read", data={"id": ""})
            if "isError" in response and not response["isError"]:
                return {
                    "status": "connected",
                    "account_type": self.account_type,
                    "message": "Successfully connected to eMAG API",
                }
            return {
                "status": "error",
                "account_type": self.account_type,
                "error": response.get("messages", ["Unknown error"]),
                "message": "Failed to connect to eMAG API",
            }
        except Exception as e:
            return {
                "status": "error",
                "account_type": self.account_type,
                "error": str(e),
                "message": "Failed to connect to eMAG API",
            }
