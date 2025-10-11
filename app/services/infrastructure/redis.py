import asyncio
import inspect
import json
import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import redis.asyncio as redis

from ...core.config import settings

logger = logging.getLogger(__name__)

# Type variable for generic function return type
T = TypeVar("T")


class CacheManager:
    _instance = None
    _client = None
    _version = 0  # Global cache version for cache busting
    _local_cache: dict[str, Any] = {}  # In-memory cache for frequently accessed data
    _local_cache_timestamps: dict[str, float] = {}  # Timestamps for local cache entries
    _local_cache_lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._client = None
        return cls._instance

    @classmethod
    async def get_client(cls) -> redis.Redis:
        if cls._client is None or not await cls._client.ping():
            cls._client = redis.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_keepalive=True,
                retry_on_timeout=True,
                max_connections=50,
                retry_on_error=[redis.ConnectionError, redis.TimeoutError],
            )
        return cls._client

    @classmethod
    async def close(cls):
        if cls._client:
            await cls._client.close()
            cls._client = None

    @classmethod
    def generate_key(cls, prefix: str, *parts: str) -> str:
        """Generate a cache key from parts."""
        key_parts = [str(part).strip().lower() for part in parts if part is not None]
        return f"cache:{prefix}:{cls._version}:{':'.join(key_parts)}"

    @classmethod
    async def invalidate_prefix(cls, prefix: str) -> None:
        """Invalidate all keys with the given prefix by bumping the version."""
        cls._version += 1
        # Clear local cache entries that match the prefix
        async with cls._local_cache_lock:
            keys_to_remove = [
                key
                for key in cls._local_cache
                if key.startswith(f"cache:{prefix}:")
            ]
            for key in keys_to_remove:
                cls._local_cache.pop(key, None)
                cls._local_cache_timestamps.pop(key, None)
        logger.info(f"Cache version bumped to {cls._version} for prefix: {prefix}")

    @classmethod
    async def invalidate_pattern(cls, pattern: str) -> None:
        """Invalidate keys matching a pattern."""
        try:
            client = await cls.get_client()
            keys = await client.keys(pattern)
            if keys:
                await client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} keys matching pattern: {pattern}")
        except redis.RedisError as e:
            logger.warning(f"Cache invalidation failed: {e!s}")

    @classmethod
    async def get_json(cls, key: str) -> Any:
        """Get a JSON value from multi-level cache (local → Redis)."""
        # Check local cache first
        async with cls._local_cache_lock:
            if key in cls._local_cache:
                timestamp = cls._local_cache_timestamps.get(key, 0)
                # Local cache expires after 30 seconds
                if time.time() - timestamp < 30:
                    logger.debug(f"Local cache hit: {key}")
                    return cls._local_cache[key]

        try:
            client = await cls.get_client()
            value = await client.get(key)
            if value is None:
                return None

            # Deserialize JSON
            result = json.loads(value)

            # Cache in local storage
            async with cls._local_cache_lock:
                cls._local_cache[key] = result
                cls._local_cache_timestamps[key] = time.time()

            return result
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Cache get failed for key {key}: {e!s}")
            return None

    @classmethod
    async def set_json(cls, key: str, value: Any, expire: int = 3600) -> bool:
        """Set a JSON value in cache with expiration."""
        try:
            client = await cls.get_client()
            serialized = json.dumps(value)
            result = await client.set(key, serialized, ex=expire)

            # Update local cache
            async with cls._local_cache_lock:
                cls._local_cache[key] = value
                cls._local_cache_timestamps[key] = time.time()

            return bool(result)
        except (redis.RedisError, TypeError) as e:
            logger.warning(f"Cache set failed for key {key}: {e!s}")
            return False

    @classmethod
    async def delete(cls, key: str) -> bool:
        """Delete a key from cache."""
        try:
            client = await cls.get_client()
            result = await client.delete(key)

            # Remove from local cache
            async with cls._local_cache_lock:
                cls._local_cache.pop(key, None)
                cls._local_cache_timestamps.pop(key, None)

            return bool(result)
        except redis.RedisError as e:
            logger.warning(f"Cache delete failed for key {key}: {e!s}")
            return False

    @classmethod
    async def clear_all(cls) -> bool:
        """Clear all cached data (use with caution)."""
        try:
            client = await cls.get_client()
            await client.flushdb()

            # Clear local cache
            async with cls._local_cache_lock:
                cls._local_cache.clear()
                cls._local_cache_timestamps.clear()

            return True
        except redis.RedisError as e:
            logger.warning(f"Cache clear failed: {e!s}")
            return False

    @classmethod
    def cache_it(
        cls,
        prefix: str,
        expire: int = 3600,
        key_args: list[str] | None = None,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """Decorator to cache function results.

        Args:
            prefix: Cache key prefix
            expire: Cache expiration in seconds
            key_args: List of argument names to include in cache key
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                # Generate cache key
                key_parts = [prefix]

                # Add key_args to cache key if specified
                if key_args:
                    # Get function signature
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()

                    for arg_name in key_args:
                        if arg_name in bound_args.arguments:
                            key_parts.append(str(bound_args.arguments[arg_name]))

                cache_key = cls.generate_key(*key_parts)

                # Try to get from cache
                cached = await cls.get_json(cache_key)
                if cached is not None:
                    return cached

                # Call the function
                result = await func(*args, **kwargs)

                # Cache the result
                if result is not None:
                    await cls.set_json(cache_key, result, expire=expire)

                return result

            return wrapper

        return decorator


# Create a singleton instance
cache = CacheManager()
