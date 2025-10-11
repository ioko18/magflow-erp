"""
eMAG Synchronization API endpoints.

Handles synchronization operations for eMAG marketplace integration.
"""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_active_user
from app.core.config import get_settings
from app.core.dependency_injection import ServiceContext
from app.core.logging import get_logger
from app.services.emag.emag_integration_service import EmagIntegrationService

logger = get_logger(__name__)
router = APIRouter(prefix="/sync", tags=["emag-sync"])


async def _run_product_sync(account_type: str, full_sync: bool = False):
    """Background task for product synchronization."""
    try:
        settings = get_settings()
        context = ServiceContext(settings=settings)
        service = EmagIntegrationService(context, account_type=account_type)

        logger.info(
            f"Starting product sync - account: {account_type}, full: {full_sync}"
        )

        result = await service.sync_products(full_sync=full_sync)

        logger.info(
            f"Product sync completed - account: {account_type}, "
            f"synced: {result.get('synced', 0)}, errors: {result.get('errors', 0)}"
        )

    except Exception as e:
        logger.error(f"Product sync failed: {e}", exc_info=True)


async def _run_order_sync(account_type: str, days_back: int = 7):
    """Background task for order synchronization."""
    try:
        settings = get_settings()
        context = ServiceContext(settings=settings)
        service = EmagIntegrationService(context, account_type=account_type)

        logger.info(
            f"Starting order sync - account: {account_type}, days_back: {days_back}"
        )

        result = await service.sync_orders(days_back=days_back)

        logger.info(
            f"Order sync completed - account: {account_type}, "
            f"synced: {result.get('synced', 0)}, errors: {result.get('errors', 0)}"
        )

    except Exception as e:
        logger.error(f"Order sync failed: {e}", exc_info=True)


@router.post("/products")
async def sync_emag_products(
    background_tasks: BackgroundTasks,
    account_type: str = Query("main", description="Account type: main or fbe"),
    full_sync: bool = Query(False, description="Perform full synchronization"),
    async_mode: bool = Query(True, description="Run synchronization in background"),
    current_user=Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    Synchronize products from eMAG API to local database.

    Args:
        account_type: Account type (main or fbe)
        full_sync: If True, performs full sync; if False, incremental sync
        async_mode: If True, runs in background; if False, waits for completion

    Returns:
        Synchronization status and results
    """
    try:
        if async_mode:
            # Run in background
            background_tasks.add_task(_run_product_sync, account_type, full_sync)

            return {
                "success": True,
                "message": "Product synchronization started in background",
                "account_type": account_type,
                "full_sync": full_sync,
                "async_mode": True,
            }
        else:
            # Run synchronously
            settings = get_settings()
            context = ServiceContext(settings=settings)
            service = EmagIntegrationService(context, account_type=account_type)

            logger.info(f"Starting synchronous product sync - account: {account_type}")

            result = await service.sync_products(full_sync=full_sync)

            return {
                "success": True,
                "message": "Product synchronization completed",
                "account_type": account_type,
                "full_sync": full_sync,
                "async_mode": False,
                "result": result,
            }

    except Exception as e:
        logger.error(f"Error starting product sync: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start product synchronization: {str(e)}",
        )


@router.post("/orders")
async def sync_orders(
    background_tasks: BackgroundTasks,
    account_type: str = Query("main", description="Account type: main or fbe"),
    days_back: int = Query(7, ge=1, le=90, description="Number of days to sync"),
    async_mode: bool = Query(True, description="Run synchronization in background"),
    current_user=Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    Synchronize orders from eMAG API to local database.

    Args:
        account_type: Account type (main or fbe)
        days_back: Number of days to look back for orders
        async_mode: If True, runs in background; if False, waits for completion

    Returns:
        Synchronization status and results
    """
    try:
        if async_mode:
            # Run in background
            background_tasks.add_task(_run_order_sync, account_type, days_back)

            return {
                "success": True,
                "message": "Order synchronization started in background",
                "account_type": account_type,
                "days_back": days_back,
                "async_mode": True,
            }
        else:
            # Run synchronously
            settings = get_settings()
            context = ServiceContext(settings=settings)
            service = EmagIntegrationService(context, account_type=account_type)

            logger.info(f"Starting synchronous order sync - account: {account_type}")

            result = await service.sync_orders(days_back=days_back)

            return {
                "success": True,
                "message": "Order synchronization completed",
                "account_type": account_type,
                "days_back": days_back,
                "async_mode": False,
                "result": result,
            }

    except Exception as e:
        logger.error(f"Error starting order sync: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start order synchronization: {str(e)}",
        )


@router.get("/status")
async def get_sync_status(
    account_type: str = Query("main", description="Account type: main or fbe"),
    current_user=Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    Get synchronization status for an account.

    Args:
        account_type: Account type (main or fbe)

    Returns:
        Current synchronization status
    """
    try:
        settings = get_settings()
        context = ServiceContext(settings=settings)
        service = EmagIntegrationService(context, account_type=account_type)

        status_info = await service.get_sync_status()

        return {
            "success": True,
            "account_type": account_type,
            "status": status_info,
        }

    except Exception as e:
        logger.error(f"Error getting sync status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sync status: {str(e)}",
        )
