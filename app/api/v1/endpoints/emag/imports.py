"""API endpoints for eMAG offer import operations."""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.models import User
from app.integrations.emag.services.emag_offer_import_service import (
    EmagOfferImportService,
)
from app.models.emag_offers import EmagImportConflict, EmagOfferSync

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/import/offers",
    response_model=dict[str, Any],
    status_code=status.HTTP_202_ACCEPTED,
)
async def import_emag_offers(
    background_tasks: BackgroundTasks,
    account_type: str = "main",
    conflict_strategy: str = "update",
    max_offers: int | None = None,
    filters: dict[str, Any] | None = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Import offers from eMAG and store them in the database.

    This endpoint triggers an asynchronous import operation.

    Args:
        account_type: Account type ('main' or 'fbe')
        conflict_strategy: Strategy for handling conflicts ('skip', 'update', 'merge', 'manual')
        max_offers: Maximum number of offers to import
        filters: Optional filters for the import

    Returns:
        Import operation details with sync_id for monitoring

    """
    # Validate conflict strategy
    valid_strategies = ["skip", "update", "merge", "manual"]
    if conflict_strategy not in valid_strategies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid conflict strategy. Must be one of: {', '.join(valid_strategies)}",
        )

    # Validate account type
    if account_type not in ["main", "fbe"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid account type. Must be 'main' or 'fbe'",
        )

    # Create import service
    import_service = EmagOfferImportService(db)

    # Start import in background
    background_tasks.add_task(
        _run_import_task,
        import_service=import_service,
        account_type=account_type,
        conflict_strategy=conflict_strategy,
        max_offers=max_offers,
        filters=filters,
        user_id=current_user.id,
        user_name=current_user.username,
    )

    return {
        "message": "Import operation started",
        "account_type": account_type,
        "conflict_strategy": conflict_strategy,
        "max_offers": max_offers,
        "status": "running",
        "note": "Use the returned sync_id to monitor progress",
    }


@router.get("/import/status/{sync_id}", response_model=dict[str, Any])
async def get_import_status(
    sync_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Get the status of an import operation.

    Args:
        sync_id: Import operation ID

    Returns:
        Import operation status and statistics

    """
    import_service = EmagOfferImportService(db)
    sync_record = await import_service.get_sync_status(sync_id)

    if not sync_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Import operation {sync_id} not found",
        )

    # Build response
    response = {
        "sync_id": sync_record.sync_id,
        "account_type": sync_record.account_type,
        "operation_type": sync_record.operation_type,
        "status": sync_record.status,
        "created_at": (
            sync_record.created_at.isoformat() if sync_record.created_at else None
        ),
        "started_at": (
            sync_record.started_at.isoformat() if sync_record.started_at else None
        ),
        "completed_at": (
            sync_record.completed_at.isoformat() if sync_record.completed_at else None
        ),
        "duration_seconds": sync_record.duration_seconds,
        "statistics": {
            "total_offers_processed": sync_record.total_offers_processed,
            "offers_created": sync_record.offers_created,
            "offers_updated": sync_record.offers_updated,
            "offers_failed": sync_record.offers_failed,
            "offers_skipped": sync_record.offers_skipped,
        },
        "error_count": sync_record.error_count,
        "errors": sync_record.errors if sync_record.errors else [],
        "filters": sync_record.filters if sync_record.filters else {},
        "initiated_by": sync_record.initiated_by,
    }

    # Add success rate if operation is completed
    if hasattr(sync_record, "is_completed") and sync_record.is_completed:
        response["success_rate"] = getattr(sync_record, "success_rate", 0)

    return response


