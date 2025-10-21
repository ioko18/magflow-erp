"""CRUD operations for the application.

This module provides base CRUD (Create, Read, Update, Delete) operations
that can be extended by model-specific CRUD modules.
"""

# from .inventory import (  # Commented out due to circular import issues
#     CRUDWarehouse,
#     CRUDInventoryItem,
#     CRUDStockMovement,
#     CRUDStockReservation,
#     CRUDStockTransfer,
#     warehouse,
#     inventory_item,
#     stock_movement,
#     stock_reservation,
#     stock_transfer,
# )
from .user import CRUDUser, user

# from .role import CRUDPermission, CRUDRole,
# permission, role  # Commented out due to Permission model removal

__all__ = [
    "CRUDBase",
    "CRUDUser",
    # "CRUDRole",  # Commented out due to Permission model removal
    # "CRUDPermission",  # Commented out due to Permission model removal
    "user",
    # "role",  # Commented out due to Permission model removal
    # "permission",  # Commented out due to Permission model removal
    # Inventory CRUDs - commented out due to circular import issues
    # "CRUDWarehouse",
    # "CRUDInventoryItem",
    # "CRUDStockMovement",
    # "CRUDStockReservation",
    # "CRUDStockTransfer",
    # "warehouse",
    # "inventory_item",
    # "stock_movement",
    # "stock_reservation",
    # "stock_transfer",
]
