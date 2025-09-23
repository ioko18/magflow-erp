"""Caching for eMAG API responses with TTL and invalidation support."""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.core.logging import get_logger
from app.integrations.emag.models.responses.vat import VatResponse
from app.services.redis_cache import cache

logger = get_logger(__name__)

# Cache TTLs in seconds
CACHE_TTL = {
    "vat_rates": int(timedelta(hours=24).total_seconds()),  # VAT rates change rarely
    "default_rate": int(timedelta(hours=1).total_seconds()),
}

# Cache key templates
VAT_RATES_KEY = "emag:vat:rates:{country_code}"
DEFAULT_RATE_KEY = "emag:vat:default:{country_code}"


async def get_vat_cache(key: str) -> Optional[Any]:
    """Get a value from the cache.

    Args:
        key: Cache key to retrieve

    Returns:
        Cached value or None if not found

    """
    try:
        return await cache.get(key)
    except Exception as e:
        logger.warning(f"Error getting from cache: {e!s}")
        return None


async def set_vat_cache(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Set a value in the cache.

    Args:
        key: Cache key
        value: Value to cache (must be JSON serializable)
        ttl: Time to live in seconds (default: None for no expiration)

    Returns:
        bool: True if successful, False otherwise

    """
    try:
        # Add timestamp to the cached value
        cached_data = {
            "data": value,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "ttl": ttl,
        }
        return await cache.set(key, cached_data, ttl=ttl)
    except Exception as e:
        logger.warning(f"Error setting cache: {e!s}")
        return False


async def invalidate_vat_cache(country_code: Optional[str] = None) -> None:
    """Invalidate VAT rate cache for a specific country or all countries.

    Args:
        country_code: Country code to invalidate cache for, or None for all countries.

    """
    try:
        if country_code:
            # Invalidate specific country
            cache_key = f"emag:vat:rates:{country_code}"
        else:
            # Invalidate all VAT rate caches
            cache_key = "emag:vat:rates:*"

        # The actual invalidation happens in a background task
        await _invalidate_cache_keys(cache_key)
    except Exception as e:
        logger.warning(f"Error invalidating cache: {e!s}")


async def _invalidate_cache_keys(pattern: str) -> int:
    """Helper function to invalidate cache keys matching a pattern."""
    from app.services.redis_cache import cache

    keys = await cache.redis.keys(pattern)
    if keys:
        return await cache.redis.delete(*keys)
    return 0


class VatCache:
    """VAT rate caching service with TTL and invalidation support."""

    @staticmethod
    async def get_vat_rates(
        country_code: str = "RO",
        force_refresh: bool = False,
    ) -> Optional[VatResponse]:
        """Get VAT rates for a specific country.

        Args:
            country_code: ISO 2-letter country code
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            VatResponse: Cached or fresh VAT rates data, or None if not found

        """
        cache_key = VAT_RATES_KEY.format(country_code=country_code)

        if not force_refresh:
            cached = await get_vat_cache(cache_key)
            if cached and "data" in cached:
                try:
                    return VatResponse(**cached["data"])
                except Exception as e:
                    logger.warning(f"Error deserializing cached VAT rates: {e!s}")
        return None

    @staticmethod
    async def set_vat_rates(
        country_code: str,
        rates: VatResponse,
        ttl: Optional[int] = None,
    ) -> bool:
        """Cache VAT rates for a specific country.

        Args:
            country_code: ISO 2-letter country code
            rates: VAT rates to cache
            ttl: Time to live in seconds (default: from CACHE_TTL)

        Returns:
            bool: True if successful, False otherwise

        """
        cache_key = VAT_RATES_KEY.format(country_code=country_code)
        ttl = ttl or CACHE_TTL["vat_rates"]
        return await set_vat_cache(cache_key, rates.model_dump(), ttl=ttl)

    @staticmethod
    async def get_default_rate(
        country_code: str = "RO",
        force_refresh: bool = False,
    ) -> Optional[float]:
        """Get the default VAT rate for a specific country.

        Args:
            country_code: ISO 2-letter country code
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            float: Default VAT rate as a decimal (e.g., 0.19 for 19%), or None if not found

        """
        cache_key = DEFAULT_RATE_KEY.format(country_code=country_code)

        if not force_refresh:
            cached = await get_vat_cache(cache_key)
            if cached and "data" in cached:
                try:
                    return float(cached["data"])
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error deserializing cached default rate: {e!s}")
        return None

    @staticmethod
    async def set_default_rate(
        country_code: str,
        rate: float,
        ttl: Optional[int] = None,
    ) -> bool:
        """Cache the default VAT rate for a specific country.

        Args:
            country_code: ISO 2-letter country code
            rate: Default VAT rate as a decimal (e.g., 0.19 for 19%)
            ttl: Time to live in seconds (default: from CACHE_TTL)

        Returns:
            bool: True if successful, False otherwise

        """
        cache_key = DEFAULT_RATE_KEY.format(country_code=country_code)
        ttl = ttl or CACHE_TTL["default_rate"]
        return await set_vat_cache(cache_key, str(rate), ttl=ttl)
