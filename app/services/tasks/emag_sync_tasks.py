"""
Celery tasks for automated eMAG synchronization.

This module provides background tasks for:
- Automatic order synchronization every 5 minutes
- Product synchronization
- Error recovery and retry logic
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Dict, Any

from celery import shared_task
from celery.utils.log import get_task_logger

from app.core.database import async_session_factory
from app.services.emag_order_service import EmagOrderService
from app.models.emag_models import EmagOrder, EmagSyncLog

logger = get_task_logger(__name__)


def run_async(coro):
    """
    Safely run async coroutine in Celery worker context with greenlet support.
    
    This wraps the async execution in a greenlet context which is required
    for SQLAlchemy async operations in Celery workers.
    """
    try:
        # Create a new event loop and run the coroutine
        # This works with solo pool which runs in the main thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(coro)
            return result
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Error running async coroutine: {e}", exc_info=True)
        raise


@shared_task(
    name="emag.sync_orders",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)
def sync_emag_orders_task(self) -> Dict[str, Any]:
    """
    Sync orders from both MAIN and FBE eMAG accounts.
    
    This task runs every 5 minutes to fetch new orders from eMAG API.
    It processes both accounts and returns statistics.
    
    Returns:
        Dict with sync statistics for both accounts
    """
    logger.info("Starting automated eMAG order synchronization")

    try:
        result = run_async(_sync_orders_async())
        logger.info(f"Order sync completed: {result}")
        return result
    except Exception as exc:
        logger.error(f"Order sync failed: {exc}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=exc)


async def _sync_orders_async() -> Dict[str, Any]:
    """
    Async implementation of order synchronization.
    
    Returns:
        Dict with sync results for both accounts
    """
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "accounts": {},
        "total_orders_synced": 0,
        "total_new_orders": 0,
        "errors": []
    }

    async with async_session_factory() as db:
        for account_type in ['main', 'fbe']:
            try:
                logger.info(f"Syncing orders for {account_type} account")

                async with EmagOrderService(account_type, db) as order_service:
                    # Sync new orders (status 1 = new)
                    sync_result = await order_service.sync_new_orders(
                        status_filter=1,
                        max_pages=10
                    )

                    results["accounts"][account_type] = {
                        "success": True,
                        "orders_synced": sync_result.get("orders_synced", 0),
                        "new_orders": sync_result.get("new_orders", 0),
                        "updated_orders": sync_result.get("updated_orders", 0),
                    }

                    results["total_orders_synced"] += sync_result.get("orders_synced", 0)
                    results["total_new_orders"] += sync_result.get("new_orders", 0)

                    logger.info(
                        f"{account_type}: Synced {sync_result.get('orders_synced', 0)} orders, "
                        f"{sync_result.get('new_orders', 0)} new"
                    )

            except Exception as e:
                logger.error(f"Failed to sync {account_type} orders: {e}", exc_info=True)
                results["accounts"][account_type] = {
                    "success": False,
                    "error": str(e)
                }
                results["errors"].append(f"{account_type}: {str(e)}")

    return results


@shared_task(
    name="emag.sync_products",
    bind=True,
    max_retries=2,
    default_retry_delay=600,  # 10 minutes
)
def sync_emag_products_task(
    self,
    account_type: str = "both",
    max_pages_per_account: int = 5
) -> Dict[str, Any]:
    """
    Sync products from eMAG accounts.
    
    Args:
        account_type: 'main', 'fbe', or 'both'
        max_pages_per_account: Maximum pages to fetch per account
        
    Returns:
        Dict with sync statistics
    """
    logger.info(f"Starting product sync for {account_type}")

    try:
        result = run_async(_sync_products_async(account_type, max_pages_per_account))
        logger.info(f"Product sync completed: {result}")
        return result
    except Exception as exc:
        logger.error(f"Product sync failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


async def _sync_products_async(
    account_type: str,
    max_pages_per_account: int
) -> Dict[str, Any]:
    """
    Async implementation of product synchronization using new sync service.
    
    Returns:
        Dict with sync results
    """
    from app.services.emag_product_sync_service import (
        EmagProductSyncService,
        SyncMode,
        ConflictResolutionStrategy,
    )
    
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "account_type": account_type,
        "products_synced": 0,
        "errors": []
    }

    async with async_session_factory() as db:
        try:
            async with EmagProductSyncService(
                db=db,
                account_type=account_type,
                conflict_strategy=ConflictResolutionStrategy.EMAG_PRIORITY,
            ) as sync_service:
                sync_result = await sync_service.sync_all_products(
                    mode=SyncMode.INCREMENTAL,
                    max_pages=max_pages_per_account,
                    items_per_page=100,
                    include_inactive=False,
                )

                results["products_synced"] = sync_result.get("total_processed", 0)
                results["created"] = sync_result.get("created", 0)
                results["updated"] = sync_result.get("updated", 0)
                results["failed"] = sync_result.get("failed", 0)

                logger.info(
                    f"Synced {results['products_synced']} products: "
                    f"{results['created']} created, {results['updated']} updated"
                )

        except Exception as e:
            logger.error(f"Failed to sync products: {e}", exc_info=True)
            results["errors"].append(str(e))
            raise

    return results


@shared_task(
    name="emag.auto_acknowledge_orders",
    bind=True,
    max_retries=3,
)
def auto_acknowledge_orders_task(self) -> Dict[str, Any]:
    """
    Automatically acknowledge new orders (status 1 → 2).
    
    This prevents eMAG from sending repeated notifications.
    
    Returns:
        Dict with acknowledgment statistics
    """
    logger.info("Starting auto-acknowledgment of new orders")

    try:
        result = run_async(_auto_acknowledge_async())
        logger.info(f"Auto-acknowledgment completed: {result}")
        return result
    except Exception as exc:
        logger.error(f"Auto-acknowledgment failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


async def _auto_acknowledge_async() -> Dict[str, Any]:
    """
    Async implementation of auto-acknowledgment.
    
    Returns:
        Dict with acknowledgment results
    """
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "accounts": {},
        "total_acknowledged": 0,
        "errors": []
    }

    async with async_session_factory() as db:
        for account_type in ['main', 'fbe']:
            try:
                async with EmagOrderService(account_type, db) as order_service:
                    # Get all new orders (status 1)
                    from sqlalchemy import select
                    query = select(EmagOrder).where(
                        EmagOrder.account_type == account_type,
                        EmagOrder.status == 1
                    )
                    result = await db.execute(query)
                    new_orders = result.scalars().all()

                    acknowledged = 0
                    for order in new_orders:
                        try:
                            await order_service.acknowledge_order(order.emag_order_id)
                            acknowledged += 1
                        except Exception as e:
                            logger.warning(
                                f"Failed to acknowledge order {order.emag_order_id}: {e}"
                            )

                    results["accounts"][account_type] = {
                        "success": True,
                        "acknowledged": acknowledged
                    }
                    results["total_acknowledged"] += acknowledged

                    logger.info(f"{account_type}: Acknowledged {acknowledged} orders")

            except Exception as e:
                logger.error(f"Failed to acknowledge {account_type} orders: {e}", exc_info=True)
                results["accounts"][account_type] = {
                    "success": False,
                    "error": str(e)
                }
                results["errors"].append(f"{account_type}: {str(e)}")

    return results


@shared_task(
    name="emag.cleanup_old_sync_logs",
    bind=True,
)
def cleanup_old_sync_logs_task(self, days_to_keep: int = 30) -> Dict[str, Any]:
    """
    Clean up old sync logs to prevent database bloat.
    
    Args:
        days_to_keep: Number of days to keep logs (default 30)
        
    Returns:
        Dict with cleanup statistics
    """
    logger.info(f"Cleaning up sync logs older than {days_to_keep} days")

    try:
        result = run_async(_cleanup_logs_async(days_to_keep))
        logger.info(f"Cleanup completed: {result}")
        return result
    except Exception as exc:
        logger.error(f"Cleanup failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


async def _cleanup_logs_async(days_to_keep: int) -> Dict[str, Any]:
    """
    Async implementation of log cleanup.
    
    Returns:
        Dict with cleanup results
    """
    from datetime import timedelta
    from sqlalchemy import delete

    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

    async with async_session_factory() as db:
        try:
            # Delete old sync logs
            stmt = delete(EmagSyncLog).where(
                EmagSyncLog.created_at < cutoff_date
            )
            result = await db.execute(stmt)
            await db.commit()

            deleted_count = result.rowcount

            logger.info(f"Deleted {deleted_count} old sync logs")

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "deleted_logs": deleted_count,
                "cutoff_date": cutoff_date.isoformat()
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to cleanup logs: {e}", exc_info=True)
            raise


@shared_task(
    name="emag.health_check",
    bind=True,
)
def health_check_task(self) -> Dict[str, Any]:
    """
    Perform health check on eMAG integration.
    
    Checks:
    - Database connectivity
    - eMAG API connectivity
    - Recent sync status
    
    Returns:
        Dict with health status
    """
    logger.info("Performing eMAG integration health check")

    try:
        result = run_async(_health_check_async())
        logger.info(f"Health check completed: {result}")
        return result
    except Exception as exc:
        logger.error(f"Health check failed: {exc}", exc_info=True)
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "unhealthy",
            "error": str(exc)
        }


async def _health_check_async() -> Dict[str, Any]:
    """
    Async implementation of health check.
    
    Returns:
        Dict with health status
    """
    health = {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "healthy",
        "checks": {}
    }

    async with async_session_factory() as db:
        try:
            # Check database
            from sqlalchemy import select, func
            result = await db.execute(select(func.count(EmagOrder.id)))
            order_count = result.scalar()

            health["checks"]["database"] = {
                "status": "healthy",
                "total_orders": order_count
            }

            # Check recent syncs
            from datetime import timedelta
            recent_cutoff = datetime.utcnow() - timedelta(hours=1)

            result = await db.execute(
                select(func.count(EmagSyncLog.id)).where(
                    EmagSyncLog.created_at >= recent_cutoff
                )
            )
            recent_syncs = result.scalar()

            health["checks"]["recent_activity"] = {
                "status": "healthy" if recent_syncs > 0 else "warning",
                "syncs_last_hour": recent_syncs
            }

        except Exception as e:
            health["status"] = "unhealthy"
            health["checks"]["error"] = str(e)
            logger.error(f"Health check failed: {e}", exc_info=True)

    return health
