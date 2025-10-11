"""
Inventory Caching Service

Provides Redis caching for inventory statistics and frequently accessed data
to reduce database load and improve response times.
"""

from typing import Any

from app.core.logging import get_logger
from app.services.infrastructure.redis_cache import RedisCache

logger = get_logger(__name__)


class InventoryCacheService:
    """Service for caching inventory-related data."""

    # Cache TTL configurations (in seconds)
    STATISTICS_TTL = 300  # 5 minutes
    LOW_STOCK_LIST_TTL = 180  # 3 minutes
    SEARCH_RESULTS_TTL = 600  # 10 minutes
    PRODUCT_DETAILS_TTL = 900  # 15 minutes

    def __init__(self):
        """Initialize the cache service."""
        self.cache = RedisCache()
        self.cache_prefix = "inventory:"

    def _make_key(self, key_type: str, *args: str) -> str:
        """
        Generate a cache key.

        Args:
            key_type: Type of cache key (stats, low_stock, search, etc.)
            *args: Additional key components

        Returns:
            Formatted cache key
        """
        parts = [self.cache_prefix, key_type] + list(args)
        return ":".join(str(p) for p in parts if p)

    # ========================================================================
    # Statistics Caching
    # ========================================================================

    async def get_statistics(
        self, account_type: str | None = None
    ) -> dict[str, Any] | None:
        """
        Get cached inventory statistics.

        Args:
            account_type: Optional account type filter

        Returns:
            Cached statistics or None if not found
        """
        key = self._make_key("stats", account_type or "all")
        data = await self.cache.get(key)

        if data:
            logger.debug(f"Cache hit for statistics: {key}")
            return data

        logger.debug(f"Cache miss for statistics: {key}")
        return None

    async def set_statistics(
        self,
        statistics: dict[str, Any],
        account_type: str | None = None,
        ttl: int | None = None,
    ) -> bool:
        """
        Cache inventory statistics.

        Args:
            statistics: Statistics data to cache
            account_type: Optional account type filter
            ttl: Time to live in seconds (default: STATISTICS_TTL)

        Returns:
            True if cached successfully
        """
        key = self._make_key("stats", account_type or "all")
        ttl = ttl or self.STATISTICS_TTL

        success = await self.cache.set(key, statistics, ttl=ttl)
        if success:
            logger.debug(f"Cached statistics: {key} (TTL: {ttl}s)")

        return success

    async def invalidate_statistics(self, account_type: str | None = None) -> bool:
        """
        Invalidate cached statistics.

        Args:
            account_type: Optional account type filter

        Returns:
            True if invalidated successfully
        """
        if account_type:
            key = self._make_key("stats", account_type)
            return await self.cache.delete(key)
        else:
            # Invalidate all statistics
            pattern = self._make_key("stats", "*")
            return await self.cache.delete_pattern(pattern)

    # ========================================================================
    # Low Stock List Caching
    # ========================================================================

    async def get_low_stock_list(
        self,
        account_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any] | None:
        """
        Get cached low stock product list.

        Args:
            account_type: Optional account type filter
            status: Optional status filter
            page: Page number
            page_size: Items per page

        Returns:
            Cached product list or None if not found
        """
        key = self._make_key(
            "low_stock",
            account_type or "all",
            status or "all",
            str(page),
            str(page_size),
        )

        data = await self.cache.get(key)
        if data:
            logger.debug(f"Cache hit for low stock list: {key}")
            return data

        return None

    async def set_low_stock_list(
        self,
        products_data: dict[str, Any],
        account_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
        ttl: int | None = None,
    ) -> bool:
        """
        Cache low stock product list.

        Args:
            products_data: Product list data to cache
            account_type: Optional account type filter
            status: Optional status filter
            page: Page number
            page_size: Items per page
            ttl: Time to live in seconds (default: LOW_STOCK_LIST_TTL)

        Returns:
            True if cached successfully
        """
        key = self._make_key(
            "low_stock",
            account_type or "all",
            status or "all",
            str(page),
            str(page_size),
        )
        ttl = ttl or self.LOW_STOCK_LIST_TTL

        return await self.cache.set(key, products_data, ttl=ttl)

    # ========================================================================
    # Search Results Caching
    # ========================================================================

    async def get_search_results(
        self, query: str, limit: int = 20
    ) -> dict[str, Any] | None:
        """
        Get cached search results.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            Cached search results or None if not found
        """
        # Normalize query for consistent caching
        normalized_query = query.lower().strip()
        key = self._make_key("search", normalized_query, str(limit))

        return await self.cache.get(key)

    async def set_search_results(
        self,
        query: str,
        results: dict[str, Any],
        limit: int = 20,
        ttl: int | None = None,
    ) -> bool:
        """
        Cache search results.

        Args:
            query: Search query
            results: Search results to cache
            limit: Maximum results
            ttl: Time to live in seconds (default: SEARCH_RESULTS_TTL)

        Returns:
            True if cached successfully
        """
        normalized_query = query.lower().strip()
        key = self._make_key("search", normalized_query, str(limit))
        ttl = ttl or self.SEARCH_RESULTS_TTL

        return await self.cache.set(key, results, ttl=ttl)

    # ========================================================================
    # Cache Invalidation
    # ========================================================================

    async def invalidate_all(self) -> bool:
        """
        Invalidate all inventory caches.

        Returns:
            True if invalidated successfully
        """
        pattern = self._make_key("*")
        deleted = await self.cache.delete_pattern(pattern)

        if deleted:
            logger.info(f"Invalidated all inventory caches (pattern: {pattern})")

        return deleted

    async def invalidate_on_update(self, account_type: str | None = None) -> None:
        """
        Invalidate relevant caches when inventory is updated.

        Args:
            account_type: Account type that was updated
        """
        # Invalidate statistics
        await self.invalidate_statistics(account_type)

        # Invalidate low stock lists
        pattern = self._make_key("low_stock", "*")
        await self.cache.delete_pattern(pattern)

        logger.info(f"Invalidated caches for account: {account_type or 'all'}")

    # ========================================================================
    # Cache Warming
    # ========================================================================

    async def warm_cache(self, statistics: dict[str, Any]) -> None:
        """
        Warm up cache with frequently accessed data.

        Args:
            statistics: Statistics to cache
        """
        # Cache overall statistics
        await self.set_statistics(statistics)

        # Cache per-account statistics if available
        if "by_account" in statistics:
            for account in ["MAIN", "FBE"]:
                account_stats = statistics.copy()
                account_stats["filtered_by"] = account
                await self.set_statistics(account_stats, account_type=account)

        logger.info("Cache warmed with inventory statistics")


# Singleton instance
_cache_service: InventoryCacheService | None = None


def get_inventory_cache() -> InventoryCacheService:
    """
    Get the inventory cache service instance.

    Returns:
        InventoryCacheService singleton instance
    """
    global _cache_service
    if _cache_service is None:
        _cache_service = InventoryCacheService()
    return _cache_service
