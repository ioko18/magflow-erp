"""RMA (Returns Management) API endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_async_session
from app.db.models import User
from app.models.rma import (
    RefundMethod,
    ReturnItem,
    ReturnReason,
    ReturnRequest,
    ReturnStatus,
)

router = APIRouter(prefix="/rma", tags=["rma"])


@router.post("/requests", response_model=dict)
async def create_return_request(
    order_id: int | None = None,
    emag_order_id: str | None = None,
    customer_name: str = None,
    customer_email: str | None = None,
    reason: ReturnReason = None,
    reason_description: str | None = None,
    items: list[dict] = None,  # List of item dicts with sku, quantity, etc.
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new return request."""
    # Generate return number

    return_number = (
        "RMA-"
        f"{datetime.now().strftime('%Y%m%d')}"
        "-"
        f"{abs(hash(str(order_id or emag_order_id) + (customer_email or ''))) % 10000:04d}"
    )

    # Create return request
    return_request = ReturnRequest(
        return_number=return_number,
        order_id=order_id,
        emag_order_id=emag_order_id,
        customer_name=customer_name,
        customer_email=customer_email,
        reason=reason,
        reason_description=reason_description,
        status=ReturnStatus.PENDING,
        account_type="main",  # Default to main, should be configurable
    )

    session.add(return_request)
    await session.commit()
    await session.refresh(return_request)

    # Create return items
    for item_data in items or []:
        return_item = ReturnItem(
            return_request_id=return_request.id,
            sku=item_data.get("sku"),
            product_name=item_data.get("product_name", ""),
            quantity=item_data.get("quantity", 1),
            unit_price=item_data.get("unit_price", 0.0),
            total_amount=item_data.get("total_amount", 0.0),
            condition=item_data.get("condition", "new"),
            reason=item_data.get("reason"),
            status=ReturnStatus.PENDING,
        )
        session.add(return_item)

    await session.commit()

    return {
        "message": "Return request created successfully",
        "return_request_id": return_request.id,
        "return_number": return_request.return_number,
        "status": return_request.status,
    }


