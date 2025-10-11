"""eMAG synchronization endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db import get_db

router = APIRouter()


@router.post("/sync", response_model=dict[str, Any])
async def sync_emag_offers(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Synchronize eMAG offers to database."""
    try:
        # Import the sync function
        from app.emag.services.offer_sync_service import OfferSyncService

        # Run sync using the service
        service = OfferSyncService(per_page=100)
        await service.sync_all_offers()

        return {
            "status": "success",
            "message": "eMAG synchronization completed",
            "data": {"sync_id": service.sync_id, "started_at": service.started_at},
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=dict[str, Any])
async def get_emag_sync_status(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get eMAG synchronization status."""
    try:
        # Get latest sync status
        result = await db.execute(
            text(
                """
            SELECT sync_id, status, total_offers_processed,
                   started_at, completed_at, duration_seconds
            FROM app.emag_offer_syncs
            ORDER BY created_at DESC
            LIMIT 5
        """,
            ),
        )

        syncs = result.fetchall()

        # Get product counts
        products_result = await db.execute(
            text("SELECT COUNT(*) FROM app.emag_products"),
        )
        products_count = products_result.scalar()

        offers_result = await db.execute(
            text("SELECT COUNT(*) FROM app.emag_product_offers"),
        )
        offers_count = offers_result.scalar()

        return {
            "status": "success",
            "data": {
                "total_products": products_count,
                "total_offers": offers_count,
                "recent_syncs": [
                    {
                        "sync_id": sync.sync_id,
                        "status": sync.status,
                        "offers_processed": sync.total_offers_processed,
                        "started_at": sync.started_at,
                        "completed_at": sync.completed_at,
                        "duration_seconds": sync.duration_seconds,
                    }
                    for sync in syncs
                ],
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products", response_model=dict[str, Any])
async def get_emag_products(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get eMAG products from database."""
    try:
        # Get products
        result = await db.execute(
            text(
                """
            SELECT id, emag_id, name, part_number, is_active, created_at, updated_at
            FROM app.emag_products
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :skip
        """,
            ),
            {"limit": limit, "skip": skip},
        )

        products = result.fetchall()

        return {
            "status": "success",
            "data": {
                "products": [
                    {
                        "id": product.id,
                        "emag_id": product.emag_id,
                        "name": product.name,
                        "part_number": product.part_number,
                        "is_active": product.is_active,
                        "created_at": product.created_at,
                        "updated_at": product.updated_at,
                    }
                    for product in products
                ],
                "pagination": {"skip": skip, "limit": limit},
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progress", response_model=dict[str, Any])
async def get_emag_sync_progress(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get current eMAG synchronization progress."""
    try:
        # Get currently running sync
        result = await db.execute(
            text(
                """
            SELECT sync_id, account_type, status, total_offers_processed,
                   started_at, completed_at, duration_seconds, error_count, errors
            FROM app.emag_offer_syncs
            WHERE status IN ('running', 'pending')
            ORDER BY started_at DESC
            LIMIT 1
        """,
            ),
        )

        current_sync = result.fetchone()

        if current_sync:
            # Calculate progress percentage if we have total expected offers
            # For now, we'll estimate based on the pattern from the frontend
            progress_data = {
                "sync_id": current_sync.sync_id,
                "account_type": current_sync.account_type,
                "status": current_sync.status,
                "total_offers_processed": current_sync.total_offers_processed,
                "started_at": current_sync.started_at,
                "completed_at": current_sync.completed_at,
                "duration_seconds": current_sync.duration_seconds,
                "error_count": current_sync.error_count,
                "errors": current_sync.errors,
                "is_running": current_sync.status == "running",
                "current_page": None,  # Would be populated by sync script
                "total_pages": None,  # Would be populated by sync script
                "estimated_time_remaining": None,  # Would be calculated based on progress
            }
        else:
            # No active sync, return no_data status like frontend expects
            progress_data = {
                "status": "no_data",
                "detail": "No active synchronization in progress",
                "is_running": False,
            }

        # Return progress data directly (not wrapped in "data" field)
        return progress_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_emag_sync_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get synchronization history."""
    try:
        # Get recent sync history
        result = await db.execute(
            text(
                """
            SELECT sync_id, account_type, status, total_offers_processed,
                   started_at, completed_at, duration_seconds, error_count, errors
            FROM app.emag_offer_syncs
            ORDER BY started_at DESC
            LIMIT :limit
        """,
            ),
            {"limit": limit},
        )

        syncs = result.fetchall()

        sync_records = [
            {
                "sync_id": sync.sync_id,
                "account_type": sync.account_type,
                "status": sync.status,
                "total_offers_processed": sync.total_offers_processed,
                "started_at": sync.started_at,
                "completed_at": sync.completed_at,
                "duration_seconds": sync.duration_seconds,
                "error_count": sync.error_count,
                "errors": sync.errors,
            }
            for sync in syncs
        ]

        return {
            "sync_records": sync_records,
            "total_count": len(sync_records),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
