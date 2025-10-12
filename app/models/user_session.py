"""Database model for tracking user sessions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserSession(Base):
    """User session model for authentication tracking."""

    __tablename__ = "user_sessions"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(String(255), unique=True)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_activity: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="sessions")

    def touch(self) -> None:
        """Update last activity to current time."""
        self.last_activity = datetime.now(UTC)

    def __repr__(self) -> str:
        return f"<UserSession user_id={self.user_id} active={self.is_active}>"


__all__ = ["UserSession"]
