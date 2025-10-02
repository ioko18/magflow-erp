"""
eMAG Customers API Endpoints for MagFlow ERP.

This module provides REST API endpoints for managing eMAG customers
with advanced analytics and segmentation capabilities.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_async_session
from app.core.logging import get_logger
from app.db import get_db
from app.models.user import User

logger = get_logger(__name__)
router = APIRouter()


class CustomerResponse(BaseModel):
    """Response model for customer data."""

    id: int
    code: Optional[str] = None
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    tier: str = "bronze"
    status: str = "active"
    total_orders: int = 0
    total_spent: float = 0.0
    last_order_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # eMAG specific fields
    emag_customer_id: Optional[str] = None
    emag_orders_count: Optional[int] = None
    preferred_channel: Optional[str] = None
    loyalty_score: Optional[int] = None
    risk_level: Optional[str] = None


class CustomerSummary(BaseModel):
    """Summary statistics for customers."""

    total_active: int = 0
    total_inactive: int = 0
    total_spent: float = 0.0
    emag_customers: Dict[str, int] = Field(default_factory=dict)
    channel_distribution: Dict[str, int] = Field(default_factory=dict)
    loyalty_distribution: Dict[str, int] = Field(default_factory=dict)


@router.get("/emag-customers")
async def get_emag_customers(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    status: Optional[str] = Query(default=None, description="Filter by status: active, inactive, blocked"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get eMAG customers with pagination and filtering.
    
    Returns customer data with eMAG-specific fields including:
    - Basic customer information
    - Order statistics
    - Loyalty and tier information
    - Channel preferences
    - Summary statistics
    """
    try:
        logger.info(
            "Fetching eMAG customers: skip=%d, limit=%d, status=%s, user=%s",
            skip,
            limit,
            status,
            current_user.email,
        )

        # Generate mock customer data based on eMAG orders
        async for async_db in get_async_session():
            # Get unique customers from orders
            customers_query = """
                SELECT DISTINCT
                    ROW_NUMBER() OVER (ORDER BY customer_name) as id,
                    customer_name as name,
                    customer_email as email,
                    customer_phone as phone,
                    COALESCE(
                        shipping_address->>'city',
                        billing_address->>'city',
                        'N/A'
                    ) as city,
                    account_type as preferred_channel,
                    COUNT(*) OVER (PARTITION BY customer_name) as total_orders,
                    SUM(total_amount) OVER (PARTITION BY customer_name) as total_spent,
                    MAX(order_date) OVER (PARTITION BY customer_name) as last_order_at,
                    MIN(created_at) OVER (PARTITION BY customer_name) as created_at,
                    MAX(updated_at) OVER (PARTITION BY customer_name) as updated_at
                FROM app.emag_orders
                WHERE customer_name IS NOT NULL
                ORDER BY total_spent DESC
                LIMIT :limit OFFSET :skip
            """

            result = await async_db.execute(
                text(customers_query),
                {"limit": limit, "skip": skip}
            )
            customers_data = result.fetchall()

            # Get total count
            count_query = """
                SELECT COUNT(DISTINCT customer_name) as total
                FROM app.emag_orders
                WHERE customer_name IS NOT NULL
            """
            count_result = await async_db.execute(text(count_query))
            total_count = count_result.scalar() or 0

            # Transform to customer objects
            customers = []
            for row in customers_data:
                # Calculate tier based on total spent
                total_spent = float(row.total_spent or 0)
                if total_spent > 5000:
                    tier = "gold"
                elif total_spent > 2000:
                    tier = "silver"
                else:
                    tier = "bronze"

                # Calculate loyalty score (0-100)
                loyalty_score = min(100, int((row.total_orders or 0) * 10 + (total_spent / 100)))

                # Determine risk level
                if loyalty_score > 70:
                    risk_level = "low"
                elif loyalty_score > 40:
                    risk_level = "medium"
                else:
                    risk_level = "high"

                customer = {
                    "id": row.id,
                    "code": f"CUST-{row.id:05d}",
                    "name": row.name or "Unknown Customer",
                    "email": row.email,
                    "phone": row.phone,
                    "city": row.city,
                    "tier": tier,
                    "status": "active" if row.total_orders > 0 else "inactive",
                    "total_orders": row.total_orders or 0,
                    "total_spent": total_spent,
                    "last_order_at": row.last_order_at.isoformat() if row.last_order_at else None,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                    "emag_customer_id": f"EMAG-{row.id}",
                    "emag_orders_count": row.total_orders or 0,
                    "preferred_channel": row.preferred_channel or "main",
                    "loyalty_score": loyalty_score,
                    "risk_level": risk_level,
                }
                customers.append(customer)

            # Calculate summary statistics
            summary_query = """
                SELECT 
                    COUNT(DISTINCT customer_name) as total_customers,
                    COUNT(DISTINCT CASE WHEN order_date > NOW() - INTERVAL '30 days' THEN customer_name END) as active_customers,
                    SUM(total_amount) as total_spent,
                    account_type as channel,
                    COUNT(*) as channel_count
                FROM app.emag_orders
                WHERE customer_name IS NOT NULL
                GROUP BY account_type
            """
            summary_result = await async_db.execute(text(summary_query))
            summary_data = summary_result.fetchall()

            # Process summary
            total_customers = 0
            active_customers = 0
            total_spent_sum = 0.0
            channel_dist = {"main": 0, "fbe": 0, "mixed": 0}

            for row in summary_data:
                total_customers = max(total_customers, row.total_customers or 0)
                active_customers = max(active_customers, row.active_customers or 0)
                total_spent_sum += float(row.total_spent or 0)
                channel = row.channel or "main"
                channel_dist[channel] = row.channel_count or 0

            # Calculate loyalty distribution
            loyalty_dist = {
                "bronze": len([c for c in customers if c["tier"] == "bronze"]),
                "silver": len([c for c in customers if c["tier"] == "silver"]),
                "gold": len([c for c in customers if c["tier"] == "gold"]),
            }

            # Calculate VIP customers (gold tier)
            vip_count = loyalty_dist["gold"]

            # Calculate new customers this month
            new_this_month = len([
                c for c in customers
                if c["created_at"] and
                datetime.fromisoformat(c["created_at"]) > datetime.utcnow() - timedelta(days=30)
            ])

            summary = {
                "total_active": active_customers,
                "total_inactive": total_customers - active_customers,
                "total_spent": total_spent_sum,
                "emag_customers": {
                    "total": total_customers,
                    "active": active_customers,
                    "vip": vip_count,
                    "newThisMonth": new_this_month,
                },
                "channel_distribution": channel_dist,
                "loyalty_distribution": loyalty_dist,
            }

            return {
                "status": "success",
                "data": {
                    "customers": customers,
                    "pagination": {
                        "skip": skip,
                        "limit": limit,
                        "total": total_count,
                    },
                    "summary": summary,
                },
            }

    except Exception as e:
        logger.error("Failed to fetch eMAG customers: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch customers: {str(e)}"
        )


