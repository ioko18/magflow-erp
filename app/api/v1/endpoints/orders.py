from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Optional
from datetime import datetime, timedelta

from app.db.session import get_db
from app.models.order import Order
from app.schemas.order import Order as OrderSchema
from app.core.security import get_current_active_user
from app.models.user import User

router = APIRouter()


@router.get("/", response_model=List[OrderSchema])
async def get_orders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    external_source: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve orders with optional filtering.
    """
    # Base query
    query = select(Order)

    # Apply filters
    conditions = []
    if status:
        conditions.append(Order.status == status)
    if external_source:
        conditions.append(Order.external_source == external_source)
    if start_date:
        conditions.append(Order.order_date >= start_date)
    if end_date:
        # Include the entire end date
        conditions.append(Order.order_date <= end_date + timedelta(days=1))

    if conditions:
        query = query.where(and_(*conditions))

    # Apply pagination
    query = query.offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query)
    orders = result.scalars().all()

    return orders


@router.get("/{order_id}", response_model=OrderSchema)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a specific order by ID.
    """
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get("/sync/status")
async def get_sync_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get the status of the last order sync.
    """
    # Get the most recent order to determine last sync time
    result = await db.execute(select(Order).order_by(Order.created_at.desc()).limit(1))
    last_order = result.scalars().first()

    # Get total count of orders
    count_result = await db.execute(select(func.count()).select_from(Order))
    total_orders = count_result.scalar() or 0

    return {
        "last_sync_time": last_order.created_at if last_order else None,
        "total_orders": total_orders,
        "status": "success",
    }
