"""SQLAlchemy association tables."""

from sqlalchemy import Column, ForeignKey, Integer, Table

from app.db.base_class import Base

user_role = Table(
    "user_role",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("app.users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("app.roles.id"), primary_key=True),
    schema="app",
    extend_existing=True,
)

role_permission = Table(
    "role_permission",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("app.roles.id"), primary_key=True),
    Column(
        "permission_id", Integer, ForeignKey("app.permissions.id"), primary_key=True
    ),
    schema="app",
    extend_existing=True,
)
