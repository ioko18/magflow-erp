"""API v1 aggregator router.

Exposes `api_router` and includes versioned endpoint routers.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api import health as complex_health

from ..auth import router as auth_router
from ..routes.catalog import router as catalog_router
from ..tasks import router as tasks_router
from .endpoints import (
    cancellations,
    database,
    emag_db_offers,
    emag_integration,
    emag_offers,
    emag_sync,
    invoices,
    payment_gateways,
    reporting,
    rma,
    sms_notifications,
)

api_router = APIRouter()

# Health endpoints mounted at /health so tests can call /api/v1/health/
api_router.include_router(complex_health.router, prefix="/health")

# Auth endpoints mounted at /auth
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])

# eMAG marketplace integration endpoints
api_router.include_router(emag_integration.router, tags=["emag"])

# eMAG offers management endpoints
api_router.include_router(emag_offers.router, prefix="/offers", tags=["emag-offers"])

# eMAG DB browse endpoints (read-only, local database)
api_router.include_router(emag_db_offers.router, prefix="/emag/db", tags=["emag-db"])

# eMAG sync endpoints
api_router.include_router(emag_sync.router, prefix="/sync", tags=["emag-sync"])

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
