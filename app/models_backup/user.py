"""SQLAlchemy models for user authentication and authorization."""

from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.associations import user_roles
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.refresh_token import RefreshToken

    from app.models.audit_log import AuditLog
    from app.models.notification import Notification, NotificationSettings
    from app.models.order import Order
    from app.models.role import Role
    from app.models.user_session import UserSession


class UserRole(str, Enum):
    """Minimal user role enum for tests and role-based checks."""

    ADMIN = "admin"
    USER = "user"


class User(Base, TimestampMixin):
    """User account model for authentication and authorization."""

    __tablename__ = "users"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean(), default=False)
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_failed_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    email_verified: Mapped[bool] = mapped_column(Boolean(), default=False)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary=user_roles,
        back_populates="users",
        lazy="selectin",
        cascade="save-update, merge, refresh-expire, expunge",
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="customer",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    notification_settings: Mapped[Optional["NotificationSettings"]] = relationship(
        "NotificationSettings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Helper methods
    def __repr__(self) -> str:
        return f"<User {self.email}>"

    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return bool(self.id) and self.is_active

    @property
    def is_admin(self) -> bool:
        """Check if user has admin privileges.

        Returns:
            bool: True if user is a superuser or has the admin role
        """
        if self.is_superuser:
            return True
        return any(role.name == UserRole.ADMIN for role in (self.roles or []))

    def has_permission(self, permission_name: str) -> bool:
        """Check if user has a specific permission.

        Args:
            permission_name: Name of the permission to check

        Returns:
            bool: True if user has the permission or is a superuser
        """
        if self.is_superuser:
            return True

        for role in self.roles or []:
            if any(p.name == permission_name for p in (role.permissions or [])):
                return True
        return False

    def check_password(self, password: str) -> bool:
        """Check if the provided password matches the hashed password."""
        from app.core.security import verify_password

        return verify_password(password, self.hashed_password)

    def set_password(self, password: str) -> None:
        """Set a new password for the user."""
        from app.core.security import get_password_hash

        self.hashed_password = get_password_hash(password)

    def increment_failed_login_attempts(self) -> None:
        """Increment failed login attempts and update last failed login time."""
        self.failed_login_attempts += 1
        self.last_failed_login = datetime.now(UTC)

    def reset_failed_login_attempts(self) -> None:
        """Reset failed login attempts counter."""
        self.failed_login_attempts = 0
        self.last_failed_login = None


class RefreshToken(Base, TimestampMixin):
    """Refresh token model for JWT refresh tokens."""

    __tablename__ = "refresh_tokens"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    token: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        index=True,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    is_revoked: Mapped[bool] = mapped_column(Boolean(), default=False)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.users.id"),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    def is_expired(self) -> bool:
        """Check if the refresh token is expired."""
        return datetime.now(UTC) > self.expires_at

    def revoke(self) -> None:
        """Revoke the refresh token."""
        self.is_revoked = True
        self.updated_at = datetime.now(UTC)


# The role_permission table is now defined in role.py
