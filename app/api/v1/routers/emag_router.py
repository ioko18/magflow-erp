"""eMAG Integration Router.

Consolidates all eMAG marketplace integration endpoints into a single router.
This includes product sync, orders, offers, campaigns, and other eMAG-specific functionality.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    emag_addresses,
    emag_advanced,
    emag_campaigns,
    emag_customers,
    emag_db_offers,
    emag_ean_matching,
    emag_integration,
    emag_management,
    emag_offers,
    emag_orders,
    emag_phase2,
    emag_pricing_intelligence,
    emag_product_copy,
    emag_product_publishing,
    emag_product_sync,
    emag_sync,
    emag_v449,
    enhanced_emag_sync,
    websocket_sync,
)

# Import new modular core endpoints
from app.api.v1.endpoints.emag import (
    core_cache_router,
    core_orders_router,
    core_products_router,
    core_sync_router,
)

router = APIRouter(prefix="/emag", tags=["emag"])

# Core eMAG marketplace integration endpoints
router.include_router(emag_integration, tags=["emag-integration"])

# NEW: eMAG Core Modular Endpoints (v2 - refactored)
router.include_router(core_products_router, tags=["emag-core"])
router.include_router(core_orders_router, tags=["emag-core"])
router.include_router(core_sync_router, tags=["emag-core"])
router.include_router(core_cache_router, tags=["emag-core"])

# eMAG Product Synchronization endpoints (must be registered BEFORE
# emag_integration to avoid route conflicts)
router.include_router(emag_product_sync, prefix="/products", tags=["emag-product-sync"])

# eMAG Product Copy endpoints (copy products from MAIN to FBE)
router.include_router(emag_product_copy, tags=["emag-product-copy"])

# eMAG sync endpoints
router.include_router(emag_sync, prefix="/sync", tags=["emag-sync"])

# Enhanced eMAG sync endpoints (v4.4.8)
router.include_router(enhanced_emag_sync, prefix="/enhanced", tags=["emag-enhanced"])

# eMAG Orders Management endpoints (v4.4.9)
router.include_router(emag_orders, prefix="/orders", tags=["emag-orders"])

# eMAG Phase 2 endpoints (AWB, EAN, Invoices)
router.include_router(emag_phase2, prefix="/phase2", tags=["emag-phase2"])

# Advanced eMAG API v4.4.9 endpoints (Light Offer API, EAN matching, measurements)
router.include_router(emag_advanced, tags=["emag-advanced"])

# eMAG Management endpoints (monitoring, backup, health)
router.include_router(emag_management, prefix="/management", tags=["emag-management"])

# eMAG Addresses endpoints (pickup/return addresses for AWB)
router.include_router(emag_addresses, tags=["emag-addresses"])

# eMAG Pricing Intelligence endpoints (commission, Smart Deals, EAN search)
router.include_router(
    emag_pricing_intelligence, prefix="/pricing", tags=["emag-pricing"]
)

# eMAG Campaign Management endpoints (campaign proposals, MultiDeals)
router.include_router(emag_campaigns, prefix="/campaigns", tags=["emag-campaigns"])

# eMAG API v4.4.9 endpoints (EAN Search, Light Offer API, Measurements)
router.include_router(emag_v449, tags=["emag-v449"])

# eMAG Product Publishing endpoints (draft/complete products, offer attachment, categories)
router.include_router(
    emag_product_publishing, prefix="/publishing", tags=["emag-publishing"]
)

# eMAG EAN Matching endpoints (EAN validation and search)
router.include_router(emag_ean_matching, tags=["emag-ean-matching"])

# eMAG DB browse endpoints (read-only, local database)
router.include_router(emag_db_offers, prefix="/db", tags=["emag-db"])

# eMAG offers management endpoints
router.include_router(emag_offers, prefix="/offers", tags=["emag-offers"])

# eMAG Customers endpoints
router.include_router(emag_customers, prefix="/customers", tags=["emag-customers"])

# WebSocket endpoints for real-time sync progress
router.include_router(websocket_sync, prefix="/ws", tags=["emag-websocket"])
