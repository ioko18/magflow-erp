"""Inventory-related API endpoints."""

from .emag_inventory import router as emag_inventory_router
from .emag_inventory_sync import router as emag_inventory_sync_router
from .inventory_management import router as inventory_management_router
from .low_stock_suppliers import router as low_stock_suppliers_router
from .stock_sync import router as stock_sync_router

__all__ = [
    "inventory_management_router",
    "stock_sync_router",
    "emag_inventory_router",
    "low_stock_suppliers_router",
    "emag_inventory_sync_router",
]