@router.get("/requests", response_model=dict)
async def list_return_requests(
    status: ReturnStatus | None = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Number of results to return", ge=1, le=100),
    offset: int = Query(0, description="Number of results to skip", ge=0),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """List return requests with optional filtering."""
    query = select(ReturnRequest).order_by(ReturnRequest.created_at.desc())

    if status:
        query = query.where(ReturnRequest.status == status)

    result = await session.execute(query.offset(offset).limit(limit))
    return_requests = result.scalars().all()

    # Get total count
    count_query = select(ReturnRequest)
    if status:
        count_query = count_query.where(ReturnRequest.status == status)

    count_result = await session.execute(count_query)
    total_count = len(count_result.scalars().all())

    return {
        "return_requests": [
            {
                "id": rr.id,
                "return_number": rr.return_number,
                "order_id": rr.order_id,
                "customer_name": rr.customer_name,
                "status": rr.status,
                "reason": rr.reason,
                "created_at": rr.created_at,
                "refund_amount": rr.refund_amount,
            }
            for rr in return_requests
        ],
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
    }


@router.get("/requests/{request_id}", response_model=dict)
async def get_return_request(
    request_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Get detailed information about a return request."""
    result = await session.execute(
        select(ReturnRequest).where(ReturnRequest.id == request_id),
    )
    return_request = result.scalar_one_or_none()

    if not return_request:
        raise HTTPException(status_code=404, detail="Return request not found")

    # Get return items
    items_result = await session.execute(
        select(ReturnItem).where(ReturnItem.return_request_id == request_id),
    )
    return_items = items_result.scalars().all()

    return {
        "return_request": {
            "id": return_request.id,
            "return_number": return_request.return_number,
            "order_id": return_request.order_id,
            "emag_order_id": return_request.emag_order_id,
            "customer_name": return_request.customer_name,
            "customer_email": return_request.customer_email,
            "status": return_request.status,
            "reason": return_request.reason,
            "reason_description": return_request.reason_description,
            "refund_amount": return_request.refund_amount,
            "refund_method": return_request.refund_method,
            "refund_processed": return_request.refund_processed,
            "created_at": return_request.created_at,
            "updated_at": return_request.updated_at,
        },
        "return_items": [
            {
                "id": item.id,
                "sku": item.sku,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_amount": item.total_amount,
                "condition": item.condition,
                "status": item.status,
                "approved_quantity": item.approved_quantity,
                "rejected_quantity": item.rejected_quantity,
            }
            for item in return_items
        ],
    }


@router.put("/requests/{request_id}/status", response_model=dict)
async def update_return_request_status(
    request_id: int,
    status: ReturnStatus,
    approved_by: int | None = None,
    internal_notes: str | None = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Update the status of a return request."""
    result = await session.execute(
        select(ReturnRequest).where(ReturnRequest.id == request_id),
    )
    return_request = result.scalar_one_or_none()

    if not return_request:
        raise HTTPException(status_code=404, detail="Return request not found")

    # Update status
    return_request.status = status
    return_request.approved_by = approved_by or current_user.id
    return_request.approved_at = datetime.now(UTC)

    if internal_notes:
        return_request.internal_notes = internal_notes

    await session.commit()

    return {
        "message": "Return request status updated successfully",
        "return_request_id": return_request.id,
        "new_status": return_request.status,
    }


@router.post("/requests/{request_id}/process-refund", response_model=dict)
async def process_return_refund(
    request_id: int,
    refund_method: RefundMethod,
    refund_amount: float | None = None,
    notes: str | None = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Process refund for a return request."""
    result = await session.execute(
        select(ReturnRequest).where(ReturnRequest.id == request_id),
    )
    return_request = result.scalar_one_or_none()

    if not return_request:
        raise HTTPException(status_code=404, detail="Return request not found")

    if return_request.refund_processed:
        raise HTTPException(status_code=400, detail="Refund already processed")

    # Calculate refund amount if not provided
    if refund_amount is None:
        # Calculate based on approved items
        items_result = await session.execute(
            select(ReturnItem).where(
                and_(
                    ReturnItem.return_request_id == request_id,
                    ReturnItem.status == ReturnStatus.APPROVED,
                ),
            ),
        )
        approved_items = items_result.scalars().all()
        refund_amount = sum(item.total_amount for item in approved_items)

    # Create refund transaction
    transaction_id = (
        "REF-"
        f"{datetime.now().strftime('%Y%m%d')}"
        "-"
        f"{abs(hash(str(request_id) + str(refund_amount))) % 10000:04d}"
    )

    from app.models.rma import RefundTransaction

    refund_transaction = RefundTransaction(
        transaction_id=transaction_id,
        return_request_id=request_id,
        amount=refund_amount,
        currency=return_request.refund_amount_currency or "RON",
        method=refund_method,
        status="completed",  # Simplified for now
        notes=notes,
    )

    session.add(refund_transaction)

    # Update return request
    return_request.refund_amount = refund_amount
    return_request.refund_method = refund_method
    return_request.refund_processed = True
    return_request.refund_processed_at = datetime.now(UTC)
    return_request.processed_by = current_user.id
    return_request.processed_at = datetime.now(UTC)

    await session.commit()

    return {
        "message": "Refund processed successfully",
        "transaction_id": transaction_id,
        "refund_amount": refund_amount,
        "refund_method": refund_method,
    }


@router.get("/statistics", response_model=dict)
async def get_rma_statistics(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Get RMA statistics and metrics."""
    # Get counts by status
    status_counts = {}
    for status in ReturnStatus:
        result = await session.execute(
            select(ReturnRequest).where(ReturnRequest.status == status),
        )
        status_counts[status.value] = len(result.scalars().all())

    # Get counts by reason
    reason_counts = {}
    for reason in ReturnReason:
        result = await session.execute(
            select(ReturnRequest).where(ReturnRequest.reason == reason),
        )
        reason_counts[reason.value] = len(result.scalars().all())

    # Get refund statistics
    refund_result = await session.execute(
        select(ReturnRequest.refund_amount, ReturnRequest.refund_processed).where(
            ReturnRequest.refund_amount > 0,
        ),
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
