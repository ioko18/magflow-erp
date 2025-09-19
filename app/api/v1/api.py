"""API v1 aggregator router.

Exposes `api_router` and includes versioned endpoint routers.
"""
from __future__ import annotations

from fastapi import APIRouter

from .endpoints import health as health_endpoints

api_router = APIRouter()

# Health endpoints mounted at /health so tests can call /api/v1/health/...
api_router.include_router(health_endpoints.router, prefix="/health")
