"""Order Cancellation API endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_async_session
from app.db.models import User
from app.models.cancellation import (
    CancellationItem,
    CancellationReason,
    CancellationRequest,
    CancellationStatus,
    RefundStatus,
)

router = APIRouter(prefix="/cancellations", tags=["cancellations"])


@router.post("/", response_model=dict)
async def create_cancellation_request(
    order_id: int | None = None,
    emag_order_id: str | None = None,
    customer_name: str = None,
    customer_email: str | None = None,
    reason: CancellationReason = None,
    reason_description: str | None = None,
    cancellation_fee: float = 0.0,
    refund_amount: float = 0.0,
    currency: str = "RON",
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new cancellation request."""
    # Generate cancellation number
    cancellation_number = f"CAN-{datetime.now().strftime('%Y%m%d')}-{abs(hash(str(order_id or emag_order_id) + (customer_email or ''))) % 10000:04d}"

    # Create cancellation request
    cancellation_request = CancellationRequest(
        cancellation_number=cancellation_number,
        order_id=order_id,
        emag_order_id=emag_order_id,
        customer_name=customer_name,
        customer_email=customer_email,
        reason=reason,
        reason_description=reason_description,
        status=CancellationStatus.PENDING,
        cancellation_fee=cancellation_fee,
        refund_amount=refund_amount,
        currency=currency,
        refund_status=RefundStatus.PENDING,
        account_type="main",  # Default to main, should be configurable
    )

    session.add(cancellation_request)
    await session.commit()
    await session.refresh(cancellation_request)

    return {
        "message": "Cancellation request created successfully",
        "cancellation_request_id": cancellation_request.id,
        "cancellation_number": cancellation_request.cancellation_number,
        "status": cancellation_request.status,
    }


