"""Permission model for fine-grained access control."""

from typing import TYPE_CHECKING

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Mapped, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.role import Role


class Permission(Base, TimestampMixin):
    """Permission model for fine-grained access control.

    Attributes:
        name: Unique name of the permission (e.g., 'users:read')
        description: Human-readable description of the permission
    """

    __tablename__ = "permissions"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    name: Mapped[str] = Column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str] = Column(String(255), nullable=True)

    # Relationships
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="app.role_permissions",
        back_populates="permissions",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Permission {self.name}>"


__all__ = ["Permission"]
