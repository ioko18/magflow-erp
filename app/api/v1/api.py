"""API v1 aggregator router.

Exposes `api_router` and includes versioned endpoint routers.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api import categories
from app.api import health as complex_health
from app.api.v1.endpoints import (
    admin,
    cancellations,
    database,
    emag_addresses,
    emag_advanced,
    emag_campaigns,
    emag_customers,
    emag_db_offers,
    emag_ean_matching,
    emag_integration,
    emag_inventory,
    emag_management,
    emag_offers,
    emag_orders,
    emag_phase2,
    emag_price_update,
    emag_pricing_intelligence,
    emag_product_copy,
    emag_product_publishing,
    emag_product_sync,
    emag_sync,
    inventory_management,
    invoices,
    low_stock_suppliers,
    migration_management,
    notifications,
    orders,
    payment_gateways,
    performance_metrics,
    product_chinese_name,
    product_import,
    # invoice_names,  # File does not exist
    product_management,
    product_relationships,
    product_republish,
    product_update,
    product_variants_local,
    products_v1,
    purchase_orders,
    reporting,
    rma,
    session_management,
    sms_notifications,
    stock_sync,
    supplier_matching,
    supplier_migration,
    suppliers,
    test_auth,
    vat,
    websocket_notifications,
    websocket_sync,
)
from app.api.v1.endpoints.suppliers import (
    promote_sheet_router,
    set_sheet_supplier_router,
    supplier_sheet_sync,
)
from app.api.v1.endpoints.debug import router as debug_router

# Import new modular core endpoints
from app.api.v1.endpoints.emag import (
    core_cache_router,
    core_orders_router,
    core_products_router,
    core_sync_router,
)
from app.api.v1.endpoints.inventory import emag_inventory_sync_router
from app.api.v1.endpoints.suppliers import supplier_sheet_sync

from ..auth import router as auth_router
from ..routes.catalog import router as catalog_router
from ..tasks import router as tasks_router
from .endpoints.system.auth import users_router as auth_users_router

api_router = APIRouter()

# Health endpoints mounted at /health so tests can call /api/v1/health/
api_router.include_router(complex_health.router, prefix="/health")

# Products endpoints (legacy) - DISABLED in favor of product_management
# Product import endpoints must be mounted before the general products router
# to ensure specific routes like /products/mappings are not shadowed by
# parameterized routes in the generic products router.
api_router.include_router(product_import, prefix="/products", tags=["product-import"])
# api_router.include_router(products.router, tags=["products"])  # Disabled - using
# product_management instead

# Enhanced Products endpoints (v4.4.9) - mounted without additional prefix
# since router already has /products-v1
api_router.include_router(products_v1)

# Categories endpoints
api_router.include_router(categories.router, tags=["categories"])

# Auth endpoints mounted at /auth and user info at /users
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(auth_users_router, prefix="/users", tags=["users"])

# eMAG Product Synchronization endpoints (NEW - must be registered BEFORE
# emag_integration to avoid route conflicts)
api_router.include_router(
    emag_product_sync, prefix="/emag/products", tags=["emag-product-sync"]
)

# eMAG Product Copy endpoints (NEW - copy products from MAIN to FBE)
api_router.include_router(emag_product_copy, tags=["emag-product-copy"])

# eMAG marketplace integration endpoints
api_router.include_router(emag_integration, tags=["emag"])

# NEW: eMAG Core Modular Endpoints (v2 - refactored)
api_router.include_router(core_products_router, prefix="/emag", tags=["emag-core"])
api_router.include_router(core_orders_router, prefix="/emag", tags=["emag-core"])
api_router.include_router(core_sync_router, prefix="/emag", tags=["emag-core"])
api_router.include_router(core_cache_router, prefix="/emag", tags=["emag-core"])

# Orders endpoints
api_router.include_router(orders, prefix="/orders", tags=["orders"])

# Admin dashboard endpoints
api_router.include_router(admin)

# Test authentication endpoints
api_router.include_router(test_auth, prefix="/test-auth", tags=["test-auth"])

# eMAG offers management endpoints
api_router.include_router(emag_offers, prefix="/offers", tags=["emag-offers"])

# VAT endpoints
api_router.include_router(vat, tags=["vat"])

# eMAG DB browse endpoints (read-only, local database)
api_router.include_router(emag_db_offers, prefix="/emag/db", tags=["emag-db"])

# eMAG sync endpoints
api_router.include_router(emag_sync, prefix="/emag/sync", tags=["emag-sync"])

# eMAG Orders Management endpoints (v4.4.9)
api_router.include_router(emag_orders, prefix="/emag/orders", tags=["emag-orders"])

# eMAG Phase 2 endpoints (AWB, EAN, Invoices)
api_router.include_router(emag_phase2, prefix="/emag/phase2", tags=["emag-phase2"])

# Advanced eMAG API v4.4.9 endpoints (Light Offer API, EAN matching, measurements)
api_router.include_router(emag_advanced, tags=["emag-advanced"])

# Payment gateways endpoints
api_router.include_router(
    payment_gateways,
    prefix="/payments",
    tags=["payments"],
)

# SMS notifications endpoints
api_router.include_router(sms_notifications, prefix="/sms", tags=["sms"])

# RMA (Returns Management) endpoints
api_router.include_router(rma, prefix="/rma", tags=["rma"])

# Cancellation endpoints
api_router.include_router(
    cancellations,
    prefix="/cancellations",
    tags=["cancellations"],
)

# Invoice management endpoints
api_router.include_router(invoices, prefix="/invoices", tags=["invoices"])

# Reporting endpoints
api_router.include_router(reporting, prefix="/reports", tags=["reports"])

# Catalog endpoints
api_router.include_router(catalog_router, tags=["catalog"])

# Tasks endpoints for Celery integration
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])

# Database management endpoints
api_router.include_router(database, prefix="/database", tags=["database"])

# Supplier migration endpoints
api_router.include_router(
    supplier_migration, prefix="/supplier-migration", tags=["supplier-migration"]
)

# Product chinese name update endpoints
api_router.include_router(
    product_chinese_name, prefix="/products/chinese-name", tags=["products"]
)

# eMAG Customers endpoints
api_router.include_router(emag_customers, prefix="/admin", tags=["emag-customers"])

# WebSocket endpoints for real-time sync progress
api_router.include_router(websocket_sync, prefix="/emag/enhanced", tags=["websocket"])

# WebSocket notifications for real-time order updates
api_router.include_router(websocket_notifications, tags=["websocket-notifications"])

# eMAG Management endpoints (monitoring, backup, health)
api_router.include_router(
    emag_management, prefix="/emag/management", tags=["emag-management"]
)

# eMAG Addresses endpoints (NEW in v4.4.9 - pickup/return addresses for AWB)
api_router.include_router(emag_addresses, tags=["emag-addresses"])

# eMAG Pricing Intelligence endpoints (NEW in v4.4.9 - commission, Smart Deals, EAN search)
api_router.include_router(
    emag_pricing_intelligence, prefix="/emag/pricing", tags=["emag-pricing"]
)

# eMAG Price Update endpoints (NEW - update product prices on FBE account)
api_router.include_router(emag_price_update, tags=["emag-price-update"])

# eMAG Campaign Management endpoints (NEW - campaign proposals, MultiDeals)
api_router.include_router(
    emag_campaigns, prefix="/emag/campaigns", tags=["emag-campaigns"]
)

# eMAG Product Publishing endpoints (NEW - draft/complete products, offer attachment, categories)
api_router.include_router(
    emag_product_publishing, prefix="/emag/publishing", tags=["emag-publishing"]
)

# eMAG EAN Matching endpoints (NEW - EAN validation and search)
api_router.include_router(emag_ean_matching, tags=["emag-ean-matching"])

# Suppliers endpoints (supplier management)
api_router.include_router(suppliers, tags=["suppliers"])

# Supplier Sheet Synchronization endpoints (NEW - sync verification between
# SupplierProduct and ProductSupplierSheet)
api_router.include_router(supplier_sheet_sync.router, tags=["supplier-sync"])

# Supplier Product Matching endpoints (NEW - 1688.com product matching and price comparison)
api_router.include_router(
    supplier_matching, prefix="/suppliers/matching", tags=["supplier-matching"]
)

# Google Sheets Product Management (NEW - promote and manage Google Sheets products)
api_router.include_router(
    promote_sheet_router, prefix="/suppliers", tags=["supplier-sheets"]
)
api_router.include_router(
    set_sheet_supplier_router, prefix="/suppliers", tags=["supplier-sheets"]
)

# Product Relationships endpoints (NEW - variant tracking, PNK consistency, competition monitoring)
api_router.include_router(product_relationships, tags=["product-relationships"])

# Stock Synchronization endpoints (NEW - intelligent stock management across MAIN/FBE)
api_router.include_router(stock_sync, tags=["stock-sync"])

# Product Republishing endpoints (NEW - handle competitor attachment scenarios)
api_router.include_router(product_republish, tags=["product-republish"])

# Product Variants Local endpoints (NEW - create variants before eMAG publish)
api_router.include_router(product_variants_local, tags=["product-variants-local"])

# Invoice Names endpoints (NEW - manage product names for invoices RO/EN)
# api_router.include_router(
#     invoice_names.router, tags=["invoice-names"]
# )  # File does not exist

# Product Management endpoints (NEW - comprehensive editing with history tracking)
api_router.include_router(product_management, tags=["product-management"])

# Inventory Management endpoints (NEW - low stock alerts, Excel export for supplier orders)
api_router.include_router(inventory_management, tags=["inventory-management"])

# eMAG Inventory Management (NEW - direct integration with emag_products_v2)
api_router.include_router(emag_inventory, tags=["emag-inventory"])

# Low Stock with Suppliers (NEW - low stock products with supplier selection and export)
api_router.include_router(low_stock_suppliers, tags=["low-stock-suppliers"])

# eMag Inventory Sync (NEW - sync eMag FBE stock to inventory_items)
api_router.include_router(
    emag_inventory_sync_router, prefix="/inventory", tags=["emag-inventory-sync"]
)

# Product Import endpoints (Google Sheets integration - legacy mapping)
# Product Update endpoints (NEW - simplified Google Sheets import without eMAG mapping)
api_router.include_router(
    product_update, prefix="/products/update", tags=["product-update"]
)

# Notifications endpoints (NEW - user notifications and settings)
api_router.include_router(notifications, tags=["notifications"])

# Migration Management endpoints (NEW - migration health monitoring and consolidation)
api_router.include_router(
    migration_management, prefix="/migrations", tags=["migrations"]
)

# Session Management endpoints (NEW - user session tracking and monitoring)
api_router.include_router(session_management, prefix="/sessions", tags=["sessions"])

# Performance Metrics endpoints (NEW - application performance monitoring)
api_router.include_router(
    performance_metrics, prefix="/performance", tags=["performance"]
)

# Purchase Orders endpoints (NEW - centralized purchase order management and tracking)
api_router.include_router(purchase_orders, tags=["purchase-orders"])

# Debug endpoints (NEW - troubleshooting and diagnostics)
api_router.include_router(debug_router, tags=["debug"])
