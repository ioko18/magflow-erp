"""
Redis caching utilities for MagFlow ERP.

Provides caching decorators and utilities for:
- API response caching
- Database query caching
- Session caching
- Rate limiting support
"""

from __future__ import annotations

import json
import pickle
from functools import wraps
from typing import Any, Callable, Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Global Redis client
_redis_client: Optional[Redis] = None


async def get_redis() -> Redis:
    """
    Get or create Redis client.
    
    Returns:
        Redis client instance
    """
    global _redis_client

    if _redis_client is None:
        redis_url = getattr(settings, 'REDIS_URL', 'redis://redis:6379/0')
        _redis_client = await redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=False,  # We'll handle encoding ourselves
            socket_connect_timeout=5,
            socket_keepalive=True,
        )
        logger.info(f"Redis client initialized: {redis_url}")

    return _redis_client


async def close_redis():
    """Close Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis client closed")


def cache_key(*args, **kwargs) -> str:
    """
    Generate cache key from function arguments.
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Cache key string
    """
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return ":".join(key_parts)


def cache_result(
    ttl: int = 300,
    prefix: str = "cache",
    key_func: Optional[Callable] = None
):
    """
    Decorator to cache function results in Redis.
    
    Args:
        ttl: Time to live in seconds (default 5 minutes)
        prefix: Cache key prefix
        key_func: Optional function to generate cache key
        
    Usage:
        @cache_result(ttl=300, prefix="products")
        async def get_products(category: str):
            return await fetch_products(category)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key_str = key_func(*args, **kwargs)
            else:
                cache_key_str = cache_key(*args, **kwargs)

            full_key = f"{prefix}:{func.__name__}:{cache_key_str}"

            try:
                redis_client = await get_redis()

                # Try to get from cache
                cached = await redis_client.get(full_key)
                if cached:
                    logger.debug(f"Cache HIT: {full_key}")
                    return json.loads(cached)

                # Cache miss - execute function
                logger.debug(f"Cache MISS: {full_key}")
                result = await func(*args, **kwargs)

                # Store in cache
                await redis_client.setex(
                    full_key,
                    ttl,
                    json.dumps(result, default=str)
                )

                return result

            except Exception as e:
                logger.error(f"Cache error: {e}", exc_info=True)
                # If cache fails, execute function normally
                return await func(*args, **kwargs)

        return wrapper
    return decorator


def cache_result_binary(
    ttl: int = 300,
    prefix: str = "cache",
):
    """
    Decorator to cache function results using pickle (for complex objects).
    
    Args:
        ttl: Time to live in seconds
        prefix: Cache key prefix
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key_str = cache_key(*args, **kwargs)
            full_key = f"{prefix}:{func.__name__}:{cache_key_str}"

            try:
                redis_client = await get_redis()

                # Try to get from cache
                cached = await redis_client.get(full_key)
                if cached:
                    logger.debug(f"Cache HIT (binary): {full_key}")
                    return pickle.loads(cached)

                # Cache miss
                logger.debug(f"Cache MISS (binary): {full_key}")
                result = await func(*args, **kwargs)

                # Store in cache
                await redis_client.setex(
                    full_key,
                    ttl,
                    pickle.dumps(result)
                )

                return result

            except Exception as e:
                logger.error(f"Cache error (binary): {e}", exc_info=True)
                return await func(*args, **kwargs)

        return wrapper
    return decorator


async def invalidate_cache(pattern: str):
    """
    Invalidate cache entries matching a pattern.
    
    Args:
        pattern: Redis key pattern (e.g., "products:*")
    """
    try:
        redis_client = await get_redis()

        # Find matching keys
        keys = []
        async for key in redis_client.scan_iter(match=pattern):
            keys.append(key)

        # Delete keys
        if keys:
            await redis_client.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache entries matching: {pattern}")

    except Exception as e:
        logger.error(f"Cache invalidation error: {e}", exc_info=True)


async def set_cache(key: str, value: Any, ttl: int = 300):
    """
    Set a value in cache.
    
    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds
    """
    try:
        redis_client = await get_redis()
        await redis_client.setex(
            key,
            ttl,
            json.dumps(value, default=str)
        )
    except Exception as e:
        logger.error(f"Failed to set cache: {e}", exc_info=True)


async def get_cache(key: str) -> Optional[Any]:
    """
    Get a value from cache.
    
    Args:
        key: Cache key
        
    Returns:
        Cached value or None
    """
    try:
        redis_client = await get_redis()
        cached = await redis_client.get(key)
        if cached:
            return json.loads(cached)
        return None
    except Exception as e:
        logger.error(f"Failed to get cache: {e}", exc_info=True)
        return None


async def delete_cache(key: str):
    """
    Delete a value from cache.
    
    Args:
        key: Cache key
    """
    try:
        redis_client = await get_redis()
        await redis_client.delete(key)
    except Exception as e:
        logger.error(f"Failed to delete cache: {e}", exc_info=True)


async def get_cache_stats() -> dict:
    """
    Get Redis cache statistics.
    
    Returns:
        Dictionary with cache statistics
    """
    try:
        redis_client = await get_redis()
        info = await redis_client.info()

        return {
            "connected": True,
            "used_memory": info.get("used_memory_human", "N/A"),
            "total_keys": await redis_client.dbsize(),
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0),
            "hit_rate": (
                info.get("keyspace_hits", 0) /
                (info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1))
                * 100
            ),
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}", exc_info=True)
        return {"connected": False, "error": str(e)}


# Specific cache utilities for eMAG integration

async def cache_courier_accounts(account_type: str, data: list, ttl: int = 3600):
    """Cache courier accounts (1 hour TTL)."""
    await set_cache(f"emag:couriers:{account_type}", data, ttl)


async def get_cached_courier_accounts(account_type: str) -> Optional[list]:
    """Get cached courier accounts."""
    return await get_cache(f"emag:couriers:{account_type}")


async def cache_product_categories(account_type: str, data: list, ttl: int = 86400):
    """Cache product categories (24 hour TTL)."""
    await set_cache(f"emag:categories:{account_type}", data, ttl)


async def get_cached_categories(account_type: str) -> Optional[list]:
    """Get cached product categories."""
    return await get_cache(f"emag:categories:{account_type}")


async def cache_order_statistics(account_type: str, data: dict, ttl: int = 300):
    """Cache order statistics (5 minute TTL)."""
    await set_cache(f"emag:stats:orders:{account_type}", data, ttl)


async def get_cached_order_statistics(account_type: str) -> Optional[dict]:
    """Get cached order statistics."""
    return await get_cache(f"emag:stats:orders:{account_type}")


async def invalidate_emag_cache(account_type: Optional[str] = None):
    """
    Invalidate all eMAG-related cache.
    
    Args:
        account_type: Optional account type to invalidate specific cache
    """
    if account_type:
        await invalidate_cache(f"emag:*:{account_type}")
    else:
        await invalidate_cache("emag:*")
