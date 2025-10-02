"""
eMAG Product Synchronization API Endpoints.

This module provides REST API endpoints for managing eMAG product synchronization:
- Manual sync triggers (full, incremental, selective)
- Sync status and progress monitoring
- Sync history and statistics
- Configuration management
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.emag_product_sync_service import (
    EmagProductSyncService,
    ConflictResolutionStrategy,
    SyncMode,
)
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


# Request/Response Models

class SyncProductsRequest(BaseModel):
    """Request model for product synchronization."""
    
    account_type: str = Field(
        default="both",
        description="Account type to sync: 'main', 'fbe', or 'both'",
    )
    mode: str = Field(
        default=SyncMode.INCREMENTAL,
        description="Sync mode: 'full', 'incremental', or 'selective'",
    )
    max_pages: Optional[int] = Field(
        default=None,
        description="Maximum pages to fetch (None = all)",
        ge=1,
    )
    items_per_page: int = Field(
        default=100,
        description="Items per page",
        ge=1,
        le=100,
    )
    include_inactive: bool = Field(
        default=False,
        description="Include inactive products",
    )
    conflict_strategy: str = Field(
        default=ConflictResolutionStrategy.EMAG_PRIORITY,
        description="Conflict resolution strategy",
    )
    run_async: bool = Field(
        default=False,
        description="Run synchronization in background",
    )


class SyncProductsResponse(BaseModel):
    """Response model for product synchronization."""
    
    status: str
    message: str
    sync_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class SyncStatusResponse(BaseModel):
    """Response model for sync status."""
    
    is_running: bool
    current_sync: Optional[Dict[str, Any]] = None
    recent_syncs: List[Dict[str, Any]] = []


class SyncStatisticsResponse(BaseModel):
    """Response model for sync statistics."""
    
    products_by_account: Dict[str, int]
    total_products: int
    recent_syncs: List[Dict[str, Any]]


# API Endpoints

@router.post("/sync", response_model=SyncProductsResponse)
async def sync_products(
    request: SyncProductsRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SyncProductsResponse:
    """
    Trigger product synchronization from eMAG.
    
    This endpoint initiates product synchronization from eMAG marketplace
    to the local database. It supports both synchronous and asynchronous execution.
    
    **Sync Modes:**
    - `full`: Sync all products (slow but complete)
    - `incremental`: Sync only changed products (fast, recommended)
    - `selective`: Sync specific products (requires additional filters)
    
    **Conflict Strategies:**
    - `emag_priority`: eMAG data always wins (recommended)
    - `local_priority`: Local data always wins
    - `newest_wins`: Most recently modified wins
    - `manual`: Requires manual intervention
    
    **Examples:**
    ```json
    {
        "account_type": "both",
        "mode": "incremental",
        "max_pages": 10,
        "conflict_strategy": "emag_priority",
        "run_async": true
    }
    ```
    """
    logger.info(
        f"Product sync requested by user {current_user.email}: "
        f"account={request.account_type}, mode={request.mode}, "
        f"async={request.run_async}"
    )

    try:
        if request.run_async:
            # Run in background
            background_tasks.add_task(
                _run_sync_task,
                db=db,
                request=request,
            )
            
            return SyncProductsResponse(
                status="accepted",
                message="Product synchronization started in background",
                sync_id=None,
            )
        else:
            # Run synchronously
            async with EmagProductSyncService(
                db=db,
                account_type=request.account_type,
                conflict_strategy=request.conflict_strategy,
            ) as sync_service:
                result = await sync_service.sync_all_products(
                    mode=request.mode,
                    max_pages=request.max_pages,
                    items_per_page=request.items_per_page,
                    include_inactive=request.include_inactive,
                )
                
                # Commit the session manually
                await db.commit()
                
                return SyncProductsResponse(
                    status="completed",
                    message="Product synchronization completed successfully",
                    data=result,
                )

    except Exception as e:
        logger.error(f"Product sync failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Product synchronization failed: {str(e)}",
        )


async def _run_sync_task(db: AsyncSession, request: SyncProductsRequest):
    """Background task for running product sync."""
    from app.core.database import async_session_factory
    
    try:
        # Create new session for background task
        async with async_session_factory() as sync_db:
            async with EmagProductSyncService(
                db=sync_db,
                account_type=request.account_type,
                conflict_strategy=request.conflict_strategy,
            ) as sync_service:
                await sync_service.sync_all_products(
                    mode=request.mode,
                    max_pages=request.max_pages,
                    items_per_page=request.items_per_page,
                    include_inactive=request.include_inactive,
                )
    except Exception as e:
        logger.error(f"Background sync task failed: {e}", exc_info=True)


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SyncStatusResponse:
    """
    Get current synchronization status.
    
    Returns information about currently running synchronization
    and recent sync history.
    """
    try:
        from sqlalchemy import select, desc
        from app.models.emag_models import EmagSyncLog
        
        # Check for running sync
        stmt = (
            select(EmagSyncLog)
            .where(
                EmagSyncLog.sync_type == "products",
                EmagSyncLog.status == "running",
            )
            .order_by(desc(EmagSyncLog.started_at))
            .limit(1)
        )
        result = await db.execute(stmt)
        running_sync = result.scalar_one_or_none()
        
        # Get recent syncs
        stmt = (
            select(EmagSyncLog)
            .where(EmagSyncLog.sync_type == "products")
            .order_by(desc(EmagSyncLog.started_at))
            .limit(10)
        )
        result = await db.execute(stmt)
        recent_syncs = result.scalars().all()
        
        return SyncStatusResponse(
            is_running=running_sync is not None,
            current_sync={
                "id": str(running_sync.id),
                "account_type": running_sync.account_type,
                "operation": running_sync.operation,
                "started_at": running_sync.started_at.isoformat(),
                "total_items": running_sync.total_items,
                "processed_items": running_sync.processed_items,
            } if running_sync else None,
            recent_syncs=[
                {
                    "id": str(sync.id),
                    "account_type": sync.account_type,
                    "operation": sync.operation,
                    "status": sync.status,
                    "started_at": sync.started_at.isoformat(),
                    "completed_at": sync.completed_at.isoformat() if sync.completed_at else None,
                    "duration_seconds": sync.duration_seconds,
                    "total_items": sync.total_items,
                    "created_items": sync.created_items,
                    "updated_items": sync.updated_items,
                    "failed_items": sync.failed_items,
                }
                for sync in recent_syncs
            ],
        )
        
    except Exception as e:
        logger.error(f"Failed to get sync status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get sync status: {str(e)}",
        )


@router.get("/statistics", response_model=SyncStatisticsResponse)
async def get_sync_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SyncStatisticsResponse:
    """
    Get synchronization statistics.
    
    Returns detailed statistics about synchronized products
    including counts by account and recent sync history.
    """
    try:
        # Create service - no need to initialize API clients for stats
        async with EmagProductSyncService(db=db, account_type="both") as sync_service:
            stats = await sync_service.get_sync_statistics()
            return SyncStatisticsResponse(**stats)
            
    except Exception as e:
        logger.error(f"Failed to get sync statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get sync statistics: {str(e)}",
        )


@router.get("/history")
async def get_sync_history(
    limit: int = Query(default=50, ge=1, le=100),
    account_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get synchronization history with filtering.
    
    **Query Parameters:**
    - `limit`: Maximum number of records (1-100)
    - `account_type`: Filter by account type ('main', 'fbe')
    - `status`: Filter by status ('completed', 'failed', 'running')
    """
    try:
        from sqlalchemy import select, desc, and_
        from app.models.emag_models import EmagSyncLog
        
        # Build query
        conditions = [EmagSyncLog.sync_type == "products"]
        
        if account_type:
            conditions.append(EmagSyncLog.account_type == account_type)
        
        if status:
            conditions.append(EmagSyncLog.status == status)
        
        stmt = (
            select(EmagSyncLog)
            .where(and_(*conditions))
            .order_by(desc(EmagSyncLog.started_at))
            .limit(limit)
        )
        
        result = await db.execute(stmt)
        syncs = result.scalars().all()
        
        return {
            "status": "success",
            "data": {
                "syncs": [
                    {
                        "id": str(sync.id),
                        "account_type": sync.account_type,
                        "operation": sync.operation,
                        "status": sync.status,
                        "started_at": sync.started_at.isoformat(),
                        "completed_at": sync.completed_at.isoformat() if sync.completed_at else None,
                        "duration_seconds": sync.duration_seconds,
                        "total_items": sync.total_items,
                        "processed_items": sync.processed_items,
                        "created_items": sync.created_items,
                        "updated_items": sync.updated_items,
                        "failed_items": sync.failed_items,
                        "errors": sync.errors,
                    }
                    for sync in syncs
                ],
                "count": len(syncs),
            },
        }
        
    except Exception as e:
        logger.error(f"Failed to get sync history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get sync history: {str(e)}",
        )


