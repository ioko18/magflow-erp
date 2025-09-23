"""Redis caching service for MagFlow ERP."""

import asyncio
import json
import logging
import pickle
from typing import Any, Dict, List, Optional

from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import ConnectionError, RedisError

from ..core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Service for Redis caching operations."""

    def __init__(self):
        """Initialize Redis connection pool."""
        self.pool = None
        self.redis_client: Optional[Redis] = None
        self._connected = False

    async def connect(self) -> None:
        """Create Redis connection pool and client."""
        if settings.REDIS_ENABLED:
            try:
                self.pool = ConnectionPool(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    password=settings.REDIS_PASSWORD,
                    socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                    socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                    retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT,
                    max_connections=settings.REDIS_MAX_CONNECTIONS,
                    decode_responses=True,
                )
                self.redis_client = Redis(connection_pool=self.pool)
                # Test connection
                await self.redis_client.ping()
                self._connected = True
                logger.info("Redis cache service connected successfully")
            except (ConnectionError, RedisError) as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self._connected = False
        else:
            logger.info("Redis caching disabled")
            self._connected = False

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            self._connected = False
            logger.info("Redis cache service disconnected")

    async def is_connected(self) -> bool:
        """Check if Redis is connected."""
        if not self.redis_client or not self._connected:
            return False

        try:
            await self.redis_client.ping()
            return True
        except (ConnectionError, RedisError):
            self._connected = False
            return False

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: str = "default",
    ) -> bool:
        """Set a value in cache."""
        if not await self.is_connected():
            return False

        try:
            # Add namespace to key
            namespaced_key = f"{namespace}:{key}"

            # Serialize value based on type
            if isinstance(value, (str, int, float, bool)):
                serialized_value = str(value)
            elif isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, default=str)
            else:
                serialized_value = pickle.dumps(value)

            # Set in Redis
            if ttl:
                result = await self.redis_client.setex(
                    namespaced_key,
                    ttl,
                    serialized_value,
                )
            else:
                result = await self.redis_client.set(namespaced_key, serialized_value)

            return bool(result)

        except (RedisError, TypeError, pickle.PicklingError) as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            return False

    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Get a value from cache."""
        if not await self.is_connected():
            return None

        try:
            # Add namespace to key
            namespaced_key = f"{namespace}:{key}"

            # Get from Redis
            value = await self.redis_client.get(namespaced_key)
            if value is None:
                return None

            # Try to parse as JSON first
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # Try to unpickle
                try:
                    return pickle.loads(value.encode())
                except (pickle.UnpicklingError, AttributeError):
                    # Return as string
                    return value

        except RedisError as e:
            logger.error(f"Failed to get cache key {key}: {e}")
            return None

    async def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete a key from cache."""
        if not await self.is_connected():
            return False

        try:
            namespaced_key = f"{namespace}:{key}"
            result = await self.redis_client.delete(namespaced_key)
            return bool(result)

        except RedisError as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str, namespace: str = "default") -> int:
        """Delete keys matching a pattern."""
        if not await self.is_connected():
            return 0

        try:
            namespaced_pattern = f"{namespace}:{pattern}"
            keys = await self.redis_client.keys(namespaced_pattern)

            if keys:
                result = await self.redis_client.delete(*keys)
                return result
            return 0

        except RedisError as e:
            logger.error(f"Failed to delete cache pattern {pattern}: {e}")
            return 0

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions from cache."""
        try:
            # Clean up expired session entries
            expired_count = 0
            # Get all session keys
            session_pattern = "sessions:session:*"
            keys = await self.redis_client.keys(session_pattern)

            for key in keys:
                # Check if session is expired
                ttl = await self.redis_client.ttl(key)
                if ttl <= 0:
                    await self.redis_client.delete(key)
                    expired_count += 1

            logger.info(f"Cleaned up {expired_count} expired sessions")
            return expired_count

        except RedisError as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0

    async def exists(self, key: str, namespace: str = "default") -> bool:
        """Check if key exists in cache."""
        if not await self.is_connected():
            return False

        try:
            namespaced_key = f"{namespace}:{key}"
            return bool(await self.redis_client.exists(namespaced_key))

        except RedisError as e:
            logger.error(f"Failed to check cache key {key}: {e}")
            return False

    async def expire(self, key: str, ttl: int, namespace: str = "default") -> bool:
        """Set TTL for a key."""
        if not await self.is_connected():
            return False

        try:
            namespaced_key = f"{namespace}:{key}"
            return bool(await self.redis_client.expire(namespaced_key, ttl))

        except RedisError as e:
            logger.error(f"Failed to set TTL for cache key {key}: {e}")
            return False

    async def ttl(self, key: str, namespace: str = "default") -> int:
        """Get TTL for a key."""
        if not await self.is_connected():
            return -2  # Key doesn't exist

        try:
            namespaced_key = f"{namespace}:{key}"
            return await self.redis_client.ttl(namespaced_key)

        except RedisError as e:
            logger.error(f"Failed to get TTL for cache key {key}: {e}")
            return -2

    async def increment(
        self,
        key: str,
        amount: int = 1,
        namespace: str = "default",
    ) -> Optional[int]:
        """Increment a numeric value in cache."""
        if not await self.is_connected():
            return None

        try:
            namespaced_key = f"{namespace}:{key}"
            return await self.redis_client.incr(namespaced_key, amount)

        except RedisError as e:
            logger.error(f"Failed to increment cache key {key}: {e}")
            return None

    async def get_or_set(
        self,
        key: str,
        value_func,
        ttl: Optional[int] = None,
        namespace: str = "default",
    ) -> Any:
        """Get value from cache or set it if not exists."""
        # Try to get from cache
        cached_value = await self.get(key, namespace)
        if cached_value is not None:
            return cached_value

        # Get value from function
        try:
            value = (
                await value_func()
                if asyncio.iscoroutinefunction(value_func)
                else value_func()
            )
        except Exception as e:
            logger.error(f"Error executing value function for key {key}: {e}")
            return None

        # Set in cache
        await self.set(key, value, ttl, namespace)
        return value

    async def cache_database_query(
        self,
        query_key: str,
        query_func,
        ttl: int = 300,  # 5 minutes default
        namespace: str = "db_query",
    ):
        """Cache database query results."""
        return await self.get_or_set(query_key, query_func, ttl, namespace)

    async def cache_user_session(
        self,
        session_token: str,
        session_data: Dict[str, Any],
        ttl: int = 3600,  # 1 hour
        namespace: str = "sessions",
    ) -> bool:
        """Cache user session data."""
        key = f"session:{session_token}"
        return await self.set(key, session_data, ttl, namespace)

    async def get_user_session(
        self,
        session_token: str,
        namespace: str = "sessions",
    ) -> Optional[Dict[str, Any]]:
        """Get cached user session data."""
        key = f"session:{session_token}"
        return await self.get(key, namespace)

    async def delete_user_session(
        self,
        session_token: str,
        namespace: str = "sessions",
    ) -> bool:
        """Delete cached user session data."""
        key = f"session:{session_token}"
        return await self.delete(key, namespace)

    async def cache_user_permissions(
        self,
        user_id: int,
        permissions: List[Dict[str, str]],
        ttl: int = 600,  # 10 minutes
        namespace: str = "permissions",
    ) -> bool:
        """Cache user permissions."""
        key = f"user:{user_id}:permissions"
        return await self.set(key, permissions, ttl, namespace)

    async def get_user_permissions(
        self,
        user_id: int,
        namespace: str = "permissions",
    ) -> Optional[List[Dict[str, str]]]:
        """Get cached user permissions."""
        key = f"user:{user_id}:permissions"
        return await self.get(key, namespace)

    async def invalidate_user_cache(self, user_id: int) -> bool:
        """Invalidate all cache entries for a user."""
        try:
            # Delete user permissions
            await self.delete(f"user:{user_id}:permissions", "permissions")

            # Delete user sessions pattern
            session_count = await self.delete_pattern(f"user:{user_id}:*", "sessions")

            logger.info(
                f"Invalidated cache for user {user_id}, deleted {session_count} sessions",
            )
            return True

        except Exception as e:
            logger.error(f"Failed to invalidate user cache for user {user_id}: {e}")
            return False

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not await self.is_connected():
            return {"connected": False, "error": "Redis not connected"}

        try:
            info = await self.redis_client.info("memory")
            return {
                "connected": True,
                "used_memory": info.get("used_memory_human", "unknown"),
                "used_memory_peak": info.get("used_memory_peak_human", "unknown"),
                "total_connections": await self.redis_client.dbsize(),
            }
        except RedisError as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"connected": True, "error": str(e)}


# Global cache service instance
cache_service = CacheService()


async def get_cache_service() -> CacheService:
    """Get cache service instance."""
    if not cache_service._connected:
        await cache_service.connect()
    return cache_service


class CacheManager:
    """Manager for cache operations with automatic cleanup."""

    def __init__(self, cache_service: CacheService):
        self.cache = cache_service

    async def get_or_set_user(self, user_id: int, fetch_func) -> Any:
        """Get user from cache or database."""
        key = f"user:{user_id}"
        return await self.cache.get_or_set(key, fetch_func, 600, "users")  # 10 minutes

    async def get_or_set_permissions(
        self,
        user_id: int,
        fetch_func,
    ) -> List[Dict[str, str]]:
        """Get user permissions from cache or database."""
        key = f"user:{user_id}:permissions"
        return await self.cache.get_or_set(
            key,
            fetch_func,
            600,
            "permissions",
        )  # 10 minutes

    async def invalidate_user_data(self, user_id: int):
        """Invalidate all cached data for a user."""
        await self.cache.invalidate_user_cache(user_id)

    async def cleanup_expired(self):
        """Clean up expired cache entries."""
        return await self.cache.cleanup_expired_sessions()
