"""SQLAlchemy models for the application."""

from sqlalchemy.orm import registry

# Import all models here so they are properly registered with SQLAlchemy
from app.models.mixins import SoftDeleteMixin, TimestampMixin
from app.models.user import User, RefreshToken
from app.models.role import Role, Permission
from app.models.order import Order, OrderLine
from app.models.product import Product
from app.models.category import Category

# Create a mapper registry
mapper_registry = registry()

__all__ = [
    # Mixins
    "TimestampMixin",
    "SoftDeleteMixin",
    # Core models
    "User",
    "Role",
    "Permission",
    "RefreshToken",
    "Order",
    "OrderLine",
    "Product",
    "Category",
]