@router.get("/import/history", response_model=list[dict[str, Any]])
async def list_import_operations(
    account_type: str | None = None,
    status: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """List import operations with optional filtering.

    Args:
        account_type: Filter by account type
        status: Filter by status
        limit: Maximum number of records to return

    Returns:
        List of import operations

    """
    import_service = EmagOfferImportService(db)
    operations = await import_service.list_sync_operations(
        account_type=account_type,
        status=status,
        limit=limit,
    )

    return [
        {
            "sync_id": op.sync_id,
            "account_type": op.account_type,
            "operation_type": op.operation_type,
            "status": op.status,
            "created_at": op.created_at.isoformat() if op.created_at else None,
            "started_at": op.started_at.isoformat() if op.started_at else None,
            "completed_at": op.completed_at.isoformat() if op.completed_at else None,
            "duration_seconds": op.duration_seconds,
            "total_offers_processed": op.total_offers_processed,
            "offers_created": op.offers_created,
            "offers_updated": op.offers_updated,
            "offers_failed": op.offers_failed,
            "offers_skipped": op.offers_skipped,
            "error_count": op.error_count,
            "initiated_by": op.initiated_by,
        }
        for op in operations
    ]


@router.get("/import/statistics", response_model=dict[str, Any])
async def get_import_statistics(
    account_type: str = "main",
    days: int = 30,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Get import statistics for the specified period.

    Args:
        account_type: Account type to get statistics for
        days: Number of days to look back

    Returns:
        Import statistics

    """
    import_service = EmagOfferImportService(db)
    stats = await import_service.get_import_statistics(
        account_type=account_type,
        days=days,
    )

    return stats


@router.get("/import/conflicts", response_model=list[dict[str, Any]])
async def list_import_conflicts(
    sync_id: str | None = None,
    status: str = "pending",
    limit: int = 50,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """List import conflicts that need manual review.

    Args:
        sync_id: Filter by specific sync operation
        status: Filter by conflict status ('pending', 'resolved', 'ignored')
        limit: Maximum number of records to return

    Returns:
        List of import conflicts

    """
    from sqlalchemy import select

    # Build query
    stmt = select(EmagImportConflict).order_by(EmagImportConflict.created_at.desc())

    if sync_id:
        stmt = stmt.where(EmagImportConflict.sync_id == sync_id)

    if status:
        stmt = stmt.where(EmagImportConflict.status == status)

    stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    conflicts = result.scalars().all()

    return [
        {
            "id": conflict.id,
            "sync_id": conflict.sync_id,
            "emag_offer_id": conflict.emag_offer_id,
            "emag_product_id": conflict.emag_product_id,
            "conflict_type": conflict.conflict_type,
            "emag_data": conflict.emag_data,
            "internal_data": conflict.internal_data,
            "resolution": conflict.resolution,
            "resolved_at": (
                conflict.resolved_at.isoformat() if conflict.resolved_at else None
            ),
            "resolved_by": conflict.resolved_by,
            "status": conflict.status,
            "notes": conflict.notes,
            "created_at": (
                conflict.created_at.isoformat() if conflict.created_at else None
            ),
        }
        for conflict in conflicts
    ]


@router.put("/import/conflicts/{conflict_id}", response_model=dict[str, Any])
async def resolve_import_conflict(
    conflict_id: int,
    resolution: str,
    notes: str | None = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Resolve an import conflict.

    Args:
        conflict_id: Conflict ID
        resolution: Resolution action ('skip', 'update', 'merge', 'ignore')
        notes: Optional notes about the resolution

    Returns:
        Updated conflict information

    """
    from sqlalchemy import select, update

    # Validate resolution
    valid_resolutions = ["skip", "update", "merge", "ignore"]
    if resolution not in valid_resolutions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid resolution. Must be one of: {', '.join(valid_resolutions)}",
        )

    # Get conflict
    stmt = select(EmagImportConflict).where(EmagImportConflict.id == conflict_id)
    result = await db.execute(stmt)
    conflict = result.scalars().first()

    if not conflict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conflict {conflict_id} not found",
        )

    # Update conflict
    update_stmt = (
        update(EmagImportConflict)
        .where(EmagImportConflict.id == conflict_id)
        .values(
            resolution=resolution if resolution != "ignore" else None,
            resolved_at=datetime.now() if resolution != "ignore" else None,
            resolved_by=current_user.username if resolution != "ignore" else None,
            status="resolved" if resolution != "ignore" else "ignored",
            notes=notes,
        )
    )

    await db.execute(update_stmt)
    await db.commit()

    # Refresh conflict data
    await db.refresh(conflict)

    return {
        "id": conflict.id,
        "sync_id": conflict.sync_id,
        "emag_offer_id": conflict.emag_offer_id,
        "emag_product_id": conflict.emag_product_id,
        "conflict_type": conflict.conflict_type,
        "resolution": conflict.resolution,
        "resolved_at": (
            conflict.resolved_at.isoformat() if conflict.resolved_at else None
        ),
        "resolved_by": conflict.resolved_by,
        "status": conflict.status,
        "notes": conflict.notes,
    }


