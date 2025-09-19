"""SQLAlchemy models for user authentication and authorization."""
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.role import Role  # noqa: F401
    from app.models.refresh_token import RefreshToken  # noqa: F401

from app.db.base_class import Base
from app.models.mixins import TimestampMixin

class UserRole(str, Enum):
    """Minimal user role enum for tests and role-based checks."""
    ADMIN = "admin"
    USER = "user"

class User(Base, TimestampMixin):
    """User account model for authentication and authorization."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean(), default=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_failed_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean(), default=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Relationships
    roles: Mapped[List["Role"]] = relationship("Role", secondary="user_role", back_populates="users")
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship("RefreshToken", back_populates="user")
    
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


class RefreshToken(Base, TimestampMixin):
    """Refresh token model for JWT refresh tokens."""
    __tablename__ = "refresh_tokens"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    token: Mapped[str] = mapped_column(String(512), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean(), default=False)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")
    
    def is_expired(self) -> bool:
        """Check if the refresh token is expired."""
        return datetime.utcnow() > self.expires_at
    
    def revoke(self) -> None:
        """Revoke the refresh token."""
        self.is_revoked = True
        self.updated_at = datetime.utcnow()


# The role_permission table is now defined in role.py
