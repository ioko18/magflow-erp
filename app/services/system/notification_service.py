"""
Notification Service for MagFlow ERP.

Provides comprehensive notification management including:
- Creating and managing notifications
- User notification preferences
- Notification delivery across channels (push, email, SMS)
- Notification cleanup and archival
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.notification import (
    Notification,
    NotificationCategory,
    NotificationPriority,
    NotificationSettings,
    NotificationType,
)

logger = get_logger(__name__)


class NotificationService:
    """Service for managing user notifications."""

    def __init__(self, db: AsyncSession):
        """
        Initialize notification service.

        Args:
            db: Database session
        """
        self.db = db

    async def create_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        type: NotificationType = NotificationType.INFO,
        category: NotificationCategory = NotificationCategory.SYSTEM,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        data: dict[str, Any] | None = None,
        action_url: str | None = None,
        action_label: str | None = None,
        expires_at: datetime | None = None,
    ) -> Notification:
        """
        Create a new notification for a user.

        Args:
            user_id: ID of the user to notify
            title: Notification title
            message: Notification message
            type: Notification type (success, info, warning, error)
            category: Notification category
            priority: Notification priority
            data: Additional JSON data
            action_url: Optional action URL
            action_label: Optional action button label
            expires_at: Optional expiration datetime

        Returns:
            Created notification
        """
        try:
            # Check user notification settings
            settings = await self.get_user_settings(user_id)
            if settings and not settings.enabled:
                logger.info(f"Notifications disabled for user {user_id}")
                return None

            # Check priority threshold
            if settings and self._is_below_priority_threshold(
                priority, settings.min_priority
            ):
                logger.info(
                    f"Notification priority {priority} below threshold for user {user_id}"
                )
                return None

            # Check category preferences
            if settings and not settings.get_category_preference(
                category.value, "push"
            ):
                logger.info(f"Category {category} disabled for user {user_id}")
                return None

            notification = Notification(
                user_id=user_id,
                type=type,
                category=category,
                priority=priority,
                title=title,
                message=message,
                data=data,
                action_url=action_url,
                action_label=action_label,
                expires_at=expires_at,
                read=False,
                created_at=datetime.now(UTC),
            )

            self.db.add(notification)
            await self.db.commit()
            await self.db.refresh(notification)

            logger.info(f"Created notification {notification.id} for user {user_id}")

            # Send via other channels if enabled
            if settings:
                await self._send_via_channels(notification, settings)

            return notification

        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            await self.db.rollback()
            raise

    async def create_bulk_notifications(
        self, user_ids: list[int], title: str, message: str, **kwargs
    ) -> list[Notification]:
        """
        Create notifications for multiple users.

        Args:
            user_ids: List of user IDs
            title: Notification title
            message: Notification message
            **kwargs: Additional notification parameters

        Returns:
            List of created notifications
        """
        notifications = []
        for user_id in user_ids:
            try:
                notification = await self.create_notification(
                    user_id=user_id, title=title, message=message, **kwargs
                )
                if notification:
                    notifications.append(notification)
            except Exception as e:
                logger.error(f"Error creating notification for user {user_id}: {e}")
                continue

        return notifications

    async def get_user_notifications(
        self,
        user_id: int,
        unread_only: bool = False,
        category: NotificationCategory | None = None,
        priority: NotificationPriority | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        """
        Get notifications for a user with filters.

        Args:
            user_id: User ID
            unread_only: Only return unread notifications
            category: Filter by category
            priority: Filter by priority
            limit: Maximum number of notifications
            offset: Pagination offset

        Returns:
            List of notifications
        """
        try:
            query = select(Notification).where(Notification.user_id == user_id)

            if unread_only:
                query = query.where(~Notification.read)

            if category:
                query = query.where(Notification.category == category)

            if priority:
                query = query.where(Notification.priority == priority)

            # Filter out expired notifications
            query = query.where(
                or_(
                    Notification.expires_at.is_(None),
                    Notification.expires_at > datetime.now(UTC).replace(tzinfo=None),
                )
            )

            query = query.order_by(Notification.created_at.desc())
            query = query.limit(limit).offset(offset)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error getting notifications for user {user_id}: {e}")
            return []

    async def get_notification(self, notification_id: int) -> Notification | None:
        """Get a specific notification by ID."""
        try:
            result = await self.db.execute(
                select(Notification).where(Notification.id == notification_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting notification {notification_id}: {e}")
            return None

    async def mark_as_read(self, notification_id: int, user_id: int) -> bool:
        """
        Mark a notification as read.

        Args:
            notification_id: Notification ID
            user_id: User ID (for security check)

        Returns:
            True if successful
        """
        try:
            notification = await self.get_notification(notification_id)
            if not notification or notification.user_id != user_id:
                return False

            notification.read = True
            notification.read_at = datetime.now(UTC)

            await self.db.commit()
            logger.info(f"Marked notification {notification_id} as read")
            return True

        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            await self.db.rollback()
            return False

    async def mark_all_as_read(self, user_id: int) -> int:
        """
        Mark all notifications as read for a user.

        Args:
            user_id: User ID

        Returns:
            Number of notifications marked as read
        """
        try:
            result = await self.db.execute(
                select(Notification).where(
                    and_(Notification.user_id == user_id, ~Notification.read)
                )
            )
            notifications = result.scalars().all()

            count = 0
            for notification in notifications:
                notification.read = True
                notification.read_at = datetime.now(UTC)
                count += 1

            await self.db.commit()
            logger.info(f"Marked {count} notifications as read for user {user_id}")
            return count

        except Exception as e:
            logger.error(f"Error marking all notifications as read: {e}")
            await self.db.rollback()
            return 0

    async def delete_notification(self, notification_id: int, user_id: int) -> bool:
        """
        Delete a notification.

        Args:
            notification_id: Notification ID
            user_id: User ID (for security check)

        Returns:
            True if successful
        """
        try:
            notification = await self.get_notification(notification_id)
            if not notification or notification.user_id != user_id:
                return False

            await self.db.delete(notification)
            await self.db.commit()
            logger.info(f"Deleted notification {notification_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting notification: {e}")
            await self.db.rollback()
            return False

    async def delete_all_notifications(self, user_id: int) -> int:
        """
        Delete all notifications for a user.

        Args:
            user_id: User ID

        Returns:
            Number of notifications deleted
        """
        try:
            result = await self.db.execute(
                delete(Notification).where(Notification.user_id == user_id)
            )
            await self.db.commit()
            count = result.rowcount
            logger.info(f"Deleted {count} notifications for user {user_id}")
            return count

        except Exception as e:
            logger.error(f"Error deleting all notifications: {e}")
            await self.db.rollback()
            return 0

    async def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications for a user."""
        try:
            result = await self.db.execute(
                select(func.count(Notification.id)).where(
                    and_(
                        Notification.user_id == user_id,
                        ~Notification.read,
                        or_(
                            Notification.expires_at.is_(None),
                            Notification.expires_at > datetime.now(UTC).replace(tzinfo=None),
                        ),
                    )
                )
            )
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0

    async def get_statistics(self, user_id: int) -> dict[str, Any]:
        """
        Get notification statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary with statistics
        """
        try:
            # Total notifications
            total_result = await self.db.execute(
                select(func.count(Notification.id)).where(
                    Notification.user_id == user_id
                )
            )
            total = total_result.scalar() or 0

            # Unread count
            unread = await self.get_unread_count(user_id)

            # By category
            category_result = await self.db.execute(
                select(Notification.category, func.count(Notification.id))
                .where(Notification.user_id == user_id)
                .group_by(Notification.category)
            )
            by_category = {cat.value: count for cat, count in category_result.all()}

            # By priority
            priority_result = await self.db.execute(
                select(Notification.priority, func.count(Notification.id))
                .where(Notification.user_id == user_id)
                .group_by(Notification.priority)
            )
            by_priority = {pri.value: count for pri, count in priority_result.all()}

            return {
                "total": total,
                "unread": unread,
                "read": total - unread,
                "by_category": by_category,
                "by_priority": by_priority,
            }

        except Exception as e:
            logger.error(f"Error getting notification statistics: {e}")
            return {}

    # Notification Settings Methods

    async def get_user_settings(self, user_id: int) -> NotificationSettings | None:
        """Get notification settings for a user."""
        try:
            result = await self.db.execute(
                select(NotificationSettings).where(
                    NotificationSettings.user_id == user_id
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting notification settings: {e}")
            return None

    async def create_default_settings(self, user_id: int) -> NotificationSettings:
        """Create default notification settings for a new user."""
        try:
            settings = NotificationSettings(
                user_id=user_id,
                enabled=True,
                email_enabled=True,
                push_enabled=True,
                sms_enabled=False,
                min_priority="LOW",  # Use UPPERCASE to match PostgreSQL enum
                auto_delete_enabled=True,
                auto_delete_days=30,
            )

            self.db.add(settings)
            await self.db.commit()
            await self.db.refresh(settings)

            logger.info(f"Created default notification settings for user {user_id}")
            return settings

        except Exception as e:
            logger.error(f"Error creating default settings: {e}")
            await self.db.rollback()
            raise

    async def update_settings(
        self, user_id: int, **kwargs
    ) -> NotificationSettings | None:
        """
        Update notification settings for a user.

        Args:
            user_id: User ID
            **kwargs: Settings to update

        Returns:
            Updated settings
        """
        try:
            settings = await self.get_user_settings(user_id)
            if not settings:
                settings = await self.create_default_settings(user_id)

            # Update fields
            for key, value in kwargs.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)

            settings.updated_at = datetime.now(UTC)

            await self.db.commit()
            await self.db.refresh(settings)

            logger.info(f"Updated notification settings for user {user_id}")
            return settings

        except Exception as e:
            logger.error(f"Error updating notification settings: {e}")
            await self.db.rollback()
            return None

    async def cleanup_old_notifications(self, days: int = 30) -> int:
        """
        Clean up old read notifications.

        Args:
            days: Delete notifications older than this many days

        Returns:
            Number of notifications deleted
        """
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days)

            result = await self.db.execute(
                delete(Notification).where(
                    and_(Notification.read, Notification.created_at < cutoff_date)
                )
            )
            await self.db.commit()
            count = result.rowcount
            logger.info(f"Cleaned up {count} old notifications")
            return count

        except Exception as e:
            logger.error(f"Error cleaning up old notifications: {e}")
            await self.db.rollback()
            return 0

    async def cleanup_expired_notifications(self) -> int:
        """
        Delete expired notifications.

        Returns:
            Number of notifications deleted
        """
        try:
            result = await self.db.execute(
                delete(Notification).where(
                    and_(
                        Notification.expires_at.isnot(None),
                        Notification.expires_at < datetime.now(UTC).replace(tzinfo=None),
                    )
                )
            )
            await self.db.commit()
            count = result.rowcount
            logger.info(f"Cleaned up {count} expired notifications")
            return count

        except Exception as e:
            logger.error(f"Error cleaning up expired notifications: {e}")
            await self.db.rollback()
            return 0

    # Helper methods

    def _is_below_priority_threshold(
        self, priority: NotificationPriority, min_priority: NotificationPriority
    ) -> bool:
        """Check if notification priority is below user's threshold."""
        priority_order = {
            NotificationPriority.LOW: 0,
            NotificationPriority.MEDIUM: 1,
            NotificationPriority.HIGH: 2,
            NotificationPriority.CRITICAL: 3,
        }
        return priority_order[priority] < priority_order[min_priority]

    async def _send_via_channels(
        self, notification: Notification, settings: NotificationSettings
    ) -> None:
        """
        Send notification via additional channels (email, SMS).

        Args:
            notification: Notification to send
            settings: User notification settings
        """
        try:
            # Email notification
            if settings.email_enabled and settings.get_category_preference(
                notification.category.value, "email"
            ):
                await self._send_email_notification(notification)

            # SMS notification
            if settings.sms_enabled and settings.get_category_preference(
                notification.category.value, "sms"
            ):
                await self._send_sms_notification(notification)

        except Exception as e:
            logger.error(f"Error sending notification via channels: {e}")

    async def _send_email_notification(self, notification: Notification) -> None:
        """Send notification via email using Email Service."""
        try:
            from app.services.email_service import email_service

            # Get user email
            user_email = None
            if notification.user_id:
                from app.models.user import User

                user = await self.db.get(User, notification.user_id)
                if user and user.email:
                    user_email = user.email

            if not user_email:
                logger.warning(f"No email found for notification {notification.id}")
                return

            # Send notification email
            success = await email_service.send_notification_email(
                to_email=user_email,
                notification_type=notification.category.value,
                title=notification.title,
                message=notification.message,
                priority=notification.priority.value,
                action_url=f"{getattr(settings, 'APP_URL', 'http://localhost:8000')}/notifications/{notification.id}",
                action_text="View Notification",
            )

            if success:
                logger.info(f"Email notification sent successfully: {notification.id}")
            else:
                logger.error(f"Failed to send email notification: {notification.id}")

        except Exception as e:
            logger.error(
                f"Error sending email notification {notification.id}: {e}",
                exc_info=True,
            )

    async def _send_sms_notification(self, notification: Notification) -> None:
        """Send notification via SMS - DISABLED per user request."""
        # SMS notifications are disabled - user does not want SMS service
        logger.debug(
            f"SMS notifications disabled, skipping notification {notification.id}"
        )
