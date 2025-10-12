"""
eMAG Orders API endpoints.

Handles order-related operations for eMAG marketplace integration.
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_active_user
from app.core.config import get_settings
from app.core.dependency_injection import ServiceContext
from app.core.logging import get_logger
from app.services.emag.emag_integration_service import EmagIntegrationService

logger = get_logger(__name__)
router = APIRouter(prefix="/orders", tags=["emag-orders"])


@router.get("/")
async def get_orders(
    account_type: str = Query("main", description="Account type: main or fbe"),
    status_filter: str | None = Query(None, description="Filter by order status"),
    days_back: int = Query(7, ge=1, le=90, description="Number of days to look back"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of orders"),
    current_user=Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    Get orders from eMAG API.

    Args:
        account_type: Account type (main or fbe)
        status_filter: Filter by order status
        days_back: Number of days to look back
        limit: Maximum number of orders

    Returns:
        Dictionary with orders and metadata
    """
    try:
        settings = get_settings()
        context = ServiceContext(settings=settings)
        service = EmagIntegrationService(context, account_type=account_type)

        # Initialize the service
        await service.initialize()

        logger.info(
            f"Fetching orders from eMAG - account: {account_type}, "
            f"status: {status_filter}, days_back: {days_back}"
        )

        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            # Get orders from eMAG API
            orders = await service.get_orders(
                start_date=start_date,
                end_date=end_date,
                status=status_filter,
                limit=limit,
            )

            return {
                "success": True,
                "account_type": account_type,
                "count": len(orders),
                "filters": {
                    "status": status_filter,
                    "days_back": days_back,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "orders": orders,
            }
        finally:
            # Clean up the service
            await service.close()

    except Exception as e:
        logger.error(f"Error fetching orders: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch orders: {str(e)}",
        ) from e


@router.get("/{order_id}")
async def get_order_by_id(
    order_id: int,
    account_type: str = Query("main", description="Account type: main or fbe"),
    current_user=Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    Get a specific order by ID from eMAG API.

    Args:
        order_id: eMAG order ID
        account_type: Account type (main or fbe)

    Returns:
        Order details
    """
    try:
        settings = get_settings()
        context = ServiceContext(settings=settings)
        service = EmagIntegrationService(context, account_type=account_type)

        # Initialize the service
        await service.initialize()

        logger.info(f"Fetching order {order_id} from eMAG - account: {account_type}")

        try:
            order = await service.get_order_by_id(order_id)

            if not order:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Order {order_id} not found",
                )

            return {
                "success": True,
                "account_type": account_type,
                "order": order,
            }
        finally:
            # Clean up the service
            await service.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching order {order_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch order: {str(e)}",
        ) from e


@router.get("/count")
async def get_orders_count(
    account_type: str = Query("main", description="Account type: main or fbe"),
    status_filter: str | None = Query(None, description="Filter by order status"),
    days_back: int = Query(7, ge=1, le=90, description="Number of days to look back"),
    current_user=Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    Get count of orders from eMAG API.

    Args:
        account_type: Account type (main or fbe)
        status_filter: Filter by order status
        days_back: Number of days to look back

    Returns:
        Total count of orders
    """
    try:
        settings = get_settings()
        context = ServiceContext(settings=settings)
        service = EmagIntegrationService(context, account_type=account_type)

        # Initialize the service
        await service.initialize()

        logger.info(
            f"Getting orders count from eMAG - account: {account_type}, "
            f"status: {status_filter}, days_back: {days_back}"
        )

        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            count = await service.get_orders_count(
                start_date=start_date,
                end_date=end_date,
                status=status_filter,
            )

            return {
                "success": True,
                "account_type": account_type,
                "total_count": count,
                "filters": {
                    "status": status_filter,
                    "days_back": days_back,
                },
            }
        finally:
            # Clean up the service
            await service.close()

    except Exception as e:
        logger.error(f"Error getting orders count: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get orders count: {str(e)}",
        ) from e