@router.get("/", response_model=dict)
async def list_cancellation_requests(
    status: CancellationStatus | None = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Number of results to return", ge=1, le=100),
    offset: int = Query(0, description="Number of results to skip", ge=0),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """List cancellation requests with optional filtering."""
    query = select(CancellationRequest).order_by(CancellationRequest.created_at.desc())

    if status:
        query = query.where(CancellationRequest.status == status)

    result = await session.execute(query.offset(offset).limit(limit))
    cancellation_requests = result.scalars().all()

    # Get total count
    count_query = select(CancellationRequest)
    if status:
        count_query = count_query.where(CancellationRequest.status == status)

    count_result = await session.execute(count_query)
    total_count = len(count_result.scalars().all())

    return {
        "cancellation_requests": [
            {
                "id": cr.id,
                "cancellation_number": cr.cancellation_number,
                "order_id": cr.order_id,
                "customer_name": cr.customer_name,
                "status": cr.status,
                "reason": cr.reason,
                "refund_amount": cr.refund_amount,
                "created_at": cr.created_at,
            }
            for cr in cancellation_requests
        ],
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{request_id}", response_model=dict)
async def get_cancellation_request(
    request_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Get detailed information about a cancellation request."""
    result = await session.execute(
        select(CancellationRequest).where(CancellationRequest.id == request_id),
    )
    cancellation_request = result.scalar_one_or_none()

    if not cancellation_request:
        raise HTTPException(status_code=404, detail="Cancellation request not found")

    # Get cancellation items
    items_result = await session.execute(
        select(CancellationItem).where(
            CancellationItem.cancellation_request_id == request_id,
        ),
    )
    cancellation_items = items_result.scalars().all()

    return {
        "cancellation_request": {
            "id": cancellation_request.id,
            "cancellation_number": cancellation_request.cancellation_number,
            "order_id": cancellation_request.order_id,
            "emag_order_id": cancellation_request.emag_order_id,
            "customer_name": cancellation_request.customer_name,
            "customer_email": cancellation_request.customer_email,
            "status": cancellation_request.status,
            "reason": cancellation_request.reason,
            "reason_description": cancellation_request.reason_description,
            "cancellation_fee": cancellation_request.cancellation_fee,
            "refund_amount": cancellation_request.refund_amount,
            "currency": cancellation_request.currency,
            "refund_status": cancellation_request.refund_status,
            "stock_restored": cancellation_request.stock_restored,
            "created_at": cancellation_request.created_at,
            "updated_at": cancellation_request.updated_at,
        },
        "cancellation_items": [
            {
                "id": item.id,
                "sku": item.sku,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_amount": item.total_amount,
                "stock_to_restore": item.stock_to_restore,
                "stock_restored": item.stock_restored,
                "refund_amount": item.refund_amount,
            }
            for item in cancellation_items
        ],
    }


@router.put("/{request_id}/status", response_model=dict)
async def update_cancellation_status(
    request_id: int,
    status: CancellationStatus,
    approved_by: int | None = None,
    internal_notes: str | None = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Update the status of a cancellation request."""
    result = await session.execute(
        select(CancellationRequest).where(CancellationRequest.id == request_id),
    )
    cancellation_request = result.scalar_one_or_none()

    if not cancellation_request:
        raise HTTPException(status_code=404, detail="Cancellation request not found")

    # Update status
    cancellation_request.status = status
    cancellation_request.approved_by = approved_by or current_user.id
    cancellation_request.approved_at = datetime.now(UTC)

    if internal_notes:
        cancellation_request.internal_notes = internal_notes

    await session.commit()

    return {
        "message": "Cancellation status updated successfully",
        "cancellation_request_id": cancellation_request.id,
        "new_status": cancellation_request.status,
    }


@router.post("/{request_id}/process", response_model=dict)
async def process_cancellation(
    request_id: int,
    process_refund: bool = True,
    restore_stock: bool = True,
    notes: str | None = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Process a cancellation request (refund and stock restoration)."""
    result = await session.execute(
        select(CancellationRequest).where(CancellationRequest.id == request_id),
    )
    cancellation_request = result.scalar_one_or_none()

    if not cancellation_request:
        raise HTTPException(status_code=404, detail="Cancellation request not found")

    if cancellation_request.status == CancellationStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Cancellation already processed")

    # Process refund if requested
    if process_refund and cancellation_request.refund_amount > 0:
        from app.models.cancellation import CancellationRefund

        refund_id = f"CRF-{datetime.now().strftime('%Y%m%d')}-{abs(hash(str(request_id))) % 10000:04d}"

        refund = CancellationRefund(
            refund_id=refund_id,
            cancellation_request_id=request_id,
            order_id=cancellation_request.order_id,
            amount=cancellation_request.refund_amount,
            currency=cancellation_request.currency,
            refund_method="original_payment",  # Default method
            status="completed",  # Simplified for now
        )

        session.add(refund)

        cancellation_request.refund_status = RefundStatus.COMPLETED
        cancellation_request.refund_processed = True
        cancellation_request.refund_processed_at = datetime.now(UTC)

    # Restore stock if requested
    if restore_stock:
        items_result = await session.execute(
            select(CancellationItem).where(
                CancellationItem.cancellation_request_id == request_id,
            ),
        )
        cancellation_items = items_result.scalars().all()

        for item in cancellation_items:
            if item.stock_to_restore > 0:
                item.stock_restored = True

        cancellation_request.stock_restored = True
        cancellation_request.stock_restored_at = datetime.now(UTC)

    # Update cancellation status
    cancellation_request.status = CancellationStatus.COMPLETED
    cancellation_request.processed_by = current_user.id
    cancellation_request.processed_at = datetime.now(UTC)

    if notes:
        cancellation_request.internal_notes = notes

    await session.commit()

    return {
        "message": "Cancellation processed successfully",
        "cancellation_request_id": cancellation_request.id,
        "refund_processed": process_refund,
        "stock_restored": restore_stock,
    }


@router.get("/statistics", response_model=dict)
async def get_cancellation_statistics(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Get cancellation statistics and metrics."""
    # Get counts by status
    status_counts = {}
    for status in CancellationStatus:
        result = await session.execute(
            select(CancellationRequest).where(CancellationRequest.status == status),
        )
        status_counts[status.value] = len(result.scalars().all())

    # Get counts by reason
    reason_counts = {}
    for reason in CancellationReason:
        result = await session.execute(
            select(CancellationRequest).where(CancellationRequest.reason == reason),
        )
        reason_counts[reason.value] = len(result.scalars().all())

    # Get refund statistics
    refund_result = await session.execute(
        select(
            CancellationRequest.refund_amount,
            CancellationRequest.refund_processed,
        ).where(CancellationRequest.refund_amount > 0),
    )
    refund_data = refund_result.all()

    total_refund_amount = sum(row[0] for row in refund_data if row[0])
    processed_refunds = sum(1 for row in refund_data if row[1])

    return {
        "total_requests": sum(status_counts.values()),
        "status_breakdown": status_counts,
        "reason_breakdown": reason_counts,
        "refund_statistics": {
            "total_refund_amount": total_refund_amount,
            "processed_refunds": processed_refunds,
            "pending_refunds": len(refund_data) - processed_refunds,
        },
    }
