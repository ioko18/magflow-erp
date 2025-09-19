"""Role and Permission models for role-based access control."""
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.user import User  # noqa: F401
    from app.models.permission import Permission  # noqa: F401

from app.db.base_class import Base
from app.models.mixins import TimestampMixin

# Association tables are now defined in the main __init__.py to avoid circular imports

class Role(Base, TimestampMixin):
    """Role model for role-based access control."""
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True)
    
    # Relationships
    users: Mapped[List["User"]] = relationship("User", secondary="user_role", back_populates="roles")
    permissions: Mapped[List["Permission"]] = relationship("Permission", secondary="role_permission", back_populates="roles")

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


class Permission(Base, TimestampMixin):
    """Permission model for fine-grained access control."""
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Relationships
    roles: Mapped[List["Role"]] = relationship("Role", secondary="role_permission", back_populates="permissions")

    def __repr__(self) -> str:
        return f"<Permission {self.name}>"
