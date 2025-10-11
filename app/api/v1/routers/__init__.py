"""API v1 Routers Package.

This package contains thematic routers that organize API endpoints
into logical groups for better maintainability and clarity.
"""

from .emag_router import router as emag_router
from .orders_router import router as orders_router
from .products_router import router as products_router
from .suppliers_router import router as suppliers_router

__all__ = [
    "emag_router",
    "products_router",
    "orders_router",
    "suppliers_router",
]
