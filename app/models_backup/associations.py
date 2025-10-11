"""Association tables for many-to-many relationships."""

from sqlalchemy import Column, ForeignKey, Integer, Table

from app.db.base_class import Base

# Association table for user-role many-to-many relationship
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("app.users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("app.roles.id"), primary_key=True),
    extend_existing=True,
    schema="app",
)

# Association table for role-permission many-to-many relationship
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

# Association table for product-category many-to-many relationship
product_categories = Table(
    "product_categories",
    Base.metadata,
    Column("product_id", Integer, ForeignKey("app.products.id"), primary_key=True),
    Column("category_id", Integer, ForeignKey("app.categories.id"), primary_key=True),
    extend_existing=True,
    schema="app",
)

__all__ = ["user_roles", "role_permissions", "product_categories"]
