"""
User Session Tracking Service

Tracks active user sessions for real-time metrics and monitoring.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_redis
from app.core.logging_config import get_logger
from app.models.user_session import UserSession

logger = get_logger(__name__)


class SessionTrackingService:
    """Service for tracking active user sessions."""

    def __init__(self, db: AsyncSession):
        """
        Initialize session tracking service.

        Args:
            db: Database session
        """
        self.db = db
        self._redis = None

    async def _get_redis(self):
        """Get Redis client lazily."""
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis

    async def track_user_activity(
        self, user_id: int, session_id: str, activity_type: str = "page_view"
    ) -> bool:
        """
        Track user activity.

        Args:
            user_id: User ID
            session_id: Session ID
            activity_type: Type of activity

        Returns:
            True if tracked successfully
        """
        try:
            redis = await self._get_redis()

            # Update last activity timestamp in Redis
            key = f"user:activity:{user_id}:{session_id}"
            await redis.setex(
                key,
                1800,  # 30 minutes TTL
                datetime.now(UTC).isoformat(),
            )

            # Track activity count
            activity_key = f"user:activity:count:{user_id}"
            await redis.incr(activity_key)
            await redis.expire(activity_key, 86400)  # 24 hours

            return True

        except Exception as e:
            logger.error(f"Error tracking user activity: {e}")
            return False

    async def get_active_users_count(self, minutes: int = 30) -> int:
        """
        Get count of active users in the last N minutes.

        Args:
            minutes: Time window in minutes

        Returns:
            Number of active users
        """
        try:
            redis = await self._get_redis()

            # Scan for active user keys
            pattern = "user:activity:*:*"
            active_sessions = set()

            async for key in redis.scan_iter(match=pattern):
                # Extract user_id from key
                parts = key.decode("utf-8").split(":")
                if len(parts) >= 3:
                    user_id = parts[2]
                    active_sessions.add(user_id)

            return len(active_sessions)

        except Exception as e:
            logger.error(f"Error getting active users count: {e}")
            # Fallback to database query
            return await self._get_active_users_from_db(minutes)

    async def _get_active_users_from_db(self, minutes: int = 30) -> int:
        """
        Fallback: Get active users from database.

        Args:
            minutes: Time window in minutes

        Returns:
            Number of active users
        """
        try:
            cutoff_time = datetime.now(UTC) - timedelta(minutes=minutes)

            query = select(func.count(func.distinct(UserSession.user_id))).where(
                UserSession.last_activity >= cutoff_time
            )

            result = await self.db.execute(query)
            count = result.scalar()

            return count or 0

        except Exception as e:
            logger.error(f"Error getting active users from DB: {e}")
            return 0

    async def get_user_sessions(self, user_id: int) -> list[dict]:
        """
        Get all active sessions for a user.

        Args:
            user_id: User ID

        Returns:
            List of session information
        """
        try:
            query = (
                select(UserSession)
                .where(and_(UserSession.user_id == user_id, UserSession.is_active))
                .order_by(UserSession.last_activity.desc())
            )

            result = await self.db.execute(query)
            sessions = result.scalars().all()

            return [
                {
                    "session_id": session.session_id,
                    "ip_address": session.ip_address,
                    "user_agent": session.user_agent,
                    "last_activity": session.last_activity.isoformat()
                    if session.last_activity
                    else None,
                    "created_at": session.created_at.isoformat()
                    if session.created_at
                    else None,
                }
                for session in sessions
            ]

        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            return []

    async def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate a user session.

        Args:
            session_id: Session ID to invalidate

        Returns:
            True if invalidated successfully
        """
        try:
            # Update database
            query = select(UserSession).where(UserSession.session_id == session_id)
            result = await self.db.execute(query)
            session = result.scalar_one_or_none()

            if session:
                session.is_active = False
                await self.db.commit()

            # Remove from Redis
            redis = await self._get_redis()
            pattern = f"user:activity:*:{session_id}"
            async for key in redis.scan_iter(match=pattern):
                await redis.delete(key)

            return True

        except Exception as e:
            logger.error(f"Error invalidating session: {e}")
            await self.db.rollback()
            return False

    async def cleanup_expired_sessions(self, hours: int = 24) -> int:
        """
        Cleanup expired sessions from database.

        Args:
            hours: Sessions older than this are considered expired

        Returns:
            Number of sessions cleaned up
        """
        try:
            cutoff_time = datetime.now(UTC) - timedelta(hours=hours)

            # Find expired sessions
            query = select(UserSession).where(
                and_(UserSession.last_activity < cutoff_time, UserSession.is_active)
            )

            result = await self.db.execute(query)
            expired_sessions = result.scalars().all()

            # Mark as inactive
            count = 0
            for session in expired_sessions:
                session.is_active = False
                count += 1

            await self.db.commit()

            logger.info(f"Cleaned up {count} expired sessions")
            return count

        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
            await self.db.rollback()
            return 0

    async def get_session_statistics(self) -> dict:
        """
        Get session statistics.

        Returns:
            Dictionary with session statistics
        """
        try:
            # Active sessions
            active_query = select(func.count(UserSession.id)).where(
                UserSession.is_active
            )
            active_result = await self.db.execute(active_query)
            active_count = active_result.scalar() or 0

            # Total sessions today
            today_start = datetime.now(UTC).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            today_query = select(func.count(UserSession.id)).where(
                UserSession.created_at >= today_start
            )
            today_result = await self.db.execute(today_query)
            today_count = today_result.scalar() or 0

            # Active users (last 30 minutes)
            active_users = await self.get_active_users_count(30)

            return {
                "active_sessions": active_count,
                "sessions_today": today_count,
                "active_users_30min": active_users,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting session statistics: {e}")
            return {
                "active_sessions": 0,
                "sessions_today": 0,
                "active_users_30min": 0,
                "error": str(e),
            }
