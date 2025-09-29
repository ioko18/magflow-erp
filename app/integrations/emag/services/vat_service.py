"""VAT rate service with caching and business logic.

This module provides a service layer for managing VAT rates with support for:
- Caching to reduce API calls
- Fallback mechanisms
- Rate limiting and retries
- Input validation
- Business logic for VAT rate management
"""

from datetime import datetime, timezone
from typing import List, Optional, Union

import pytz  # Used for timezone handling in _is_rate_active

from app.core.logging import get_logger
from app.integrations.emag.cache import VatCache
from app.integrations.emag.client import EmagAPIClient
from app.integrations.emag.models.responses.vat import VatRate, VatResponse
from app.integrations.emag.services.exceptions import EmagAPIError

logger = get_logger(__name__)


class VatService:
    """Service for handling VAT rate operations with caching and business logic.

    This service provides methods to retrieve and manage VAT rates with built-in
    caching, error handling, and fallback mechanisms.
    """

    def __init__(self, emag_client: Optional[EmagAPIClient] = None):
        """Initialize the VAT service.

        Args:
            emag_client: Optional eMAG API client instance. If not provided,
                        a new one will be created with default settings.

        """
        self.emag_client = emag_client or EmagAPIClient()
        self._cache = VatCache()

    async def get_vat_rates(
        self,
        country_code: str = "RO",
        cursor: Optional[str] = None,
        limit: int = 100,
        force_refresh: bool = False,
        include_inactive: bool = False,
    ) -> VatResponse:
        """Get VAT rates for a specific country with caching and fallback.

        Args:
            country_code: ISO 2-letter country code (default: "RO")
            cursor: Pagination cursor for large result sets
            limit: Maximum number of results per page (default: 100, max: 500)
            force_refresh: If True, bypass cache and fetch fresh data
            include_inactive: If True, include inactive VAT rates

        Returns:
            VatResponse: Response containing VAT rates and pagination info

        Raises:
            ValueError: If country_code is invalid
            EmagAPIError: If there's an error fetching from the API

        """
        # Input validation with more detailed error messages
        if not isinstance(country_code, str):
            raise TypeError(
                f"Country code must be a string, got {type(country_code).__name__}",
            )

        country_code = country_code.strip().upper()
        if len(country_code) != 2 or not country_code.isalpha():
            raise ValueError("Country code must be a 2-letter ISO 3166-1 alpha-2 code")

        # Validate limit is within allowed range
        if not isinstance(limit, int) or limit < 1 or limit > 500:
            raise ValueError("Limit must be an integer between 1 and 500")

        # Validate cursor if provided
        if cursor is not None and not isinstance(cursor, str):
            raise TypeError("Cursor must be a string or None")

        country_code = country_code.upper()

        # Try to get from cache first if not forcing refresh
        cache_key = f"vat_rates:{country_code}"
        if not force_refresh:
            try:
                cached_response = await self._cache.get(cache_key)
                if cached_response:
                    try:
                        # Validate cached data before returning
                        if not isinstance(cached_response, VatResponse):
                            logger.warning("Invalid cache data format, forcing refresh")
                            raise ValueError("Invalid cache format")

                        logger.debug(f"Cache hit for VAT rates: {country_code}")
                        return cached_response
                    except Exception as e:
                        logger.warning(
                            f"Invalid cached data, forcing refresh: {e!s}",
                        )
                        # Invalidate the cache entry if it's corrupted
                        await self._cache.delete(cache_key)

            except Exception as e:
                logger.warning(f"Error getting VAT rates from cache: {e!s}")
                # Don't fail the request if cache fails, just log and continue

        try:
            # Build request parameters
            params = {
                "countryCode": country_code,
                "includeInactive": str(include_inactive).lower(),
                "limit": min(limit, 500),  # Enforce max limit
            }

            # Make the API call
            response = await self.emag_client.get_paginated(
                endpoint="/api/vat",
                response_model=VatResponse,
                cursor=cursor,
                limit=limit,
                params=params,
                force_refresh=force_refresh,
            )

            # Cache the successful response with error handling and TTL
            try:
                # Set a reasonable TTL (e.g., 1 hour) for the cache
                cache_ttl = 3600  # 1 hour in seconds

                # Cache the full response
                await self._cache.set(
                    f"vat_rates:{country_code}",
                    response,
                    ttl=cache_ttl,
                )

                # Also cache the default rate if available
                default_rate = self._find_default_rate(response.results)
                if default_rate is not None:
                    await self._cache.set(
                        f"default_vat_rate:{country_code}",
                        default_rate.value,
                        ttl=cache_ttl,
                    )

                logger.debug(f"Successfully cached VAT rates for {country_code}")

            except Exception as e:
                logger.error(f"Error caching VAT rates: {e!s}", exc_info=True)
                # Don't fail the request if caching fails, just log the error
            return response

        except EmagAPIError as e:
            error_msg = f"Error fetching VAT rates for {country_code}: {e!s}"
            logger.error(error_msg, exc_info=True)

            # Log additional context for debugging
            logger.debug(
                f"Request params: country_code={country_code}, cursor={cursor}, limit={limit}",
            )

            # Try to get any cached data, even if expired
            try:
                cached_response = await self._cache.get(f"vat_rates:{country_code}")
                if cached_response and isinstance(cached_response, VatResponse):
                    logger.warning("Returning potentially stale cached VAT rates")
                    # Add a warning message to indicate cached data is being used
                    cached_response.messages.append(
                        {
                            "code": "CACHED_DATA",
                            "message": "Returning cached data due to API error",
                            "severity": "warning",
                        },
                    )
                    return cached_response
            except Exception as cache_err:
                logger.warning(f"Error getting stale cache: {cache_err!s}")

            # If we get here, we have no cached data to return
            raise EmagAPIError(
                f"Failed to fetch VAT rates for {country_code} and no cached data available. "
                f"Original error: {e!s}",
            ) from e

    async def get_default_rate(
        self,
        country_code: str = "RO",
        force_refresh: bool = False,
        effective_date: Optional[datetime] = None,
    ) -> VatRate:
        """Get the default VAT rate for a specific country and optional date.

        Args:
            country_code: ISO 2-letter country code (default: "RO")
            force_refresh: If True, bypass cache and fetch fresh data
            effective_date: Optional date to get the default rate for.
                          If None, uses current date.

        Returns:
            VatRate: The default VAT rate for the country and date

        Raises:
            TypeError: If country_code is not a string or effective_date is not a datetime
            ValueError: If country_code is invalid or no default rate is found
            EmagAPIError: If there's an error fetching from the API and no cached data is available

        """
        # Input validation
        if not isinstance(country_code, str):
            raise TypeError(
                f"Country code must be a string, got {type(country_code).__name__}",
            )

        country_code = country_code.strip().upper()
        if len(country_code) != 2 or not country_code.isalpha():
            raise ValueError("Country code must be a 2-letter ISO 3166-1 alpha-2 code")

        if effective_date is not None and not isinstance(effective_date, datetime):
            raise TypeError(
                f"effective_date must be a datetime object, got {type(effective_date).__name__}",
            )
        """Get the default VAT rate for a specific country and optional date.

        Args:
            country_code: ISO 2-letter country code (default: "RO")
            force_refresh: If True, bypass cache and fetch fresh data
            effective_date: Optional date to get the default rate for.
                          If None, uses current date.

        Returns:
            VatRate: The default VAT rate for the country and date

        Raises:
            ValueError: If no default rate is found for the country/date
            EmagAPIError: If there's an error fetching from the API
        """
        if not effective_date:
            effective_date = datetime.now(pytz.utc)

        cache_key = f"default_vat_rate:{country_code}"

        # Check cache first if not forcing refresh
        if not force_refresh:
            try:
                cached_rate = await self._cache.get(cache_key)
                if cached_rate is not None:
                    try:
                        # Basic validation of cached rate
                        if (
                            not isinstance(cached_rate, (int, float))
                            or cached_rate < 0
                            or cached_rate > 100
                        ):
                            logger.warning("Invalid cached rate value, forcing refresh")
                            raise ValueError("Invalid rate value in cache")

                        logger.debug(f"Cache hit for default rate: {country_code}")

                        # Return a basic VatRate object with the cached value
                        return VatRate(
                            id=0,  # Dummy ID for cached values
                            name=f"Cached {cached_rate}%",
                            value=float(cached_rate),
                            is_default=True,
                            valid_from=datetime.utcnow(),
                            country_code=country_code,
                            is_active=True,
                        )
                    except Exception as e:
                        logger.warning(
                            f"Invalid cached rate, forcing refresh: {e!s}",
                        )
                        # Invalidate the cache entry if it's corrupted
                        await self._cache.delete(cache_key)

            except Exception as e:
                logger.warning(f"Error getting default rate from cache: {e!s}")
                # Don't fail the request if cache fails, just log and continue

        try:
            # First, try to get from the full list with caching
            response = await self.get_vat_rates(
                country_code=country_code,
                force_refresh=force_refresh,
                include_inactive=True,  # Need to include inactive to find historical rates
            )

            # Find the default rate that's active on the effective date
            default_rates = [
                rate
                for rate in response.results
                if rate.is_default and self._is_rate_active(rate, effective_date)
            ]

            if default_rates:
                # Sort by valid_from date (most recent first)
                default_rates.sort(
                    key=lambda r: r.valid_from
                    or datetime.min.replace(tzinfo=timezone.utc),
                    reverse=True,
                )
                default_rate = default_rates[0]

                # Cache the default rate
                try:
                    await self._cache.set(
                        f"default_vat_rate:{country_code}",
                        default_rate.value,
                        ttl=3600,  # 1 hour TTL
                    )
                except Exception as e:
                    logger.warning(f"Error caching default rate: {e!s}")
                return default_rate

        except Exception as e:
            logger.warning(f"Error getting default rate from list: {e!s}")

        # Fall back to direct API call if not found in the list
        try:
            params = {
                "countryCode": country_code,
                "isDefault": "true",
                "validAt": effective_date.isoformat(),
            }

            response = await self.emag_client.get(
                endpoint="/api/vat",
                response_model=VatResponse,
                params=params,
                force_refresh=force_refresh,
            )

            if response.results:
                default_rate = response.results[0]
                try:
                    await self._cache.set_default_rate(country_code, default_rate.value)
                except Exception as e:
                    logger.warning(f"Error caching default rate: {e!s}")
                return default_rate

        except Exception as e:
            logger.error(f"Error fetching default VAT rate: {e!s}", exc_info=True)
            # If we get here, we couldn't find a default rate through any method
            raise ValueError(
                f"No default VAT rate found for country {country_code} "
                f"on {effective_date.isoformat()}",
            ) from e
            # Return cached data if available, even if expired
            try:
                cached_rate = await self._cache.get_default_rate(country_code)
                if cached_rate:
                    logger.warning("Returning potentially stale cached default rate")
                    return cached_rate
            except Exception as cache_err:
                logger.warning(f"Error getting stale cache: {cache_err!s}")
            raise ValueError(
                f"No default VAT rate found for country: {country_code} "
                f"on {effective_date.strftime('%Y-%m-%d')}",
            )

    async def get_rate_by_id(
        self,
        rate_id: int,
        country_code: Optional[str] = None,
        force_refresh: bool = False,
    ) -> Optional[VatRate]:
        """Get a specific VAT rate by ID, optionally filtered by country.

        Args:
            rate_id: The ID of the VAT rate to retrieve
            country_code: Optional country code to filter by
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            Optional[VatRate]: The VAT rate if found, None otherwise

        Raises:
            EmagAPIError: If there's an error fetching from the API

        """
        # Try to get from cache first
        if not force_refresh:
            try:
                cached_rate = await self._cache.get_vat_rate(rate_id)
                if cached_rate:
                    if (
                        not country_code
                        or cached_rate.countryCode == country_code.upper()
                    ):
                        return cached_rate
            except Exception as e:
                logger.warning(f"Error getting VAT rate from cache: {e!s}")

        try:
            params = {"id": str(rate_id)}
            if country_code:
                params["countryCode"] = country_code.upper()

            response = await self.emag_client.get(
                endpoint=f"/api/vat/{rate_id}",
                response_model=VatResponse,
                params=params,
                force_refresh=force_refresh,
            )

            if response.results:
                rate = response.results[0]
                try:
                    await self._cache.set_vat_rate(rate_id, rate)
                except Exception as e:
                    logger.warning(f"Error caching VAT rate: {e!s}")
                return rate

        except EmagAPIError as e:
            if e.status_code == 404:  # Not found
                return None
            logger.error(f"Error fetching VAT rate {rate_id}: {e!s}")
            raise

        return None

    async def get_rates_by_country(
        self,
        country_code: str,
        active_only: bool = True,
        effective_date: Optional[datetime] = None,
        force_refresh: bool = False,
    ) -> List[VatRate]:
        """Get all VAT rates for a country, optionally filtered by date.

        Args:
            country_code: ISO 2-letter country code
            active_only: If True, only return rates active on the effective date
            effective_date: Optional date to check for active rates.
                          If None, uses current date.
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            List[VatRate]: List of VAT rates matching the criteria

        Raises:
            ValueError: If country_code is invalid
            EmagAPIError: If there's an error fetching from the API

        """
        if not effective_date:
            effective_date = datetime.now(pytz.utc)

        # Check cache first if not forcing refresh
        if not force_refresh:
            try:
                cached_rates = await self._cache.get_vat_rates(country_code)
                if cached_rates:
                    return cached_rates
            except Exception as e:
                logger.warning(f"Error getting VAT rates from cache: {e!s}")

        # Get all rates for the country
        response = await self.get_vat_rates(
            country_code=country_code,
            force_refresh=force_refresh,
            include_inactive=not active_only,
        )

        # Filter by date if needed
        if active_only:
            rates = [
                rate
                for rate in response.results
                if self._is_rate_active(rate, effective_date)
            ]
        else:
            rates = response.results

        # Cache the results
        try:
            await self._cache.set_vat_rates(country_code, rates)
        except Exception as e:
            logger.warning(f"Error caching VAT rates: {e!s}")
        return rates

    async def invalidate_vat_cache(self, country_code: str):
        """Invalidate the VAT cache for a specific country.

        Args:
            country_code: ISO 2-letter country code

        """
        await self._cache.invalidate_vat_cache(country_code)

    async def refresh_vat_rates(
        self,
        country_code: Optional[Union[str, List[str]]] = None,
        rate_ids: Optional[List[int]] = None,
    ) -> None:
        """Force refresh the cached VAT rates for specific countries or rates.

        Args:
            country_code: Optional country code or list of country codes to refresh.
                        If None, refreshes all cached VAT rates.
            rate_ids: Optional list of rate IDs to refresh. Takes precedence over country_code.

        """
        if rate_ids:
            # Invalidate specific rate IDs
            for rate_id in rate_ids:
                try:
                    await self._cache.invalidate_vat_rate(rate_id)
                except Exception as e:
                    logger.error(f"Error invalidating cache: {e!s}")
        elif country_code:
            # Invalidate cache for this country
            try:
                await self._cache.invalidate_vat_rates(country_code)
            except Exception as e:
                logger.error(f"Error invalidating cache: {e!s}")

        # Pre-warm the cache with fresh data if a single country is specified
        if isinstance(country_code, str):
            try:
                await self.get_vat_rates(country_code=country_code, force_refresh=True)
                await self.get_default_rate(
                    country_code=country_code,
                    force_refresh=True,
                )
            except Exception as e:
                logger.warning(f"Error pre-warming cache for {country_code}: {e!s}")
        else:
            # In a real implementation, we would fetch all supported countries
            # For now, just refresh the default country
            await self.refresh_vat_rates("RO")

    def _find_default_rate(
        self,
        rates: Optional[List[VatRate]],
        effective_date: Optional[datetime] = None,
    ) -> Optional[VatRate]:
        """Find the default VAT rate active for the given effective date.

        Args:
            rates: Collection of VAT rates to inspect.
            effective_date: Point in time to evaluate activity against. Defaults to now.

        Returns:
            Optional[VatRate]: The most recent active default rate if available.
        """

        if not rates:
            return None

        effective_date = self._ensure_timezone(
            effective_date or datetime.now(timezone.utc)
        )

        active_defaults = [
            rate
            for rate in rates
            if rate.is_default and self._is_rate_active(rate, effective_date)
        ]

        if not active_defaults:
            return None

        return max(
            active_defaults,
            key=lambda rate: self._ensure_timezone(rate.valid_from)
            or datetime.min.replace(tzinfo=timezone.utc),
        )

    def _is_rate_active(self, rate: VatRate, effective_date: datetime) -> bool:
        """Check whether a VAT rate is active for the provided effective date."""

        if not rate:
            return False

        effective_date = self._ensure_timezone(
            effective_date or datetime.now(timezone.utc)
        )
        valid_from = self._ensure_timezone(rate.valid_from) or datetime.min.replace(
            tzinfo=timezone.utc,
        )
        valid_until = self._ensure_timezone(rate.valid_until) or datetime.max.replace(
            tzinfo=timezone.utc,
        )

        return rate.is_active and valid_from <= effective_date <= valid_until

    @staticmethod
    def _ensure_timezone(value: Optional[datetime]) -> Optional[datetime]:
        """Ensure the provided datetime is timezone-aware in UTC."""

        if value is None:
            return None

        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)

    @classmethod
    async def get_instance(cls) -> "VatService":
        """Get a shared instance of the VAT service."""
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance
