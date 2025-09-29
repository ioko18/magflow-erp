"""API v1 aggregator router.

Exposes `api_router` and includes versioned endpoint routers.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api import categories
from app.api import health as complex_health
from app.api import products
from app.api import test_sync

from ..auth import router as auth_router
from .endpoints.auth import users_router as auth_users_router
from ..routes.catalog import router as catalog_router
from ..tasks import router as tasks_router
from .endpoints import (
    admin,
    cancellations,
    database,
    emag_db_offers,
    emag_integration,
    emag_offers,
    emag_sync,
    enhanced_emag_sync,
    invoices,
    orders,
    payment_gateways,
    reporting,
    rma,
    sms_notifications,
    test_auth,
    vat,
)

api_router = APIRouter()

# Health endpoints mounted at /health so tests can call /api/v1/health/
api_router.include_router(complex_health.router, prefix="/health")

# Products endpoints
api_router.include_router(products.router, tags=["products"])

# Categories endpoints
api_router.include_router(categories.router, tags=["categories"])

# Auth endpoints mounted at /auth and user info at /users
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(auth_users_router, prefix="/users", tags=["users"])

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
api_router.include_router(enhanced_emag_sync.router, prefix="/emag/enhanced", tags=["emag-enhanced"])

# Test sync endpoints (without auth for development)
api_router.include_router(test_sync.router, prefix="/test/sync", tags=["test-sync"])

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
