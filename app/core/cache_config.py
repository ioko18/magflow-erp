"""
Cache configuration for MagFlow ERP.

Provides caching utilities for API endpoints and database queries.
"""

import hashlib
from collections.abc import Callable
from datetime import timedelta
from functools import wraps
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Cache configuration
CACHE_CONFIG = {
    "emag_products": {
        "ttl": timedelta(minutes=15),  # 15 minutes
        "max_size": 1000,
    },
    "emag_orders": {
        "ttl": timedelta(minutes=5),  # 5 minutes
        "max_size": 500,
    },
    "emag_sync_status": {
        "ttl": timedelta(minutes=1),  # 1 minute
        "max_size": 10,
    },
    "product_count": {
        "ttl": timedelta(minutes=30),  # 30 minutes
        "max_size": 10,
    },
}


class SimpleCache:
    """Simple in-memory cache implementation."""

    def __init__(self, max_size: int = 1000):
        """
        Initialize cache.

        Args:
            max_size: Maximum number of items to cache
        """
        self._cache: dict = {}
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if key in self._cache:
            self._hits += 1
            logger.debug(f"Cache HIT: {key}")
            return self._cache[key]

        self._misses += 1
        logger.debug(f"Cache MISS: {key}")
        return None

    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        # Simple LRU: remove oldest if at capacity
        if len(self._cache) >= self._max_size:
            # Remove first item (oldest)
            first_key = next(iter(self._cache))
            del self._cache[first_key]
            logger.debug(f"Cache eviction: {first_key}")

        self._cache[key] = value
        logger.debug(f"Cache SET: {key}")

    def delete(self, key: str) -> None:
        """
        Delete value from cache.

        Args:
            key: Cache key
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache DELETE: {key}")

    def clear(self) -> None:
        """Clear all cache."""
        self._cache.clear()
        logger.info("Cache cleared")

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0

        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.2f}%",
        }


# Global cache instances
_caches: dict[str, SimpleCache] = {}


def get_cache(cache_name: str) -> SimpleCache:
    """
    Get or create cache instance.

    Args:
        cache_name: Name of the cache

    Returns:
        Cache instance
    """
    if cache_name not in _caches:
        config = CACHE_CONFIG.get(cache_name, {"max_size": 100})
        _caches[cache_name] = SimpleCache(max_size=config.get("max_size", 100))
        logger.info(f"Created cache: {cache_name}")

    return _caches[cache_name]


def generate_cache_key(*args, **kwargs) -> str:
    """
    Generate cache key from arguments.

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Cache key string
    """
    # Create a string representation of all arguments
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
    key_string = ":".join(key_parts)

    # Hash for shorter keys (not for security, just cache key generation)
    return hashlib.md5(key_string.encode(), usedforsecurity=False).hexdigest()


def cached(cache_name: str, ttl_seconds: int | None = None):
    """
    Decorator to cache function results.

    Args:
        cache_name: Name of the cache to use
        ttl_seconds: Time to live in seconds (optional)

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}:{generate_cache_key(*args, **kwargs)}"

            # Try to get from cache
            cache = get_cache(cache_name)
            cached_value = cache.get(cache_key)

            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = await func(*args, **kwargs)
            cache.set(cache_key, result)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}:{generate_cache_key(*args, **kwargs)}"

            # Try to get from cache
            cache = get_cache(cache_name)
            cached_value = cache.get(cache_key)

            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result)

            return result

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def invalidate_cache(cache_name: str, pattern: str | None = None) -> None:
    """
    Invalidate cache entries.

    Args:
        cache_name: Name of the cache
        pattern: Optional pattern to match keys (not implemented yet)
    """
    cache = get_cache(cache_name)
    cache.clear()
    logger.info(f"Invalidated cache: {cache_name}")


def get_all_cache_stats() -> dict:
    """
    Get statistics for all caches.

    Returns:
        Dictionary with stats for each cache
    """
    stats = {}
    for name, cache in _caches.items():
        stats[name] = cache.get_stats()

    return stats
