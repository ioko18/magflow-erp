"""API v1 aggregator router.

Exposes `api_router` and includes versioned endpoint routers.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api import categories
from app.api import health as complex_health

from ..auth import router as auth_router
from .endpoints.auth import users_router as auth_users_router
from ..routes.catalog import router as catalog_router
from ..tasks import router as tasks_router
from app.api.v1.endpoints import (
    admin,
    emag_integration,
    emag_sync,
    emag_offers,
    enhanced_emag_sync,
    emag_orders,
    emag_customers,
    emag_advanced,
    emag_management,
    emag_phase2,
    emag_addresses,
    emag_pricing_intelligence,
    emag_campaigns,
    emag_v449,
    emag_product_publishing,
    emag_product_sync,
    emag_ean_matching,
    websocket_sync,
    websocket_notifications,
    test_auth,
    orders,
    vat,
    emag_db_offers,
    payment_gateways,
    sms_notifications,
    rma,
    cancellations,
    invoices,
    reporting,
    database,
    products as products_v1,
    supplier_matching,
    suppliers,
    product_import,
    product_relationships,
    stock_sync,
    product_republish,
    product_variants_local,
    invoice_names,
    product_management,
    inventory_management,
    emag_inventory,
)

api_router = APIRouter()

# Health endpoints mounted at /health so tests can call /api/v1/health/
api_router.include_router(complex_health.router, prefix="/health")

# Products endpoints (legacy) - DISABLED in favor of product_management
# Product import endpoints must be mounted before the general products router
# to ensure specific routes like /products/mappings are not shadowed by
# parameterized routes in the generic products router.
api_router.include_router(product_import.router, prefix="/products", tags=["product-import"])
# api_router.include_router(products.router, tags=["products"])  # Disabled - using product_management instead

# Enhanced Products endpoints (v4.4.9) - mounted without additional prefix since router already has /products-v1
api_router.include_router(products_v1.router)

# Categories endpoints
api_router.include_router(categories.router, tags=["categories"])

# Auth endpoints mounted at /auth and user info at /users
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(auth_users_router, prefix="/users", tags=["users"])

# eMAG Product Synchronization endpoints (NEW - must be registered BEFORE emag_integration to avoid route conflicts)
api_router.include_router(
    emag_product_sync.router, prefix="/emag/products", tags=["emag-product-sync"]
)

# eMAG marketplace integration endpoints
api_router.include_router(emag_integration.router, tags=["emag"])

# Orders endpoints
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])

# Admin dashboard endpoints
api_router.include_router(admin.router)

# Test authentication endpoints
api_router.include_router(test_auth.router, prefix="/test-auth", tags=["test-auth"])

# eMAG offers management endpoints
api_router.include_router(emag_offers.router, prefix="/offers", tags=["emag-offers"])

# VAT endpoints
api_router.include_router(vat.router, tags=["vat"])

# eMAG DB browse endpoints (read-only, local database)
api_router.include_router(emag_db_offers.router, prefix="/emag/db", tags=["emag-db"])

# eMAG sync endpoints
api_router.include_router(emag_sync.router, prefix="/emag/sync", tags=["emag-sync"])

# Enhanced eMAG sync endpoints (v4.4.8)
api_router.include_router(
    enhanced_emag_sync.router, prefix="/emag/enhanced", tags=["emag-enhanced"]
)

# eMAG Orders Management endpoints (v4.4.9)
api_router.include_router(
    emag_orders.router, prefix="/emag/orders", tags=["emag-orders"]
)

# eMAG Phase 2 endpoints (AWB, EAN, Invoices)
api_router.include_router(
    emag_phase2.router, prefix="/emag/phase2", tags=["emag-phase2"]
)

# Advanced eMAG API v4.4.9 endpoints (Light Offer API, EAN matching, measurements)
api_router.include_router(
    emag_advanced.router, tags=["emag-advanced"]
)

# Payment gateways endpoints
api_router.include_router(
    payment_gateways.router,
    prefix="/payments",
    tags=["payments"],
)

# SMS notifications endpoints
api_router.include_router(sms_notifications.router, prefix="/sms", tags=["sms"])

# RMA (Returns Management) endpoints
api_router.include_router(rma.router, prefix="/rma", tags=["rma"])

# Cancellation endpoints
api_router.include_router(
    cancellations.router,
    prefix="/cancellations",
    tags=["cancellations"],
)

# Invoice management endpoints
api_router.include_router(invoices.router, prefix="/invoices", tags=["invoices"])

# Reporting endpoints
api_router.include_router(reporting.router, prefix="/reports", tags=["reports"])

# Catalog endpoints
api_router.include_router(catalog_router, tags=["catalog"])

# Tasks endpoints for Celery integration
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])

# Database management endpoints
api_router.include_router(database.router, prefix="/database", tags=["database"])

# eMAG Customers endpoints
api_router.include_router(emag_customers.router, prefix="/admin", tags=["emag-customers"])

# WebSocket endpoints for real-time sync progress
api_router.include_router(websocket_sync.router, prefix="/emag/enhanced", tags=["websocket"])

# WebSocket notifications for real-time order updates
api_router.include_router(websocket_notifications.router, tags=["websocket-notifications"])

# eMAG Management endpoints (monitoring, backup, health)
api_router.include_router(emag_management.router, prefix="/emag/management", tags=["emag-management"])

# eMAG Addresses endpoints (NEW in v4.4.9 - pickup/return addresses for AWB)
api_router.include_router(emag_addresses.router, tags=["emag-addresses"])

# eMAG Pricing Intelligence endpoints (NEW in v4.4.9 - commission, Smart Deals, EAN search)
api_router.include_router(
    emag_pricing_intelligence.router, prefix="/emag/pricing", tags=["emag-pricing"]
)

# eMAG Campaign Management endpoints (NEW - campaign proposals, MultiDeals)
api_router.include_router(
    emag_campaigns.router, prefix="/emag/campaigns", tags=["emag-campaigns"]
)

# eMAG API v4.4.9 endpoints (EAN Search, Light Offer API, Measurements)
api_router.include_router(
    emag_v449.router, tags=["emag-v449"]
)

# eMAG Product Publishing endpoints (NEW - draft/complete products, offer attachment, categories)
api_router.include_router(
    emag_product_publishing.router, prefix="/emag/publishing", tags=["emag-publishing"]
)

# eMAG EAN Matching endpoints (NEW - EAN validation and search)
api_router.include_router(
    emag_ean_matching.router, tags=["emag-ean-matching"]
)

# Suppliers endpoints (supplier management)
api_router.include_router(
    suppliers.router, tags=["suppliers"]
)

# Supplier Product Matching endpoints (NEW - 1688.com product matching and price comparison)
api_router.include_router(
    supplier_matching.router, prefix="/suppliers/matching", tags=["supplier-matching"]
)

# Product Relationships endpoints (NEW - variant tracking, PNK consistency, competition monitoring)
api_router.include_router(
    product_relationships.router, tags=["product-relationships"]
)

# Stock Synchronization endpoints (NEW - intelligent stock management across MAIN/FBE)
api_router.include_router(
    stock_sync.router, tags=["stock-sync"]
)

# Product Republishing endpoints (NEW - handle competitor attachment scenarios)
api_router.include_router(
    product_republish.router, tags=["product-republish"]
)

# Product Variants Local endpoints (NEW - create variants before eMAG publish)
api_router.include_router(
    product_variants_local.router, tags=["product-variants-local"]
)

# Invoice Names endpoints (NEW - manage product names for invoices RO/EN)
api_router.include_router(
    invoice_names.router, tags=["invoice-names"]
)

# Product Management endpoints (NEW - comprehensive editing with history tracking)
api_router.include_router(
    product_management.router, tags=["product-management"]
)

# Inventory Management endpoints (NEW - low stock alerts, Excel export for supplier orders)
api_router.include_router(
    inventory_management.router, tags=["inventory-management"]
)

# eMAG Inventory Management (NEW - direct integration with emag_products_v2)
api_router.include_router(
    emag_inventory.router, tags=["emag-inventory"]
)

# Product Import endpoints (Google Sheets integration)
