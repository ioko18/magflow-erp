"""
eMAG Management Endpoints.

Provides endpoints for monitoring, backup, health checks, and system management
for the eMAG integration.
"""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user
from app.core.database import get_async_session
from app.core.emag_rate_limiter import get_rate_limiter
from app.models.user import User
from app.services.emag.emag_monitoring import EmagMonitoringService
from app.services.infrastructure.backup_service import BackupService, scheduled_backup

router = APIRouter()


@router.get("/health", response_model=dict[str, Any])
async def get_emag_health(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get eMAG integration health status.

    Returns comprehensive health metrics including:
    - Overall health score (0-100)
    - System status (healthy, degraded, warning, critical)
    - Current metrics (error rate, response time, rate limit usage)
    - Active alerts
    """
    monitoring = EmagMonitoringService(db)
    health_status = await monitoring.get_health_status()

    return health_status


@router.get("/monitoring/metrics", response_model=dict[str, Any])
async def get_monitoring_metrics(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get detailed monitoring metrics.

    Returns:
    - Request rate and response times
    - Error rates and types
    - Rate limit usage
    - Sync success rates
    """
    monitoring = EmagMonitoringService(db)
    await monitoring.update_metrics()

    return {
        "metrics": monitoring.metrics,
        "alerts": monitoring.alerts,
        "timestamp": monitoring.metrics.get("timestamp"),
    }


@router.get("/monitoring/sync-stats", response_model=dict[str, Any])
async def get_sync_statistics(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get synchronization statistics for the last 24 hours.

    Returns:
    - Total syncs
    - Successful/failed syncs
    - Success rate
    - Average duration
    - Total items processed
    """
    monitoring = EmagMonitoringService(db)
    stats = await monitoring.get_sync_statistics()

    return stats


@router.get("/monitoring/product-stats", response_model=dict[str, Any])
async def get_product_statistics(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get product statistics.

    Returns:
    - Total products
    - Active/inactive products
    - Products by account (MAIN/FBE)
    - Recently synced products
    """
    monitoring = EmagMonitoringService(db)
    stats = await monitoring.get_product_statistics()

    return stats


@router.get("/rate-limiter/stats", response_model=dict[str, Any])
async def get_rate_limiter_stats(
    current_user: User = Depends(get_current_active_user),
):
    """
    Get rate limiter statistics.

    Returns:
    - Current usage for orders and other operations
    - Total requests made
    - Rate limit hits
    - Available tokens
    """
    limiter = get_rate_limiter()
    stats = await limiter.get_stats()

    return stats


@router.post("/rate-limiter/reset", response_model=dict[str, str])
async def reset_rate_limiter_stats(
    current_user: User = Depends(get_current_active_user),
):
    """Reset rate limiter statistics."""
    limiter = get_rate_limiter()
    await limiter.reset_stats()

    return {"message": "Rate limiter statistics reset successfully"}


@router.post("/backup/create", response_model=dict[str, Any])
async def create_backup(
    include_products: bool = True,
    include_offers: bool = True,
    include_orders: bool = True,
    include_sync_logs: bool = True,
    compress: bool = True,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a backup of eMAG data.

    Args:
        include_products: Include products in backup
        include_offers: Include offers in backup
        include_orders: Include orders in backup
        include_sync_logs: Include sync logs in backup
        compress: Compress backup with gzip

    Returns:
        Backup information including path and size
    """
    backup_service = BackupService(db)

    result = await backup_service.create_backup(
        include_products=include_products,
        include_offers=include_offers,
        include_orders=include_orders,
        include_sync_logs=include_sync_logs,
        compress=compress,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=500, detail=result.get("error", "Backup failed")
        )

    return result


@router.get("/backup/list", response_model=list[dict[str, Any]])
async def list_backups(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    List all available backups.

    Returns:
        List of backup information (filename, timestamp, size, etc.)
    """
    backup_service = BackupService(db)
    backups = await backup_service.list_backups()

    return backups


@router.post("/backup/cleanup", response_model=dict[str, Any])
async def cleanup_old_backups(
    days: int = 30,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete backups older than specified days.

    Args:
        days: Number of days to keep backups (default: 30)

    Returns:
        Cleanup results (deleted count, freed space)
    """
    backup_service = BackupService(db)
    result = await backup_service.cleanup_old_backups(days=days)

    if not result["success"]:
        raise HTTPException(
            status_code=500, detail=result.get("error", "Cleanup failed")
        )

    return result


@router.post("/backup/restore", response_model=dict[str, Any])
async def restore_backup(
    backup_path: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Restore data from a backup file.

    Args:
        backup_path: Path to the backup file

    Returns:
        Restore results
    """
    backup_service = BackupService(db)
    result = await backup_service.restore_backup(backup_path)

    if not result["success"]:
        raise HTTPException(
            status_code=500, detail=result.get("error", "Restore failed")
        )

    return result


@router.post("/backup/schedule", response_model=dict[str, str])
async def schedule_backup_task(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Schedule a backup task to run in the background.

    Returns:
        Confirmation message
    """
    background_tasks.add_task(scheduled_backup, db)

    return {"message": "Backup task scheduled successfully"}