@router.get("/products")
async def get_synced_products(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    account_type: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get synchronized products from local database.
    
    **Query Parameters:**
    - `skip`: Number of records to skip (pagination)
    - `limit`: Maximum number of records (1-100)
    - `account_type`: Filter by account type ('main', 'fbe')
    - `search`: Search in SKU or name
    """
    try:
        from sqlalchemy import select, or_, func
        from app.models.emag_models import EmagProductV2
        
        # Build query
        conditions = []
        
        if account_type:
            conditions.append(EmagProductV2.account_type == account_type)
        
        if search:
            conditions.append(
                or_(
                    EmagProductV2.sku.ilike(f"%{search}%"),
                    EmagProductV2.name.ilike(f"%{search}%"),
                )
            )
        
        # Count total
        count_stmt = select(func.count(EmagProductV2.id))
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        
        result = await db.execute(count_stmt)
        total = result.scalar()
        
        # Get products - select only necessary columns to avoid issues with missing columns
        stmt = select(
            EmagProductV2.id,
            EmagProductV2.emag_id,
            EmagProductV2.sku,
            EmagProductV2.name,
            EmagProductV2.account_type,
            EmagProductV2.price,
            EmagProductV2.currency,
            EmagProductV2.stock_quantity,
            EmagProductV2.is_active,
            EmagProductV2.status,
            EmagProductV2.sync_status,
            EmagProductV2.last_synced_at,
            EmagProductV2.created_at,
            EmagProductV2.updated_at,
        )
        if conditions:
            stmt = stmt.where(*conditions)
        
        stmt = stmt.order_by(EmagProductV2.updated_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(stmt)
        products = result.all()
        
        return {
            "status": "success",
            "data": {
                "products": [
                    {
                        "id": str(row[0]),  # id
                        "emag_id": row[1],  # emag_id
                        "sku": row[2],  # sku
                        "name": row[3],  # name
                        "account_type": row[4],  # account_type
                        "price": row[5],  # price
                        "currency": row[6],  # currency
                        "stock_quantity": row[7],  # stock_quantity
                        "is_active": row[8],  # is_active
                        "status": row[9],  # status
                        "sync_status": row[10],  # sync_status
                        "last_synced_at": row[11].isoformat() if row[11] else None,  # last_synced_at
                        "created_at": row[12].isoformat(),  # created_at
                        "updated_at": row[13].isoformat(),  # updated_at
                    }
                    for row in products
                ],
                "pagination": {
                    "skip": skip,
                    "limit": limit,
                    "total": total,
                },
            },
        }
        
    except Exception as e:
        logger.error(f"Failed to get synced products: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get synced products: {str(e)}",
        )


@router.delete("/sync/{sync_id}")
async def cancel_sync(
    sync_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Cancel a running synchronization.
    
    **Note:** This only marks the sync as cancelled in the database.
    The actual sync process may take some time to stop.
    """
    try:
        from datetime import datetime
        from sqlalchemy import select
        from app.models.emag_models import EmagSyncLog
        
        # Get sync log
        stmt = select(EmagSyncLog).where(EmagSyncLog.id == sync_id)
        result = await db.execute(stmt)
        sync_log = result.scalar_one_or_none()
        
        if not sync_log:
            raise HTTPException(status_code=404, detail="Sync not found")
        
        if sync_log.status != "running":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel sync with status: {sync_log.status}",
            )
        
        # Mark as cancelled
        sync_log.status = "cancelled"
        sync_log.completed_at = datetime.utcnow()
        sync_log.duration_seconds = (
            sync_log.completed_at - sync_log.started_at
        ).total_seconds()
        await db.commit()
        
        return {
            "status": "success",
            "message": "Sync cancellation requested",
            "data": {
                "sync_id": str(sync_id),
            },
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel sync: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel sync: {str(e)}",
        )


