"""
Notification models for MagFlow ERP.

Provides database models for user notifications and notification preferences.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class NotificationType(str, enum.Enum):
    """Notification type enumeration."""

    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class NotificationCategory(str, enum.Enum):
    """Notification category enumeration."""

    SYSTEM = "system"
    EMAG = "emag"
    ORDERS = "orders"
    USERS = "users"
    INVENTORY = "inventory"
    SYNC = "sync"
    PAYMENT = "payment"
    SHIPPING = "shipping"


class NotificationPriority(str, enum.Enum):
    """Notification priority enumeration."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Notification(Base):
    """
    User notification model.

    Stores individual notifications for users with metadata like type,
    category, priority, and read status.
    """

    __tablename__ = "notifications"
    __table_args__ = {"schema": "app"}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("app.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Notification content
    type = Column(SQLEnum(NotificationType), nullable=False, default="info")
    category = Column(SQLEnum(NotificationCategory), nullable=False, default="system")
    priority = Column(SQLEnum(NotificationPriority), nullable=False, default="medium")

    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Additional data (JSON format for flexibility)
    data = Column(JSON, nullable=True)

    # Action link (optional)
    action_url = Column(String(500), nullable=True)
    action_label = Column(String(100), nullable=True)

    # Status
    read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, title='{self.title}', read={self.read})>"

    def to_dict(self):
        """Convert notification to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type.value if self.type else None,
            "category": self.category.value if self.category else None,
            "priority": self.priority.value if self.priority else None,
            "title": self.title,
            "message": self.message,
            "data": self.data,
            "action_url": self.action_url,
            "action_label": self.action_label,
            "read": self.read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class NotificationSettings(Base):
    """
    User notification settings model.

    Stores user preferences for different types of notifications
    across various channels (email, push, SMS, etc.).
    """

    __tablename__ = "notification_settings"
    __table_args__ = {"schema": "app"}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("app.users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Global settings
    enabled = Column(Boolean, default=True, nullable=False)

    # Channel preferences
    email_enabled = Column(Boolean, default=True, nullable=False)
    push_enabled = Column(Boolean, default=True, nullable=False)
    sms_enabled = Column(Boolean, default=False, nullable=False)

    # Category-specific settings (JSON for flexibility)
    # Format: {"category_name": {"email": true, "push": true, "sms": false}}
    category_preferences = Column(JSON, nullable=True)

    # Priority threshold (only show notifications above this priority)
    min_priority = Column(SQLEnum(NotificationPriority), default="low", nullable=False)

    # Quiet hours
    quiet_hours_enabled = Column(Boolean, default=False, nullable=False)
    quiet_hours_start = Column(String(5), nullable=True)  # Format: "HH:MM"
    quiet_hours_end = Column(String(5), nullable=True)  # Format: "HH:MM"

    # Auto-delete old notifications
    auto_delete_enabled = Column(Boolean, default=True, nullable=False)
    auto_delete_days = Column(Integer, default=30, nullable=False)

    # Digest settings
    digest_enabled = Column(Boolean, default=False, nullable=False)
    digest_frequency = Column(
        String(20), default="daily", nullable=False
    )  # daily, weekly

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="notification_settings")

    def __repr__(self):
        return f"<NotificationSettings(user_id={self.user_id}, enabled={self.enabled})>"

    def to_dict(self):
        """Convert notification settings to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "enabled": self.enabled,
            "email_enabled": self.email_enabled,
            "push_enabled": self.push_enabled,
            "sms_enabled": self.sms_enabled,
            "category_preferences": self.category_preferences or {},
            "min_priority": self.min_priority.value if self.min_priority else "low",
            "quiet_hours_enabled": self.quiet_hours_enabled,
            "quiet_hours_start": self.quiet_hours_start,
            "quiet_hours_end": self.quiet_hours_end,
            "auto_delete_enabled": self.auto_delete_enabled,
            "auto_delete_days": self.auto_delete_days,
            "digest_enabled": self.digest_enabled,
            "digest_frequency": self.digest_frequency,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_category_preference(self, category: str, channel: str = "push") -> bool:
        """
        Get notification preference for a specific category and channel.

        Args:
            category: Notification category
            channel: Notification channel (email, push, sms)

        Returns:
            bool: Whether notifications are enabled for this category/channel
        """
        if not self.enabled:
            return False

        # Check channel is enabled
        if channel == "email" and not self.email_enabled or channel == "push" and not self.push_enabled or channel == "sms" and not self.sms_enabled:
            return False

        # Check category preferences
        if self.category_preferences and category in self.category_preferences:
            return self.category_preferences[category].get(channel, True)

        return True  # Default to enabled if no specific preference