@router.get("/import/dashboard", response_model=dict[str, Any])
async def get_import_dashboard(
    days: int = 7,
    account_type: str | None = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Get comprehensive import dashboard data.

    Args:
        days: Number of days to look back for statistics
        account_type: Filter by account type

    Returns:
        Dashboard data with statistics, recent syncs, and conflicts

    """
    import_service = EmagOfferImportService(db)

    # Get statistics
    stats = {}
    if account_type:
        stats[account_type] = await import_service.get_import_statistics(
            account_type=account_type,
            days=days,
        )
    else:
        # Get stats for both account types
        for acc_type in ["main", "fbe"]:
            try:
                stats[acc_type] = await import_service.get_import_statistics(
                    account_type=acc_type,
                    days=days,
                )
            except Exception:
                stats[acc_type] = {"error": f"Failed to get stats for {acc_type}"}

    # Get recent sync operations
    recent_syncs = await import_service.list_sync_operations(
        account_type=account_type,
        limit=10,
    )

    # Get pending conflicts
    from sqlalchemy import select

    stmt = (
        select(EmagImportConflict)
        .where(EmagImportConflict.status == "pending")
        .order_by(EmagImportConflict.created_at.desc())
        .limit(20)
    )

    if account_type:
        # Filter conflicts by account type through sync relationship
        from sqlalchemy.orm import joinedload

        stmt = stmt.options(joinedload(EmagImportConflict.sync)).where(
            EmagImportConflict.sync.has(account_type=account_type),
        )

    result = await db.execute(stmt)
    pending_conflicts = result.scalars().all()

    # Get sync health metrics
    health_metrics = await _calculate_sync_health_metrics(db, account_type, days)

    return {
        "period_days": days,
        "statistics": stats,
        "recent_syncs": [
            {
                "sync_id": sync.sync_id,
                "account_type": sync.account_type,
                "operation_type": sync.operation_type,
                "status": sync.status,
                "started_at": sync.started_at.isoformat() if sync.started_at else None,
                "completed_at": (
                    sync.completed_at.isoformat() if sync.completed_at else None
                ),
                "offers_processed": sync.total_offers_processed,
                "offers_created": sync.offers_created,
                "offers_updated": sync.offers_updated,
                "offers_failed": sync.offers_failed,
                "duration_seconds": sync.duration_seconds,
            }
            for sync in recent_syncs
        ],
        "pending_conflicts": [
            {
                "id": conflict.id,
                "sync_id": conflict.sync_id,
                "emag_offer_id": conflict.emag_offer_id,
                "conflict_type": conflict.conflict_type,
                "created_at": (
                    conflict.created_at.isoformat() if conflict.created_at else None
                ),
            }
            for conflict in pending_conflicts
        ],
        "health_metrics": health_metrics,
        "generated_at": datetime.now().isoformat(),
    }


@router.get("/import/health", response_model=dict[str, Any])
async def get_import_health_status(
    account_type: str | None = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Get health status of import operations.

    Args:
        account_type: Filter by account type

    Returns:
        Health status information

    """
    health_metrics = await _calculate_sync_health_metrics(db, account_type, days=1)

    # Determine overall health status
    if health_metrics["failed_syncs_last_24h"] > 0:
        overall_status = "unhealthy"
    elif health_metrics["avg_sync_duration"] > 300:  # 5 minutes
        overall_status = "degraded"
    elif health_metrics["successful_syncs_last_24h"] > 0:
        overall_status = "healthy"
    else:
        overall_status = "unknown"

    return {
        "status": overall_status,
        "metrics": health_metrics,
        "last_updated": datetime.now().isoformat(),
        "account_type": account_type,
    }


@router.post(
    "/import/saleable",
    response_model=dict[str, Any],
    status_code=status.HTTP_202_ACCEPTED,
)
async def import_saleable_emag_offers(
    background_tasks: BackgroundTasks,
    max_offers: int | None = None,
    account_type: str = "main",
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Import only saleable offers from eMAG according to API v4.4.8 validation rules.

    Saleable offers are those that can actually be sold based on:
    - status = 1 (active)
    - offer_validation_status = 1 (saleable)
    - validation_status ∈ {9, 11, 12} (approved statuses)
    - stock > 0

    Args:
        max_offers: Maximum number of saleable offers to import
        account_type: Account type ('main' or 'fbe')

    Returns:
        Import operation details with sync_id for monitoring

    """
    # Validate account type
    if account_type not in ["main", "fbe"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid account type. Must be 'main' or 'fbe'",
        )

    # Create import service
    import_service = EmagOfferImportService(db)

    # Start import in background
    background_tasks.add_task(
        _run_saleable_import_task,
        import_service=import_service,
        account_type=account_type,
        max_offers=max_offers,
        user_id=current_user.id,
        user_name=current_user.username,
    )

    return {
        "message": "Saleable offers import started",
        "account_type": account_type,
        "max_offers": max_offers,
        "filters_applied": {
            "status": 1,
            "offer_validation_status": 1,
            "validation_status": [9, 11, 12],
            "stock": "> 0",
        },
        "status": "running",
        "note": "Only importing offers that can actually be sold",
    }


@router.patch("/offers/{offer_id}/stock", response_model=dict[str, Any])
async def update_offer_stock(
    offer_id: int,
    stock_data: dict[str, Any],
    account_type: str = "main",
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Update stock for a specific offer using PATCH /offer_stock/{id} (API v4.4.8).

    This endpoint provides fast stock updates without full offer updates.

    Args:
        offer_id: eMAG offer ID to update
        stock_data: Stock update data
        account_type: Account type ('main' or 'fbe')

    Returns:
        Update result

    """
    from app.integrations.emag.services.emag_offer_import_service import (
        EmagOfferImportService,
    )

    # Validate stock data
    if "stock" not in stock_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stock value is required",
        )

    stock_value = stock_data["stock"]
    if not isinstance(stock_value, (int, dict)) or (
        isinstance(stock_value, int) and stock_value < 0
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid stock value. Must be non-negative integer or warehouse stock object",
        )

    # Create import service
    import_service = EmagOfferImportService(db)

    try:
        # Perform stock update
        result = await import_service.update_offer_stock(
            offer_id=offer_id,
            stock_data=stock_data,
            account_type=account_type,
            user_id=current_user.id,
            user_name=current_user.username,
        )

        return {
            "message": "Stock updated successfully",
            "offer_id": offer_id,
            "account_type": account_type,
            "stock_updated": stock_value,
            "result": result,
            "updated_by": current_user.username,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to update stock for offer {offer_id}: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stock update failed: {e!s}",
        ) from e


@router.post("/offers/schedule-update", response_model=dict[str, Any])
async def schedule_offer_update(
    update_data: dict[str, Any],
    account_type: str = "main",
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Schedule offer updates with start_date (API v4.4.8 feature).

    Allows programming price/stock updates for future dates (up to 60 days ahead).

    Args:
        update_data: Update data with start_date
        account_type: Account type ('main' or 'fbe')

    Returns:
        Scheduling result

    """
    from app.integrations.emag.services.emag_offer_import_service import (
        EmagOfferImportService,
    )

    # Validate required fields
    required_fields = ["offer_ids", "start_date"]
    for field in required_fields:
        if field not in update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Required field missing: {field}",
            )

    # Validate start_date format
    from datetime import datetime, timedelta

    try:
        start_date = datetime.fromisoformat(
            update_data["start_date"].replace("Z", "+00:00"),
        )
        now = datetime.now(start_date.tzinfo)

        # Validate date is not in past and not too far in future
        if start_date < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date cannot be in the past",
            )

        if start_date > now + timedelta(days=60):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date cannot be more than 60 days in the future",
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid start_date format: {e!s}",
        ) from e

    # Create import service
    import_service = EmagOfferImportService(db)

    try:
        # Schedule the update
        result = await import_service.schedule_offer_update(
            update_data=update_data,
            account_type=account_type,
            user_id=current_user.id,
            user_name=current_user.username,
        )

        return {
            "message": "Offer update scheduled successfully",
            "start_date": update_data["start_date"],
            "offer_ids": update_data["offer_ids"],
            "account_type": account_type,
            "result": result,
            "scheduled_by": current_user.username,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to schedule offer update: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schedule failed: {e!s}",
        ) from e


@router.post("/campaigns/proposals", response_model=dict[str, Any])
async def create_campaign_proposal(
    campaign_data: dict[str, Any],
    account_type: str = "main",
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Create campaign proposals with MultiDeals support (API v4.4.8).

    Args:
        campaign_data: Campaign proposal data
        account_type: Account type ('main' or 'fbe')

    Returns:
        Campaign creation result

    """
    from app.integrations.emag.services.emag_offer_import_service import (
        EmagOfferImportService,
    )

    # Validate required fields
    required_fields = ["id", "sale_price"]
    for field in required_fields:
        if field not in campaign_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Required field missing: {field}",
            )

    # Create import service
    import_service = EmagOfferImportService(db)

    try:
        # Create campaign proposal
        result = await import_service.create_campaign_proposal(
            campaign_data=campaign_data,
            account_type=account_type,
            user_id=current_user.id,
            user_name=current_user.username,
        )

        return {
            "message": "Campaign proposal created successfully",
            "campaign_id": campaign_data["id"],
            "account_type": account_type,
            "result": result,
            "created_by": current_user.username,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to create campaign proposal: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Campaign creation failed: {e!s}",
        ) from e


@router.post("/import/cleanup", response_model=dict[str, Any])
async def cleanup_old_import_data(
    days_to_keep: int = 90,
    account_type: str | None = None,
    dry_run: bool = True,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Clean up old import data and sync history.

    Args:
        days_to_keep: Number of days of data to keep
        account_type: Filter by account type
        dry_run: If True, only report what would be deleted

    Returns:
        Cleanup operation results

    """
    from datetime import timedelta

    from sqlalchemy import delete

    cutoff_date = datetime.now() - timedelta(days=days_to_keep)

    # Count records that would be deleted
    cleanup_stats = {
        "old_syncs_to_delete": 0,
        "old_conflicts_to_delete": 0,
        "cutoff_date": cutoff_date.isoformat(),
        "dry_run": dry_run,
    }

    # Count old sync records
    from sqlalchemy import func, select

    from app.models.emag_offers import EmagImportConflict, EmagOfferSync

    sync_query = (
        select(func.count())
        .select_from(EmagOfferSync)
        .where(EmagOfferSync.created_at < cutoff_date)
    )
    if account_type:
        sync_query = sync_query.where(EmagOfferSync.account_type == account_type)

    result = await db.execute(sync_query)
    cleanup_stats["old_syncs_to_delete"] = result.scalar()

    # Count old conflict records
    conflict_query = (
        select(func.count())
        .select_from(EmagImportConflict)
        .where(EmagImportConflict.created_at < cutoff_date)
    )

    result = await db.execute(conflict_query)
    cleanup_stats["old_conflicts_to_delete"] = result.scalar()

    if not dry_run:
        # Perform actual cleanup
        sync_delete = delete(EmagOfferSync).where(
            EmagOfferSync.created_at < cutoff_date,
        )
        if account_type:
            sync_delete = sync_delete.where(EmagOfferSync.account_type == account_type)

        conflict_delete = delete(EmagImportConflict).where(
            EmagImportConflict.created_at < cutoff_date,
        )

        # Execute deletions
        sync_result = await db.execute(sync_delete)
        conflict_result = await db.execute(conflict_delete)

        await db.commit()

        cleanup_stats["syncs_deleted"] = sync_result.rowcount
        cleanup_stats["conflicts_deleted"] = conflict_result.rowcount
        cleanup_stats["status"] = "completed"

    else:
        cleanup_stats["status"] = "dry_run_completed"

    return cleanup_stats


async def _calculate_sync_health_metrics(
    db: AsyncSession,
    account_type: str | None,
    days: int,
) -> dict[str, Any]:
    """Calculate sync health metrics.

    Args:
        db: Database session
        account_type: Account type filter
        days: Number of days to look back

    Returns:
        Health metrics dictionary

    """
    from datetime import timedelta

    from sqlalchemy import func, select

    cutoff_date = datetime.now() - timedelta(days=days)

    # Base query for sync operations
    base_query = (
        select(
            func.count().label("total_syncs"),
            func.sum(EmagOfferSync.total_offers_processed).label(
                "total_offers_processed",
            ),
            func.avg(EmagOfferSync.duration_seconds).label("avg_duration"),
            func.count()
            .filter(EmagOfferSync.status == "completed")
            .label("successful_syncs"),
            func.count().filter(EmagOfferSync.status == "failed").label("failed_syncs"),
        )
        .select_from(EmagOfferSync)
        .where(EmagOfferSync.created_at >= cutoff_date)
    )

    if account_type:
        base_query = base_query.where(EmagOfferSync.account_type == account_type)

    result = await db.execute(base_query)
    row = result.first()

    metrics = {
        "period_days": days,
        "total_syncs_last_period": row.total_syncs or 0,
        "successful_syncs_last_period": row.successful_syncs or 0,
        "failed_syncs_last_period": row.failed_syncs or 0,
        "total_offers_processed": row.total_offers_processed or 0,
        "avg_sync_duration": row.avg_duration or 0,
        "success_rate": 0,
    }

    # Calculate success rate
    total_syncs = row.total_syncs or 0
    if total_syncs > 0:
        metrics["success_rate"] = (row.successful_syncs or 0) / total_syncs * 100

    # Get last 24h specific metrics
    last_24h_cutoff = datetime.now() - timedelta(hours=24)

    recent_query = (
        select(
            func.count()
            .filter(EmagOfferSync.status == "completed")
            .label("successful_24h"),
            func.count().filter(EmagOfferSync.status == "failed").label("failed_24h"),
        )
        .select_from(EmagOfferSync)
        .where(EmagOfferSync.created_at >= last_24h_cutoff)
    )

    if account_type:
        recent_query = recent_query.where(EmagOfferSync.account_type == account_type)

    result = await db.execute(recent_query)
    recent_row = result.first()

    metrics["successful_syncs_last_24h"] = recent_row.successful_24h or 0
    metrics["failed_syncs_last_24h"] = recent_row.failed_24h or 0

    return metrics


async def _run_import_task(
    import_service: EmagOfferImportService,
    account_type: str,
    conflict_strategy: str,
    max_offers: int | None,
    filters: dict[str, Any] | None,
    user_id: int | None,
    user_name: str | None,
) -> None:
    """Background task to run the import operation.

    Args:
        import_service: Import service instance
        account_type: Account type
        conflict_strategy: Conflict resolution strategy
        max_offers: Maximum number of offers to import
        filters: Import filters
        user_id: User ID who initiated the import
        user_name: Username who initiated the import

    """
    try:
        # Convert string strategy to enum
        from app.integrations.emag.services.emag_offer_import_service import (
            ConflictResolutionStrategy,
        )

        strategy_map = {
            "skip": ConflictResolutionStrategy.SKIP,
            "update": ConflictResolutionStrategy.UPDATE,
            "merge": ConflictResolutionStrategy.MERGE,
            "manual": ConflictResolutionStrategy.MANUAL,
        }
        strategy = strategy_map.get(
            conflict_strategy,
            ConflictResolutionStrategy.UPDATE,
        )

        # Run the import
        sync_id, result = await import_service.import_offers_from_emag(
            account_type=account_type,
            filters=filters,
            conflict_strategy=strategy,
            max_offers=max_offers,
            user_id=user_id,
            user_name=user_name,
        )

        logger.info(
            f"Import task completed: {sync_id}, processed {result.offers_processed} offers",
        )

    except Exception as e:
        logger.error(f"Import task failed: {e!s}", exc_info=True)


async def _run_saleable_import_task(
    import_service: EmagOfferImportService,
    account_type: str,
    max_offers: int | None,
    user_id: int | None,
    user_name: str | None,
) -> None:
    """Background task to run saleable offers import.

    Args:
        import_service: Import service instance
        account_type: Account type
        max_offers: Maximum number of offers to import
        user_id: User ID who initiated the import
        user_name: Username who initiated the import

    """
    try:
        # Run the saleable offers import
        sync_id, result = await import_service.import_saleable_offers(
            account_type=account_type,
            max_offers=max_offers,
            user_id=user_id,
            user_name=user_name,
        )

        logger.info(
            "Saleable import task completed: %s, processed %d offers",
            sync_id,
            result.offers_processed,
        )

    except Exception as e:
        logger.error(f"Saleable import task failed: {e!s}", exc_info=True)