@router.post("/cleanup-stuck-syncs")
async def cleanup_stuck_syncs(
    timeout_minutes: int = Query(default=15, ge=5, le=60),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Cleanup stuck synchronizations that have been running for too long.
    
    This marks syncs as 'failed' if they've been running longer than the timeout.
    
    **Query Parameters:**
    - `timeout_minutes`: Consider syncs stuck after this many minutes (default 15)
    """
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import select
        from app.models.emag_models import EmagSyncLog
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        
        # Find stuck syncs
        stmt = select(EmagSyncLog).where(
            EmagSyncLog.sync_type == "products",
            EmagSyncLog.status == "running",
            EmagSyncLog.started_at < cutoff_time,
        )
        result = await db.execute(stmt)
        stuck_syncs = result.scalars().all()
        
        # Mark as failed
        for sync in stuck_syncs:
            sync.status = "failed"
            sync.completed_at = datetime.utcnow()
            sync.duration_seconds = (
                sync.completed_at - sync.started_at
            ).total_seconds()
            if not sync.errors:
                sync.errors = []
            sync.errors.append({
                "error": f"Sync timed out after {timeout_minutes} minutes",
                "timestamp": datetime.utcnow().isoformat(),
            })
        
        await db.commit()
        
        logger.info(f"Cleaned up {len(stuck_syncs)} stuck syncs")
        
        return {
            "status": "success",
            "message": f"Cleaned up {len(stuck_syncs)} stuck synchronizations",
            "data": {
                "cleaned_count": len(stuck_syncs),
                "timeout_minutes": timeout_minutes,
                "sync_ids": [str(sync.id) for sync in stuck_syncs],
            },
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup stuck syncs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup stuck syncs: {str(e)}",
        )


@router.post("/test-connection")
async def test_emag_connection(
    account_type: str = Query(default="main"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Test connection to eMAG API.
    
    This endpoint verifies that the API credentials are valid
    and the connection to eMAG marketplace is working.
    """
    try:
        import os
        from app.services.emag_api_client import EmagApiClient
        
        # Get credentials
        prefix = f"EMAG_{account_type.upper()}_"
        username = os.getenv(f"{prefix}USERNAME")
        password = os.getenv(f"{prefix}PASSWORD")
        base_url = os.getenv(f"{prefix}BASE_URL", "https://marketplace-api.emag.ro/api-3")
        
        if not username or not password:
            raise HTTPException(
                status_code=400,
                detail=f"Missing credentials for {account_type} account",
            )
        
        # Test connection
        async with EmagApiClient(
            username=username,
            password=password,
            base_url=base_url,
        ) as client:
            # Try to fetch first page of products
            response = await client.get_products(page=1, items_per_page=1)
            
            return {
                "status": "success",
                "message": f"Connection to {account_type} account successful",
                "data": {
                    "account_type": account_type,
                    "base_url": base_url,
                    "total_products": response.get("total_count", 0),
                },
            }
        
    except Exception as e:
        logger.error(f"Connection test failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Connection test failed: {str(e)}",
        )