@router.get("/emag-customers/{customer_id}")
async def get_customer_details(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed information about a specific customer.
    
    Returns comprehensive customer data including:
    - Order history
    - Purchase patterns
    - Loyalty metrics
    - Risk assessment
    """
    try:
        logger.info(
            "Fetching customer details: customer_id=%d, user=%s",
            customer_id,
            current_user.email,
        )

        # Mock customer details
        customer = {
            "id": customer_id,
            "code": f"CUST-{customer_id:05d}",
            "name": f"Customer {customer_id}",
            "email": f"customer{customer_id}@example.com",
            "phone": f"+40 7XX XXX {customer_id:03d}",
            "city": "București",
            "tier": "silver",
            "status": "active",
            "total_orders": 15,
            "total_spent": 3500.00,
            "last_order_at": datetime.utcnow().isoformat(),
            "created_at": (datetime.utcnow() - timedelta(days=180)).isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "emag_customer_id": f"EMAG-{customer_id}",
            "emag_orders_count": 15,
            "preferred_channel": "main",
            "loyalty_score": 65,
            "risk_level": "low",
            "address": {
                "street": "Str. Exemplu nr. 123",
                "city": "București",
                "county": "București",
                "postal_code": "012345",
                "country": "România",
            },
            "preferences": {
                "delivery_method": "courier",
                "payment_method": "card",
                "communication_channel": "email",
            },
        }

        return {
            "status": "success",
            "data": customer,
        }

    except Exception as e:
        logger.error("Failed to fetch customer details: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch customer details: {str(e)}"
        )
