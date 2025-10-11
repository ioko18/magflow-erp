"""API v1 aggregator router - REFACTORED VERSION.

This is a cleaner, more maintainable version of the API router that uses
thematic sub-routers for better organization.

To use this version, update app/main.py to import from this file instead of api.py:
    from app.api.v1.api_refactored import api_router as v1_router
"""

from fastapi import APIRouter

from app.api import categories
from app.api import health as complex_health
from app.api.auth import router as auth_router
from app.api.routes.catalog import router as catalog_router
from app.api.tasks import router as tasks_router
from app.api.v1.endpoints import (
    database,
    migration_management,
    notifications,
    performance_metrics,
    session_management,
    test_auth,
    websocket_notifications,
)
from app.api.v1.endpoints.system.auth import users_router as auth_users_router

# Import thematic routers
from app.api.v1.routers import (
    emag_router,
    orders_router,
    products_router,
    suppliers_router,
)

api_router = APIRouter()

# ============================================================================
# CORE SYSTEM ENDPOINTS
# ============================================================================

# Health endpoints mounted at /health so tests can call /api/v1/health/
api_router.include_router(complex_health.router, prefix="/health", tags=["health"])

# Auth endpoints mounted at /auth and user info at /users
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(auth_users_router, prefix="/users", tags=["users"])

# Test authentication endpoints
api_router.include_router(test_auth, prefix="/test-auth", tags=["test-auth"])

# Categories endpoints
api_router.include_router(categories.router, tags=["categories"])

# Catalog endpoints
api_router.include_router(catalog_router, tags=["catalog"])

# Tasks endpoints for Celery integration
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])

# Database management endpoints
api_router.include_router(database, prefix="/database", tags=["database"])

# Notifications endpoints (user notifications and settings)
api_router.include_router(notifications, tags=["notifications"])

# Migration Management endpoints (migration health monitoring and consolidation)
api_router.include_router(
    migration_management, prefix="/migrations", tags=["migrations"]
)

# Session Management endpoints (user session tracking and monitoring)
api_router.include_router(session_management, prefix="/sessions", tags=["sessions"])

# Performance Metrics endpoints (application performance monitoring)
api_router.include_router(
    performance_metrics, prefix="/performance", tags=["performance"]
)

# WebSocket notifications for real-time order updates
api_router.include_router(websocket_notifications, tags=["websocket-notifications"])

# ============================================================================
# THEMATIC ROUTERS (Organized by domain)
# ============================================================================

# eMAG Integration - All eMAG marketplace endpoints
api_router.include_router(emag_router)

# Products Management - All product-related endpoints
api_router.include_router(products_router)

# Orders Management - All order-related endpoints
api_router.include_router(orders_router)

# Suppliers Management - All supplier-related endpoints
api_router.include_router(suppliers_router)
