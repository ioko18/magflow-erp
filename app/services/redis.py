import asyncio
import json
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, List, TypeVar, cast

import redis.asyncio as redis

from ..core.config import settings

logger = logging.getLogger(__name__)

# Type variable for generic function return type
T = TypeVar("T")


class CacheManager:
    _instance = None
    _client = None
    _version = 0  # Global cache version for cache busting
    _local_cache: Dict[str, Any] = {}  # In-memory cache for frequently accessed data
    _local_cache_timestamps: Dict[str, float] = {}  # Timestamps for local cache entries
    _local_cache_lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CacheManager, cls).__new__(cls)
            cls._client = None
        return cls._instance

    @classmethod
    async def get_client(cls) -> redis.Redis:
        if cls._client is None or not await cls._client.ping():
            cls._client = redis.from_url(
                settings.redis_url,
                password=settings.redis_password,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_keepalive=True,
                retry_on_timeout=True,
                # Connection pool settings for performance
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
                for key in cls._local_cache.keys()
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
            if value is not None:
                result = json.loads(value)
                # Store in local cache for faster access
                async with cls._local_cache_lock:
                    cls._local_cache[key] = result
                    cls._local_cache_timestamps[key] = time.time()
                logger.debug(f"Redis cache hit: {key}")
                return result
            return None
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Cache get failed for key {key}: {e!s}")
            return None

    @classmethod
    async def set_json(
        cls,
        key: str,
        value: Any,
        ttl: int = 60,
        nx: bool = False,
        local_only: bool = False,
    ) -> bool:
        """Set a JSON value in multi-level cache (local + Redis)."""
        try:
            serialized = json.dumps(value)

            # Store in local cache
            async with cls._local_cache_lock:
                cls._local_cache[key] = value
                cls._local_cache_timestamps[key] = time.time()

            # Store in Redis if not local-only
            if not local_only:
                client = await cls.get_client()
                if nx:
                    result = await client.set(key, serialized, ex=ttl, nx=True)
                else:
                    result = await client.set(key, serialized, ex=ttl)
                return result is not None

            return True
        except (redis.RedisError, TypeError) as e:
            logger.warning(f"Cache set failed for key {key}: {e!s}")
            return False

    @classmethod
    async def delete(cls, key: str) -> bool:
        """Delete a key from both local and Redis cache."""
        async with cls._local_cache_lock:
            cls._local_cache.pop(key, None)
            cls._local_cache_timestamps.pop(key, None)

        try:
            client = await cls.get_client()
            return await client.delete(key) > 0
        except redis.RedisError as e:
            logger.warning(f"Cache delete failed for key {key}: {e!s}")
            return False

    @classmethod
    def cached(cls, prefix: str, ttl: int = 60, skip_cache: bool = False):
        """Decorator to cache the result of an async function with multi-level caching."""

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> T:
                # Skip caching if explicitly disabled
                if kwargs.pop("skip_cache", False) or skip_cache:
                    return await func(*args, **kwargs)

                # Generate cache key from function name and arguments
                key = cls.generate_key(
                    prefix,
                    *[str(arg) for arg in args[1:]],  # Skip 'self' or 'request'
                    *[f"{k}:{v}" for k, v in sorted(kwargs.items())],
                )

                # Try to get from cache
                cached = await cls.get_json(key)
                if cached is not None:
                    logger.debug(f"Cache hit: {key}")
                    return cached

                # Cache miss, call the original function
                logger.debug(f"Cache miss: {key}")
                result = await func(*args, **kwargs)

                # Store result in cache
                if result is not None:
                    await cls.set_json(key, result, ttl=ttl)

                return result

            return cast("Callable[..., T]", wrapper)

        return decorator

    @classmethod
    async def get_or_set(
        cls,
        key: str,
        factory_func: Callable,
        ttl: int = 60,
        *args,
        **kwargs,
    ) -> Any:
        """Get from cache or execute factory function and cache result."""
        # Try to get from cache
        cached = await cls.get_json(key)
        if cached is not None:
            logger.debug(f"Cache hit: {key}")
            return cached

        # Cache miss, execute factory function
        logger.debug(f"Cache miss: {key}")
        result = await factory_func(*args, **kwargs)

        # Store result in cache
        if result is not None:
            await cls.set_json(key, result, ttl=ttl)

        return result

    @classmethod
    async def batch_get(cls, keys: List[str]) -> Dict[str, Any]:
        """Get multiple keys from cache in batch."""
        results = {}

        # Check local cache first
        async with cls._local_cache_lock:
            local_results = {
                key: cls._local_cache.get(key)
                for key in keys
                if key in cls._local_cache
            }
            results.update(local_results)

        # Get remaining keys from Redis
        remaining_keys = [key for key in keys if key not in local_results]
        if remaining_keys:
            try:
                client = await cls.get_client()
                redis_results = await client.mget(remaining_keys)

                for key, value in zip(remaining_keys, redis_results):
                    if value is not None:
                        result = json.loads(value)
                        results[key] = result
                        # Store in local cache
                        async with cls._local_cache_lock:
                            cls._local_cache[key] = result
                            cls._local_cache_timestamps[key] = time.time()
            except (redis.RedisError, json.JSONDecodeError) as e:
                logger.warning(f"Batch cache get failed: {e!s}")

        return results

    @classmethod
    async def batch_set(cls, key_value_pairs: Dict[str, Any], ttl: int = 60) -> bool:
        """Set multiple key-value pairs in batch."""
        try:
            # Prepare Redis pipeline
            client = await cls.get_client()
            pipeline = client.pipeline()

            # Store in local cache
            async with cls._local_cache_lock:
                for key, value in key_value_pairs.items():
                    cls._local_cache[key] = value
                    cls._local_cache_timestamps[key] = time.time()
                    pipeline.set(key, json.dumps(value), ex=ttl)

            # Execute pipeline
            await pipeline.execute()
            return True
        except (redis.RedisError, TypeError) as e:
            logger.warning(f"Batch cache set failed: {e!s}")
            return False
