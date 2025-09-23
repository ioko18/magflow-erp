"""Admin dashboard API endpoints."""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db

from ...deps import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard_data(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get dashboard metrics and data."""
    try:
        # Get eMAG sync statistics
        emag_result = await db.execute(
            text(
                """
            SELECT
                COUNT(*) as total_products,
                COUNT(*) FILTER (WHERE ep.updated_at > NOW() - INTERVAL '24 hours') as recent_updates
            FROM app.emag_products ep
        """,
            ),
        )
        emag_data = emag_result.fetchone()

        # Get recent sync status
        sync_result = await db.execute(
            text(
                """
            SELECT sync_id, status, total_offers_processed,
                   started_at, completed_at,
                   EXTRACT(EPOCH FROM (completed_at - started_at)) as duration_seconds
            FROM app.emag_offer_syncs
            ORDER BY created_at DESC
            LIMIT 5
        """,
            ),
        )
        syncs = sync_result.fetchall()

        # Mock data for development
        return {
            "status": "success",
            "data": {
                "totalSales": 45670.89,
                "totalOrders": 234,
                "totalCustomers": 89,
                "emagProducts": emag_data.total_products if emag_data else 0,
                "inventoryValue": 123400.50,
                "syncStatus": "success",
                "recentOrders": [
                    {
                        "id": 1,
                        "customer": "John Doe",
                        "amount": 299.99,
                        "status": "completed",
                        "date": "2024-01-15",
                    },
                    {
                        "id": 2,
                        "customer": "Jane Smith",
                        "amount": 149.50,
                        "status": "processing",
                        "date": "2024-01-15",
                    },
                    {
                        "id": 3,
                        "customer": "Bob Johnson",
                        "amount": 79.99,
                        "status": "shipped",
                        "date": "2024-01-14",
                    },
                ],
                "salesData": [
                    {"name": "Jan", "sales": 4000, "orders": 24},
                    {"name": "Feb", "sales": 3000, "orders": 18},
                    {"name": "Mar", "sales": 2000, "orders": 12},
                    {"name": "Apr", "sales": 2780, "orders": 15},
                    {"name": "May", "sales": 1890, "orders": 11},
                    {"name": "Jun", "sales": 2390, "orders": 16},
                ],
                "topProducts": [
                    {"name": "iPhone 15", "value": 35, "sales": 15420},
                    {"name": "MacBook Pro", "value": 25, "sales": 28900},
                    {"name": "iPad Air", "value": 20, "sales": 8750},
                    {"name": "AirPods Pro", "value": 20, "sales": 3240},
                ],
                "recentSyncs": [
                    {
                        "sync_id": sync.sync_id,
                        "status": sync.status,
                        "offers_processed": sync.total_offers_processed,
                        "started_at": (
                            sync.started_at.isoformat() if sync.started_at else None
                        ),
                        "completed_at": (
                            sync.completed_at.isoformat() if sync.completed_at else None
                        ),
                        "duration_seconds": sync.duration_seconds,
                    }
                    for sync in syncs
                ],
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-emag", response_model=Dict[str, Any])
async def sync_emag_offers(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Trigger eMAG synchronization."""
    try:
        # Import and run the sync function
        from app.emag.sync_emag import sync_emag_offers

        result = await sync_emag_offers()

        return {
            "status": "success" if result["status"] == "success" else "error",
            "message": result.get("message", "Sync completed"),
            "data": result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system-status", response_model=Dict[str, Any])
async def get_system_status(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get system health and status information."""
    try:
        # Check database connectivity
        db_result = await db.execute(text("SELECT 1"))
        db_status = "healthy" if db_result.scalar() == 1 else "unhealthy"

        # Get system metrics
        metrics_result = await db.execute(
            text(
                """
            SELECT
                (SELECT COUNT(*) FROM app.emag_products) as emag_products,
                (SELECT COUNT(*) FROM app.emag_product_offers) as emag_offers,
                (SELECT COUNT(*) FROM app.emag_offer_syncs WHERE status = 'completed') as successful_syncs,
                (SELECT COUNT(*) FROM app.emag_offer_syncs WHERE status = 'failed') as failed_syncs
        """,
            ),
        )
        metrics = metrics_result.fetchone()

        return {
            "status": "success",
            "data": {
                "database": {"status": db_status, "connection": "active"},
                "emag_integration": {
                    "status": "active",
                    "products_synced": metrics.emag_products or 0,
                    "offers_synced": metrics.emag_offers or 0,
                    "successful_syncs": metrics.successful_syncs or 0,
                    "failed_syncs": metrics.failed_syncs or 0,
                },
                "system": {
                    "uptime": "System uptime information",
                    "memory_usage": "Memory usage data",
                    "cpu_usage": "CPU usage data",
                },
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
