"""SQLAlchemy models for the application."""
from sqlalchemy import Column, ForeignKey, Integer, Table
from sqlalchemy.orm import registry

from app.db.base_class import Base

# Import all models here so they are properly registered with SQLAlchemy
from app.models.mixins import TimestampMixin, SoftDeleteMixin  # noqa: F401
from app.models.role import Role, Permission  # noqa: F401
from app.models.user import User, RefreshToken  # noqa: F401

# Create a mapper registry
mapper_registry = registry()

# Association tables
user_role = Table(
    "user_role",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True)
)

role_permission = Table(
    "role_permission",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True)
)

__all__ = [
    'TimestampMixin',
    'SoftDeleteMixin',
    'User',
    'Role',
    'Permission',
    'RefreshToken',
    'user_role',
    'role_permission',
]
