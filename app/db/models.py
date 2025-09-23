"""Synchronous SQLAlchemy models required by tests.

Defines `Product` and `Category` with a many-to-many relationship used by
`tests/test_cursor_pagination.py`.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.order import Order, OrderLine

from .base_class import Base

# Association table for Product<->Category many-to-many
product_categories = Table(
    "product_categories",
    Base.metadata,
    Column("product_id", ForeignKey("products.id"), primary_key=True),
    Column("category_id", ForeignKey("categories.id"), primary_key=True),
    extend_existing=True,
)


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    products: Mapped[List[Product]] = relationship(
        "Product",
        secondary=product_categories,
        back_populates="categories",
        lazy="selectin",
    )


class Product(Base):
    __tablename__ = "products"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    categories: Mapped[List[Category]] = relationship(
        Category,
        secondary=product_categories,
        back_populates="products",
        lazy="selectin",
    )
    order_lines: Mapped[List[OrderLine]] = relationship(
        "OrderLine",
        back_populates="product",
    )


# Association tables for RBAC
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
    extend_existing=True,
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id"), primary_key=True),
    extend_existing=True,
)


class Permission(Base):
    """Permission model for granular access control."""

    __tablename__ = "permissions"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    resource: Mapped[str] = mapped_column(
        String(100),
        index=True,
    )  # e.g., "users", "products"
    action: Mapped[str] = mapped_column(
        String(50),
        index=True,
    )  # e.g., "read", "write", "delete"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
    )

    # Many-to-many relationship with roles
    roles: Mapped[List[Role]] = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions",
    )


class Role(Base):
    """Role model for user role management."""

    __tablename__ = "roles"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    is_system_role: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
    )

    # Many-to-many relationships
    users: Mapped[List[User]] = relationship(
        "User",
        secondary=user_roles,
        back_populates="roles",
    )
    permissions: Mapped[List[Permission]] = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
    )


class AuditLog(Base):
    """Audit log model for tracking user actions."""

    __tablename__ = "audit_logs"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(100),
        index=True,
    )  # e.g., "login", "create", "update", "delete"
    resource: Mapped[str] = mapped_column(
        String(100),
        index=True,
    )  # e.g., "users", "products", "orders"
    resource_id: Mapped[Optional[str]] = mapped_column(
        String(100),
    )  # ID of the affected resource
    details: Mapped[Optional[str]] = mapped_column(
        Text,
    )  # JSON string with detailed information
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))  # IPv4 or IPv6
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        index=True,
    )
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Relationship with user
    user: Mapped[Optional[User]] = relationship("User", back_populates="audit_logs")


class UserSession(Base):
    """User session model for tracking active sessions."""

    __tablename__ = "user_sessions"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    session_token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_activity: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
    )

    # Relationship with user
    user: Mapped[User] = relationship("User", back_populates="sessions")


class User(Base):
    """Enhanced User model with RBAC support."""

    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_failed_login: Mapped[Optional[datetime]] = mapped_column(DateTime)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))

    # RBAC relationships
    roles: Mapped[List[Role]] = relationship(
        "Role",
        secondary=user_roles,
        back_populates="users",
    )
    audit_logs: Mapped[List[AuditLog]] = relationship("AuditLog", back_populates="user")
    sessions: Mapped[List[UserSession]] = relationship(
        "UserSession",
        back_populates="user",
    )
    orders: Mapped[List[Order]] = relationship("Order", back_populates="customer")
    refresh_tokens: Mapped[List[RefreshToken]] = relationship(
        "RefreshToken",
        back_populates="user",
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"

    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return bool(self.id)

    @property
    def is_admin(self) -> bool:
        """Check if user has admin privileges."""
        return self.is_superuser

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
        self.last_failed_login = datetime.utcnow()

    def reset_failed_login_attempts(self) -> None:
        """Reset failed login attempts counter."""
        self.failed_login_attempts = 0
        self.last_failed_login = None


class RefreshToken(Base):
    """Refresh token model for JWT refresh tokens."""

    __tablename__ = "refresh_tokens"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    token: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        index=True,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="refresh_tokens")

    def is_expired(self) -> bool:
        """Check if the refresh token is expired."""
        return datetime.utcnow() > self.expires_at

    def revoke(self) -> None:
        """Revoke the refresh token."""
        self.is_revoked = True
        self.updated_at = datetime.utcnow()
