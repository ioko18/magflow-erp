"""
eMAG Reference Data Service - v4.4.9

Handles fetching and caching VAT rates and handling times.
These are required for creating offers.
"""

from datetime import datetime, timedelta
from typing import Any

from app.config.emag_config import get_emag_config
from app.core.emag_validator import validate_emag_response
from app.core.exceptions import ServiceError
from app.core.logging import get_logger
from app.services.emag.emag_api_client import EmagApiClient, EmagApiError

logger = get_logger(__name__)


class EmagReferenceDataService:
    """
    Service for managing eMAG reference data (VAT rates, handling times).

    This data is required when creating offers and changes infrequently,
    so it's cached for performance.
    """

    def __init__(self, account_type: str = "main"):
        """
        Initialize Reference Data Service.

        Args:
            account_type: Type of eMAG account ('main' or 'fbe')
        """
        self.account_type = account_type
        self.config = get_emag_config(account_type)
        self.client = EmagApiClient(
            username=self.config.api_username,
            password=self.config.api_password,
            base_url=self.config.base_url,
            timeout=self.config.api_timeout,
            max_retries=self.config.max_retries,
        )
        self._vat_cache: list[dict[str, Any]] = []
        self._handling_time_cache: list[dict[str, Any]] = []
        self._cache_timestamp: datetime | None = None
        self._cache_ttl = timedelta(days=7)  # Cache for 7 days

        logger.info("Initialized EmagReferenceDataService for %s account", account_type)

    async def initialize(self):
        """Initialize the service."""
        await self.client.start()

    async def close(self):
        """Close the service and cleanup resources."""
        await self.client.close()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self._cache_timestamp:
            return False
        return datetime.now() - self._cache_timestamp < self._cache_ttl

    async def get_vat_rates(self, use_cache: bool = True) -> list[dict[str, Any]]:
        """
        Get available VAT rates.

        Args:
            use_cache: Whether to use cached data

        Returns:
            List of VAT rate objects

        Raises:
            ServiceError: If fetching fails
        """
        # Return cached data if valid
        if use_cache and self._is_cache_valid() and self._vat_cache:
            logger.debug("Returning cached VAT rates")
            return self._vat_cache

        try:
            logger.info("Fetching VAT rates from eMAG")

            response = await self.client.get_vat_rates()

            validate_emag_response(response, "vat/read", "get_vat_rates")

            vat_rates = response.get("results", [])

            # Cache the results
            if use_cache:
                self._vat_cache = vat_rates
                if not self._cache_timestamp:
                    self._cache_timestamp = datetime.now()

            logger.info("Fetched %d VAT rates", len(vat_rates))
            return vat_rates

        except EmagApiError as e:
            logger.error("Failed to fetch VAT rates: %s", str(e))
            raise ServiceError(f"VAT rates fetch failed: {str(e)}") from e

    async def get_vat_rate_by_id(self, vat_id: int) -> dict[str, Any] | None:
        """
        Get specific VAT rate by ID.

        Args:
            vat_id: VAT rate ID

        Returns:
            VAT rate object or None if not found

        Raises:
            ServiceError: If fetching fails
        """
        vat_rates = await self.get_vat_rates()

        for vat in vat_rates:
            if vat.get("id") == vat_id:
                return vat

        return None

    async def get_handling_times(self, use_cache: bool = True) -> list[dict[str, Any]]:
        """
        Get available handling time values.

        Args:
            use_cache: Whether to use cached data

        Returns:
            List of handling time objects

        Raises:
            ServiceError: If fetching fails
        """
        # Return cached data if valid
        if use_cache and self._is_cache_valid() and self._handling_time_cache:
            logger.debug("Returning cached handling times")
            return self._handling_time_cache

        try:
            logger.info("Fetching handling times from eMAG")

            response = await self.client.get_handling_times()

            validate_emag_response(response, "handling_time/read", "get_handling_times")

            handling_times = response.get("results", [])

            # Cache the results
            if use_cache:
                self._handling_time_cache = handling_times
                if not self._cache_timestamp:
                    self._cache_timestamp = datetime.now()

            logger.info("Fetched %d handling times", len(handling_times))
            return handling_times

        except EmagApiError as e:
            logger.error("Failed to fetch handling times: %s", str(e))
            raise ServiceError(f"Handling times fetch failed: {str(e)}") from e

    async def get_handling_time_by_value(self, value: int) -> dict[str, Any] | None:
        """
        Get specific handling time by value (days).

        Args:
            value: Number of days

        Returns:
            Handling time object or None if not found

        Raises:
            ServiceError: If fetching fails
        """
        handling_times = await self.get_handling_times()

        for ht in handling_times:
            if ht.get("value") == value:
                return ht

        return None

    async def refresh_all_cache(self) -> dict[str, Any]:
        """
        Refresh all cached reference data.

        Returns:
            Dictionary with refresh results

        Raises:
            ServiceError: If refresh fails
        """
        try:
            logger.info("Refreshing all reference data cache")

            # Fetch fresh data
            vat_rates = await self.get_vat_rates(use_cache=False)
            handling_times = await self.get_handling_times(use_cache=False)

            self._cache_timestamp = datetime.now()

            result = {
                "success": True,
                "timestamp": self._cache_timestamp.isoformat(),
                "vat_rates_count": len(vat_rates),
                "handling_times_count": len(handling_times),
                "cache_valid_until": (
                    self._cache_timestamp + self._cache_ttl
                ).isoformat(),
            }

            logger.info("Cache refreshed successfully")
            return result

        except Exception as e:
            logger.error("Failed to refresh cache: %s", str(e))
            raise ServiceError(f"Cache refresh failed: {str(e)}") from e

    def clear_cache(self):
        """Clear all cached data."""
        self._vat_cache.clear()
        self._handling_time_cache.clear()
        self._cache_timestamp = None
        logger.info("Reference data cache cleared")

    def get_cache_info(self) -> dict[str, Any]:
        """
        Get information about cache status.

        Returns:
            Dictionary with cache information
        """
        return {
            "is_valid": self._is_cache_valid(),
            "timestamp": self._cache_timestamp.isoformat()
            if self._cache_timestamp
            else None,
            "valid_until": (
                (self._cache_timestamp + self._cache_ttl).isoformat()
                if self._cache_timestamp
                else None
            ),
            "vat_rates_cached": len(self._vat_cache),
            "handling_times_cached": len(self._handling_time_cache),
            "ttl_days": self._cache_ttl.days,
        }
