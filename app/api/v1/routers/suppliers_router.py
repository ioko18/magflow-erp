"""Suppliers Management Router.

Consolidates all supplier-related endpoints including:
- Supplier CRUD operations
- Supplier-product matching (1688.com integration)
- Supplier migration
- Supplier performance tracking
- Google Sheets product promotion
"""

from fastapi import APIRouter

from app.api.v1.endpoints.suppliers import (
    promote_sheet_router,
    set_sheet_supplier_router,
    supplier_matching_router,
    supplier_migration_router,
    suppliers_router,
)

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

# Suppliers endpoints (supplier management)
router.include_router(suppliers_router, tags=["suppliers"])

# Supplier Product Matching endpoints (1688.com product matching and price comparison)
router.include_router(supplier_matching_router, prefix="/matching", tags=["supplier-matching"])

# Supplier migration endpoints
router.include_router(
    supplier_migration_router, prefix="/migration", tags=["supplier-migration"]
)

# Google Sheets product management
router.include_router(promote_sheet_router, tags=["supplier-sheets"])
router.include_router(set_sheet_supplier_router, tags=["supplier-sheets"])
