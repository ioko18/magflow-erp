"""Suppliers Management Router.

Consolidates all supplier-related endpoints including:
- Supplier CRUD operations
- Supplier-product matching (1688.com integration)
- Supplier migration
- Supplier performance tracking
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    supplier_matching,
    supplier_migration,
    suppliers,
)

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

# Suppliers endpoints (supplier management)
router.include_router(suppliers, tags=["suppliers"])

# Supplier Product Matching endpoints (1688.com product matching and price comparison)
router.include_router(supplier_matching, prefix="/matching", tags=["supplier-matching"])

# Supplier migration endpoints
router.include_router(
    supplier_migration, prefix="/migration", tags=["supplier-migration"]
)
