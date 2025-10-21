"""
eMAG Orders API Endpoints for MagFlow ERP.

This module provides REST API endpoints for managing eMAG orders including:
- Order synchronization
- Order acknowledgment
- Status updates
- Invoice and warranty attachment
"""

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.emag_models import EmagOrder
from app.models.user import User
from app.services.emag.emag_order_service import EmagOrderService

logger = get_logger(__name__)

# Global lock to prevent concurrent syncs
_sync_lock = asyncio.Lock()
_sync_in_progress = False

router = APIRouter()


# ========== Request/Response Models ==========


class OrderSyncRequest(BaseModel):
    """Request model for order synchronization."""

    account_type: str = Field(..., description="Account type (main, fbe, or both)")
    status_filter: int | None = Field(
        None, description="Order status filter (1=new, 2=in_progress, etc.)"
    )
    max_pages: int = Field(50, description="Maximum pages to fetch per account")
    days_back: int | None = Field(
        None, description="Number of days to look back for orders"
    )
    sync_mode: str = Field(
        "incremental",
        description=(
            "Sync mode: incremental (only new/updated), "
            "full (all orders), historical (specific date range)"
        ),
    )
    start_date: str | None = Field(
        None, description="Start date for historical sync (YYYY-MM-DD)"
    )
    end_date: str | None = Field(
        None, description="End date for historical sync (YYYY-MM-DD)"
    )
    auto_acknowledge: bool = Field(
        False, description="Automatically acknowledge new orders (status 1 -> 2)"
    )


class OrderAcknowledgeRequest(BaseModel):
    """Request model for order acknowledgment."""

    account_type: str = Field(..., description="Account type (main or fbe)")


class OrderStatusUpdateRequest(BaseModel):
    """Request model for order status update."""

    account_type: str = Field(..., description="Account type (main or fbe)")
    new_status: int = Field(..., description="New status code (0-5)")
    products: list[dict[str, Any]] | None = Field(
        None, description="Updated products"
    )


class InvoiceAttachRequest(BaseModel):
    """Request model for invoice attachment."""

    account_type: str = Field(..., description="Account type (main or fbe)")
    invoice_url: str = Field(..., description="Public URL of invoice PDF")
    invoice_name: str | None = Field(None, description="Display name for invoice")


class OrderResponse(BaseModel):
    """Response model for order data."""

    id: str
    emag_order_id: int
    account_type: str
    status: int
    status_name: str | None
    customer_name: str | None
    customer_email: str | None
    total_amount: float
    currency: str
    payment_method: str | None
    order_date: str | None
    sync_status: str

    class Config:
        from_attributes = True


# ========== Endpoints ==========


