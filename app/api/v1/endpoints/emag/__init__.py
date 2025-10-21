"""eMAG API endpoints.

This package contains all eMAG-related API endpoints organized by functionality:
- Integration: Core eMAG integration endpoints
- Products: Product sync, publishing, and management
- Orders: Order processing and management
- Inventory: Stock and inventory management
- Data: Addresses, customers, campaigns, etc.
- Core: New modular endpoints (products, orders, sync, cache)
"""

from .core.cache_endpoints import router as core_cache_router
from .core.orders import router as core_orders_router

# New modular core endpoints
from .core.products import router as core_products_router
from .core.sync import router as core_sync_router

# Data endpoints
from .emag_addresses import router as addresses_router

# Advanced features
from .emag_advanced import router as advanced_router
from .emag_campaigns import router as campaigns_router
from .emag_customers import router as customers_router
from .emag_db_offers import router as db_offers_router
from .emag_ean_matching import router as ean_matching_router

# Management
from .emag_management import router as management_router

# Inventory-related endpoints
# Note: emag_inventory moved to inventory/ folder - import from there instead
# from .emag_inventory import router as inventory_router
from .emag_offers import router as offers_router

# Order-related endpoints
from .emag_orders import router as orders_router
from .emag_phase2 import router as phase2_router
from .emag_pricing_intelligence import router as pricing_intelligence_router
from .emag_product_copy import router as product_copy_router
from .emag_product_publishing import router as product_publishing_router

# Product-related endpoints
from .emag_product_sync import router as product_sync_router

# Sync endpoints
from .emag_sync import router as sync_router
# emag_v449 removed - functionality not used
# enhanced_emag_sync removed - functionality not used
from .imports import router as imports_router
from .integration import router as integration_router
from .mappings import router as mappings_router

__all__ = [
    "integration_router",
    "imports_router",
    "mappings_router",
    # New modular core routers
    "core_products_router",
    "core_orders_router",
    "core_sync_router",
    "core_cache_router",
    # Legacy routers
    "product_sync_router",
    "product_publishing_router",
    "product_copy_router",
    "orders_router",
    # "inventory_router",  # Moved to inventory/ folder
    "offers_router",
    "db_offers_router",
    "addresses_router",
    "customers_router",
    "campaigns_router",
    "advanced_router",
    "pricing_intelligence_router",
    "ean_matching_router",
    "sync_router",
    "enhanced_sync_router",
    "phase2_router",
    "v449_router",
    "management_router",
]
