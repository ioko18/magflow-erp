"""Compatibility module providing catalog models for tests and legacy imports."""

from app.models.category import Category
from app.models.product import Product

__all__ = ["Product", "Category"]
