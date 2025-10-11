"""
Core eMAG API endpoints.

This module contains the core integration endpoints for eMAG marketplace.
"""

from .orders import router as orders_router
from .products import router as products_router
from .sync import router as sync_router

__all__ = ["products_router", "orders_router", "sync_router"]
