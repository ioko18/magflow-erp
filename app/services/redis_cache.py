"""Redis-based caching with namespacing and automatic invalidation."""

import hashlib
import json
import logging
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

import redis.asyncio as redis
from fastapi import Request

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RedisCache:
    """Redis-based cache with namespacing and automatic invalidation."""

    def __init__(self, redis_url: str = None, namespace: str = "magflow"):
        redis_url = redis_url or settings.REDIS_URL
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self.namespace = namespace
        self.hits = 0
        self.misses = 0

    def _get_key(self, key: str) -> str:
        """Get namespaced key."""
        return f"{self.namespace}:{key}"

    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache."""
        full_key = self._get_key(key)
        value = await self.redis.get(full_key)

        if value is not None:
            self.hits += 1
            logger.debug(f"Cache hit for key: {key}")
            return json.loads(value)

        self.misses += 1
        logger.debug(f"Cache miss for key: {key}")
        return default

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL in seconds."""
        full_key = self._get_key(key)
        serialized = json.dumps(value)

        if ttl:
            return bool(await self.redis.setex(full_key, ttl, serialized))
        return bool(await self.redis.set(full_key, serialized))

    async def invalidate(self, key: str) -> int:
        """Invalidate a specific key."""
        full_key = self._get_key(key)
        return await self.redis.delete(full_key)

    async def invalidate_namespace(self, namespace: str) -> int:
        """Invalidate all keys in a namespace."""
        pattern = f"{self.namespace}:{namespace}:*"
        keys = await self.redis.keys(pattern)
        if keys:
            return await self.redis.delete(*keys)
        return 0

    async def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total) * 100 if total > 0 else 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.2f}%",
            "keys": await self.redis.dbsize(),
        }


def cache_key_builder(func: Callable, namespace: str, *args, **kwargs) -> str:
    """Build a cache key from function call."""
    # Convert args and kwargs to a stable string representation
    args_str = ",".join(str(arg) for arg in args)
    kwargs_str = ",".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    call_str = f"{func.__module__}.{func.__name__}({args_str},{kwargs_str})"

    # Create a hash of the call string
    key_hash = hashlib.md5(call_str.encode()).hexdigest()
    return f"{namespace}:{key_hash}"


def cached(
    ttl: int = 300,
    namespace: str = "default",
    key_func: Optional[Callable] = None,
):
    """Cache decorator for async functions with TTL and namespace support."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(
            *args,
            request: Optional[Request] = None,
            cache: Optional[RedisCache] = None,
            **kwargs,
        ) -> T:
            # Get cache instance from kwargs or request state
            cache = cache or (request.app.state.cache if request else None)
            if not cache:
                return await func(*args, request=request, **kwargs)

            # Build cache key
            key = (
                key_func(*args, **kwargs)
                if key_func
                else cache_key_builder(func, namespace, *args, **kwargs)
            )

            # Try to get from cache
            cached_result = await cache.get(key)
            if cached_result is not None:
                if request:
                    request.state.cached = True
                return cached_result

            # Call the function and cache the result
            result = await func(*args, request=request, **kwargs)
            await cache.set(key, result, ttl=ttl)

            if request:
                request.state.cached = False

            return result

        # Add invalidation method
        async def invalidate(*args, **kwargs) -> bool:
            cache = kwargs.get("cache") or (
                kwargs.get("request").app.state.cache if kwargs.get("request") else None
            )
            if not cache:
                return False

            key = (
                key_func(*args, **kwargs)
                if key_func
                else cache_key_builder(func, namespace, *args, **kwargs)
            )
            return await cache.invalidate(key)

        wrapper.invalidate = invalidate
        return wrapper

    return decorator


# Initialize the default cache instance
cache = RedisCache()


def setup_cache(app):
    """Set up cache on app startup."""
    app.state.cache = cache

    @app.on_event("shutdown")
    async def shutdown_event():
        await app.state.cache.redis.close()

    return cache