@router.post("/sync", status_code=status.HTTP_200_OK)
async def sync_orders(
    request: OrderSyncRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Synchronize orders from eMAG for specified account(s).

    This endpoint fetches orders from eMAG API and saves them to the database.
    Supports syncing from MAIN, FBE, or BOTH accounts.

    For MAIN account: Only syncs orders from last 6 months (no orders since 31.03.2025)
    For FBE account: Syncs all recent orders (has daily orders)
    """
    global _sync_in_progress

    # Check if sync is already in progress
    if _sync_lock.locked():
        logger.warning(
            "User %s attempted to start sync while another sync is in progress",
            current_user.email,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another sync operation is already in progress. Please wait for it to complete.",
        )

    async with _sync_lock:
        _sync_in_progress = True
        logger.info(
            "User %s initiating order sync for %s account",
            current_user.email,
            request.account_type,
        )

        try:
            # Determine days_back based on sync_mode
            if request.sync_mode == "incremental":
                # Only sync last 7 days for incremental
                effective_days_back = 7
                logger.info("Incremental sync mode: last 7 days")
            elif request.sync_mode == "historical":
                # Historical sync with date range
                effective_days_back = None  # Will use start_date/end_date
                logger.info(
                    f"Historical sync mode: {request.start_date} to {request.end_date}"
                )
            else:  # full
                # Full sync based on request or defaults
                effective_days_back = request.days_back
                logger.info(f"Full sync mode: {effective_days_back or 'all'} days")

            if request.account_type == "both":
                # Sync both accounts in parallel
                results = {}

                # Create tasks for parallel execution
                async def sync_main():
                    logger.info("Syncing MAIN account orders")
                    async with EmagOrderService("main", db) as main_service:
                        return await main_service.sync_new_orders(
                            status_filter=request.status_filter,
                            max_pages=request.max_pages,
                            days_back=180 if request.sync_mode != "incremental" else 7,
                        )

                async def sync_fbe():
                    logger.info("Syncing FBE account orders")
                    async with EmagOrderService("fbe", db) as fbe_service:
                        return await fbe_service.sync_new_orders(
                            status_filter=request.status_filter,
                            max_pages=request.max_pages,
                            days_back=effective_days_back,
                        )

                # Run both syncs in parallel with timeout
                main_task = asyncio.create_task(sync_main())
                fbe_task = asyncio.create_task(sync_fbe())

                try:
                    # Wait for both with 15 minute timeout (increased for large syncs)
                    results["main"], results["fbe"] = await asyncio.wait_for(
                        asyncio.gather(main_task, fbe_task),
                        timeout=900.0
                    )
                except TimeoutError:
                    logger.error("Sync operation timed out after 15 minutes")
                    main_task.cancel()
                    fbe_task.cancel()
                    raise HTTPException(
                        status_code=status.HTTP_408_REQUEST_TIMEOUT,
                        detail=(
                            "Sync operation timed out. "
                            "Please try again with fewer pages or use "
                            "incremental sync mode."
                        ),
                    ) from None

                total_synced = results["main"].get("synced", 0) + results["fbe"].get(
                    "synced", 0
                )
                total_created = results["main"].get("created", 0) + results["fbe"].get(
                    "created", 0
                )
                total_updated = results["main"].get("updated", 0) + results["fbe"].get(
                    "updated", 0
                )

                return {
                    "success": True,
                    "message": (
                        "Successfully synced orders from both accounts: "
                        f"{total_synced} total "
                        f"({total_created} new, {total_updated} updated)"
                    ),
                    "data": {
                        "main_account": results["main"],
                        "fbe_account": results["fbe"],
                        "totals": {
                            "synced": total_synced,
                            "created": total_created,
                            "updated": total_updated,
                        },
                    },
                }
            else:
                # Single account sync
                async with EmagOrderService(request.account_type, db) as order_service:
                    result = await order_service.sync_new_orders(
                        status_filter=request.status_filter,
                        max_pages=request.max_pages,
                        days_back=request.days_back,
                    )

                    return {
                        "success": True,
                        "message": (
                            "Successfully synced "
                            f"{result.get('synced', 0)} orders from "
                            f"{request.account_type} account"
                        ),
                        "data": result,
                    }

        except TimeoutError:
            raise  # Already handled above
        except Exception as e:
            logger.error("Order sync failed: %s", str(e), exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Order synchronization failed: {str(e)}",
            ) from e
        finally:
            _sync_in_progress = False


@router.get("/list", status_code=status.HTTP_200_OK)
@router.get("/all", status_code=status.HTTP_200_OK)
async def get_all_orders(
    account_type: str | None = Query(None, description="Filter by account type"),
    status_filter: int | None = Query(None, description="Filter by order status"),
    page: int = Query(1, ge=1, description="Page number"),
    items_per_page: int = Query(100, le=1000, description="Items per page"),
    limit: int | None = Query(
        None,
        le=1000,
        description="Maximum orders to return (deprecated, use items_per_page)",
    ),
    offset: int | None = Query(
        None, ge=0, description="Offset for pagination (deprecated, use page)"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get all orders from database with optional filtering.
    Supports both /list and /all endpoints for compatibility.
    """
    # Handle legacy parameters
    if limit is not None:
        items_per_page = limit
    if offset is not None:
        page = (offset // items_per_page) + 1 if items_per_page > 0 else 1

    # Calculate offset from page
    calculated_offset = (page - 1) * items_per_page
    try:
        # Build query
        query = select(EmagOrder)

        # Apply filters
        if account_type:
            query = query.where(EmagOrder.account_type == account_type)
        if status_filter is not None:
            query = query.where(EmagOrder.status == status_filter)

        # Add ordering
        query = query.order_by(EmagOrder.order_date.desc())

        # Apply pagination
        query = query.limit(items_per_page).offset(calculated_offset)

        # Execute query
        result = await db.execute(query)
        orders = result.scalars().all()

        # Get total count
        count_query = select(func.count(EmagOrder.id))
        if account_type:
            count_query = count_query.where(EmagOrder.account_type == account_type)
        if status_filter is not None:
            count_query = count_query.where(EmagOrder.status == status_filter)

        total_result = await db.execute(count_query)
        total_count = total_result.scalar()

        return {
            "success": True,
            "orders": [
                {
                    "id": str(order.id),
                    "emag_order_id": order.emag_order_id,
                    "account_type": order.account_type,
                    "status": order.status,
                    "status_name": order.status_name,
                    "customer_name": order.customer_name,
                    "customer_email": order.customer_email,
                    "customer_phone": order.customer_phone,
                    "total_amount": float(order.total_amount)
                    if order.total_amount
                    else 0.0,
                    "currency": order.currency,
                    "payment_method": order.payment_method,
                    "delivery_mode": order.delivery_mode,
                    "order_date": order.order_date.isoformat()
                    if order.order_date
                    else None,
                    "sync_status": order.sync_status,
                    "last_synced_at": order.last_synced_at.isoformat()
                    if order.last_synced_at
                    else None,
                    "awb_number": order.awb_number,
                    "courier_name": order.courier_name,
                    "invoice_url": order.invoice_url,
                    "invoice_uploaded_at": order.invoice_uploaded_at.isoformat()
                    if order.invoice_uploaded_at
                    else None,
                    "products": order.products or [],
                    "shipping_address": order.shipping_address,
                }
                for order in orders
            ],
            "total": total_count,
            "page": page,
            "items_per_page": items_per_page,
            "total_pages": (total_count + items_per_page - 1) // items_per_page
            if items_per_page > 0
            else 0,
        }

    except Exception as e:
        logger.error("Failed to fetch orders: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch orders: {str(e)}",
        ) from e


@router.get("/{order_id}", status_code=status.HTTP_200_OK)
async def get_order_details(
    order_id: int,
    account_type: str = Query(..., description="Account type (main or fbe)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get detailed information about a specific order.
    """
    try:
        # Query order from database
        query = select(EmagOrder).where(
            and_(
                EmagOrder.emag_order_id == order_id,
                EmagOrder.account_type == account_type,
            )
        )

        result = await db.execute(query)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order {order_id} not found for {account_type} account",
            )

        return {
            "success": True,
            "data": {
                "id": str(order.id),
                "emag_order_id": order.emag_order_id,
                "account_type": order.account_type,
                "status": order.status,
                "status_name": order.status_name,
                "customer_id": order.customer_id,
                "customer_name": order.customer_name,
                "customer_email": order.customer_email,
                "customer_phone": order.customer_phone,
                "total_amount": order.total_amount,
                "currency": order.currency,
                "payment_method": order.payment_method,
                "payment_status": order.payment_status,
                "delivery_mode": order.delivery_mode,
                "shipping_address": order.shipping_address,
                "billing_address": order.billing_address,
                "products": order.products,
                "vouchers": order.vouchers,
                "awb_number": order.awb_number,
                "invoice_url": order.invoice_url,
                "order_date": order.order_date.isoformat()
                if order.order_date
                else None,
                "acknowledged_at": order.acknowledged_at.isoformat()
                if order.acknowledged_at
                else None,
                "finalized_at": order.finalized_at.isoformat()
                if order.finalized_at
                else None,
                "sync_status": order.sync_status,
                "last_synced_at": order.last_synced_at.isoformat()
                if order.last_synced_at
                else None,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch order details: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch order details: {str(e)}",
        ) from e


@router.post("/{order_id}/acknowledge", status_code=status.HTTP_200_OK)
async def acknowledge_order(
    order_id: int,
    request: OrderAcknowledgeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Acknowledge an order (moves from status 1 'new' to status 2 'in progress').

    This is critical to stop eMAG notifications for the order.
    """
    logger.info(
        "User %s acknowledging order %d from %s account",
        current_user.email,
        order_id,
        request.account_type,
    )

    try:
        async with EmagOrderService(request.account_type, db) as order_service:
            result = await order_service.acknowledge_order(order_id)

            return {
                "success": True,
                "message": f"Order {order_id} acknowledged successfully",
                "data": result,
            }

    except Exception as e:
        logger.error("Order acknowledgment failed: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Order acknowledgment failed: {str(e)}",
        ) from e


@router.put("/{order_id}/status", status_code=status.HTTP_200_OK)
async def update_order_status(
    order_id: int,
    request: OrderStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Update order status.

    Valid status transitions:
    - 1 → 2: Via acknowledge only
    - 2 → 3: Prepared
    - 2 → 4: Finalized
    - 3 → 4: Finalized
    - 4 → 5: Returned (within RT+5 days)
    """
    logger.info(
        "User %s updating order %d status to %d",
        current_user.email,
        order_id,
        request.new_status,
    )

    try:
        async with EmagOrderService(request.account_type, db) as order_service:
            result = await order_service.update_order_status(
                order_id=order_id,
                new_status=request.new_status,
                products=request.products,
            )

            return {
                "success": True,
                "message": f"Order {order_id} status updated successfully",
                "data": result,
            }

    except Exception as e:
        logger.error("Order status update failed: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Order status update failed: {str(e)}",
        ) from e


@router.post("/{order_id}/invoice", status_code=status.HTTP_200_OK)
async def attach_invoice(
    order_id: int,
    request: InvoiceAttachRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Attach invoice PDF to finalized order.

    Required when moving order to status 4 (finalized).
    """
    logger.info("User %s attaching invoice to order %d", current_user.email, order_id)

    try:
        async with EmagOrderService(request.account_type, db) as order_service:
            result = await order_service.attach_invoice(
                order_id=order_id,
                invoice_url=request.invoice_url,
                invoice_name=request.invoice_name,
            )

            return {
                "success": True,
                "message": f"Invoice attached to order {order_id} successfully",
                "data": result,
            }

    except Exception as e:
        logger.error("Invoice attachment failed: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invoice attachment failed: {str(e)}",
        ) from e


@router.get("/statistics/summary", status_code=status.HTTP_200_OK)
async def get_order_statistics(
    account_type: str | None = Query(None, description="Filter by account type"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get order statistics and summary.
    """
    try:
        # Build base query
        base_query = select(EmagOrder)
        if account_type:
            base_query = base_query.where(EmagOrder.account_type == account_type)

        # Count by status
        stats = {}
        for status_code in range(6):  # 0-5
            count_query = select(func.count(EmagOrder.id)).where(
                EmagOrder.status == status_code
            )
            if account_type:
                count_query = count_query.where(EmagOrder.account_type == account_type)

            result = await db.execute(count_query)
            count = result.scalar()

            status_names = {
                0: "canceled",
                1: "new",
                2: "in_progress",
                3: "prepared",
                4: "finalized",
                5: "returned",
            }

            stats[status_names[status_code]] = count

        # Total orders
        total_query = select(func.count(EmagOrder.id))
        if account_type:
            total_query = total_query.where(EmagOrder.account_type == account_type)

        total_result = await db.execute(total_query)
        total_orders = total_result.scalar()

        return {
            "success": True,
            "data": {
                "total_orders": total_orders,
                "by_status": stats,
                "account_type": account_type or "all",
            },
        }

    except Exception as e:
        logger.error("Failed to fetch order statistics: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch order statistics: {str(e)}",
        ) from e
