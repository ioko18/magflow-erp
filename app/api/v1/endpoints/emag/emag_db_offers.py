"""Read-only endpoints to browse eMAG offers and products from the local DB.

Routes under: /api/v1/emag/db
- GET /offers
- GET /products

These endpoints do NOT call the eMAG API. They read from tables:
- app.emag_product_offers
- app.emag_products
and the convenience view:
- app.v_emag_offers
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user
from app.core.database import get_async_session
from app.models.emag_offers import EmagProduct, EmagProductOffer

router = APIRouter(tags=["emag-db"])


# Use the standard get_async_session dependency directly
# No need for a wrapper since we're importing from the correct location


@router.get("/offers")
async def list_offers(
    account_type: str | None = Query(
        None, pattern="^(main|fbe)$", description="Filter by account type"
    ),
    search: str | None = Query(None, description="Filter by product name (ILIKE)"),
    min_price: float | None = Query(None, ge=0, description="Minimum sale_price"),
    max_price: float | None = Query(None, ge=0, description="Maximum sale_price"),
    stock_gt: int | None = Query(
        None, ge=0, description="Stock strictly greater than value"
    ),
    only_available: bool = Query(
        False, description="Only offers where is_available is true"
    ),
    sort_by: str = Query(
        "updated_at", description="Sort field: updated_at|sale_price|stock"
    ),
    order: str = Query(
        "desc", pattern="^(asc|desc)$", description="Sort order: asc|desc"
    ),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_active_user),
) -> dict[str, Any]:
    """List offers from the local database with optional filters and pagination.

    Uses SQLAlchemy ORM with join to EmagProduct for safe, parameterized queries.
    """
    try:
        # Build filters using SQLAlchemy ORM - completely safe from SQL injection
        filters = []

        if account_type:
            filters.append(EmagProductOffer.account_type == account_type)

        if search:
            # Join with EmagProduct to search by product name
            filters.append(func.lower(EmagProduct.name).like(func.lower(f"%{search}%")))

        if min_price is not None:
            filters.append(EmagProductOffer.sale_price >= min_price)

        if max_price is not None:
            filters.append(EmagProductOffer.sale_price <= max_price)

        if stock_gt is not None:
            filters.append(EmagProductOffer.stock > stock_gt)

        if only_available:
            filters.append(EmagProductOffer.is_available == True)  # noqa: E712

        # Validate sort field against whitelist
        allowed_sorts = {"updated_at": EmagProductOffer.updated_at,
                        "sale_price": EmagProductOffer.sale_price,
                        "stock": EmagProductOffer.stock}
        sort_column = allowed_sorts.get(sort_by, EmagProductOffer.updated_at)

        # Apply sort direction
        if order.lower() == "asc":
            sort_column = sort_column.asc().nullslast()
        else:
            sort_column = sort_column.desc().nullslast()

        offset = (page - 1) * limit

        # Build query with join to get product name
        query = (
            select(
                EmagProductOffer.emag_offer_id,
                EmagProductOffer.emag_product_id,
                EmagProduct.name.label("product_name"),
                EmagProductOffer.currency,
                EmagProductOffer.sale_price,
                EmagProductOffer.stock,
                EmagProductOffer.is_available,
                EmagProductOffer.account_type,
                EmagProductOffer.updated_at,
            )
            .join(EmagProduct, EmagProductOffer.product_id == EmagProduct.id, isouter=True)
            .where(and_(*filters) if filters else True)
            .order_by(sort_column)
            .limit(limit)
            .offset(offset)
        )

        # Count query
        count_query = (
            select(func.count(EmagProductOffer.id))
            .join(EmagProduct, EmagProductOffer.product_id == EmagProduct.id, isouter=True)
            .where(and_(*filters) if filters else True)
        )

        result = await db.execute(query)
        items = [dict(row._mapping) for row in result.fetchall()]

        total = (await db.execute(count_query)).scalar() or 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


@router.get("/products")
async def list_products(
    search: str | None = Query(None, description="Filter by product name (ILIKE)"),
    is_active: bool | None = Query(
        None, description="Filter by visibility/active flag"
    ),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(get_current_active_user),
) -> dict[str, Any]:
    """List products from the local database with optional filters and pagination.

    Uses SQLAlchemy ORM for safe, parameterized queries.
    """
    try:
        # Build filters using SQLAlchemy ORM - completely safe from SQL injection
        filters = []

        if search:
            filters.append(func.lower(EmagProduct.name).like(func.lower(f"%{search}%")))

        if is_active is not None:
            filters.append(EmagProduct.is_active == is_active)

        offset = (page - 1) * limit

        # Build query using SQLAlchemy ORM
        query = (
            select(
                EmagProduct.emag_id,
                EmagProduct.name,
                EmagProduct.is_active,
                EmagProduct.updated_at,
            )
            .where(and_(*filters) if filters else True)
            .order_by(EmagProduct.updated_at.desc().nullslast())
            .limit(limit)
            .offset(offset)
        )

        # Count query
        count_query = (
            select(func.count(EmagProduct.id))
            .where(and_(*filters) if filters else True)
        )

        result = await db.execute(query)
        items = [dict(row._mapping) for row in result.fetchall()]

        total = (await db.execute(count_query)).scalar() or 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e
