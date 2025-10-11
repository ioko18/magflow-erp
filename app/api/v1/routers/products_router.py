"""Products Management Router.

Consolidates all product-related endpoints including:
- Product CRUD operations
- Product import and export
- Product variants and relationships
- Inventory management
- Product updates and publishing
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    inventory_management,
    product_chinese_name,
    product_import,
    product_management,
    product_relationships,
    product_republish,
    product_update,
    product_variants_local,
    products_v1,
    stock_sync,
)

router = APIRouter(prefix="/products", tags=["products"])

# Product import endpoints (must be mounted before general products router
# to ensure specific routes like /products/mappings are not shadowed)
router.include_router(product_import, tags=["product-import"])

# Enhanced Products endpoints (v4.4.9) - mounted without additional prefix
# since router already has /products-v1
router.include_router(products_v1, tags=["products-v1"])

# Product Update endpoints (simplified Google Sheets import without eMAG mapping)
router.include_router(product_update, prefix="/update", tags=["product-update"])

# Product Relationships endpoints (variant tracking, PNK consistency, competition monitoring)
router.include_router(product_relationships, tags=["product-relationships"])

# Product Chinese Name update endpoints
router.include_router(product_chinese_name, prefix="/chinese-name", tags=["products"])

# Stock Synchronization endpoints (intelligent stock management across MAIN/FBE)
router.include_router(stock_sync, tags=["stock-sync"])

# Product Republishing endpoints (handle competitor attachment scenarios)
router.include_router(product_republish, tags=["product-republish"])

# Product Variants Local endpoints (create variants before eMAG publish)
router.include_router(product_variants_local, tags=["product-variants-local"])

# Product Management endpoints (comprehensive editing with history tracking)
router.include_router(product_management, tags=["product-management"])

# Inventory Management endpoints (low stock alerts, Excel export for supplier orders)
router.include_router(
    inventory_management, prefix="/inventory", tags=["inventory-management"]
)
