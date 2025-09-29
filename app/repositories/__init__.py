"""Repository module for data access layer.

This package contains repository classes that abstract the data access layer,
providing a clean interface for the service layer to interact with the database.
"""

# Import repository functions to make them available at the package level
from .base_repository import BaseRepository, get_repository
from .product_repository import get_product_repository, ProductRepository
from .order_repository import get_order_repository, OrderRepository

__all__ = [
    "BaseRepository",
    "get_repository",
    "get_product_repository",
    "ProductRepository",
    "get_order_repository",
    "OrderRepository",
]
