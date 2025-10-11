"""Role and Permission models for user authorization."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.permission import Permission
    from app.models.user import User
# Association tables
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("app.users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("app.roles.id"), primary_key=True),
    extend_existing=True,
    schema="app",
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("app.roles.id"), primary_key=True),
    Column(
        "permission_id", Integer, ForeignKey("app.permissions.id"), primary_key=True
    ),
    extend_existing=True,
    schema="app",
)


class Role(Base, TimestampMixin):
    """Role model for user role management."""

    __tablename__ = "roles"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    name: Mapped[str] = Column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = Column(String(255))
    is_system_role: Mapped[bool] = Column(Boolean, default=False)
    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User", secondary=user_roles, back_populates="roles"
    )
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", secondary=role_permissions, back_populates="roles"
    )

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


__all__ = ["Role", "user_roles", "role_permissions"]
