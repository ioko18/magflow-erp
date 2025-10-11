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
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user
from app.core.database import get_async_session

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
    """List offers from the local database with optional filters and pagination."""
    try:
        where_clauses = []
        params: dict[str, Any] = {}
        if account_type:
            where_clauses.append("account_type = :account_type")
            params["account_type"] = account_type
        if search:
            where_clauses.append("LOWER(product_name) LIKE LOWER(:search)")
            params["search"] = f"%{search}%"
        if min_price is not None:
            where_clauses.append("sale_price >= :min_price")
            params["min_price"] = min_price
        if max_price is not None:
            where_clauses.append("sale_price <= :max_price")
            params["max_price"] = max_price
        if stock_gt is not None:
            where_clauses.append("stock > :stock_gt")
            params["stock_gt"] = stock_gt
        if only_available:
            where_clauses.append("is_available = true")
        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        offset = (page - 1) * limit

        # Validate and build ORDER BY safely
        allowed_sorts = {"updated_at", "sale_price", "stock"}
        sort_field = sort_by if sort_by in allowed_sorts else "updated_at"
        sort_dir = "ASC" if order.lower() == "asc" else "DESC"

        # Use the convenience view for the data
        # nosec B608 - sort_field and sort_dir are validated against whitelist above
        rows_sql = text(  # noqa: S608
            f"""
            SELECT emag_offer_id, emag_product_id, product_name, currency,
                   sale_price, stock, is_available, account_type, updated_at
            FROM app.v_emag_offers
            {where_sql}
            ORDER BY {sort_field} {sort_dir} NULLS LAST
            LIMIT :limit OFFSET :offset
            """,
        )
        params.update({"limit": limit, "offset": offset})

        # Use base table for count (same filters)
        # Count using the same view with identical filters
        count_sql = text(
            f"""
            SELECT COUNT(*)
            FROM app.v_emag_offers
            {where_sql}
            """,
        )

        result = await db.execute(rows_sql, params)
        items = [dict(r._mapping) for r in result.fetchall()]

        total = (await db.execute(count_sql, params)).scalar() or 0
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
        )


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
    """List products from the local database with optional filters and pagination."""
    try:
        where = []
        params: dict[str, Any] = {}
        if search:
            where.append("LOWER(name) LIKE LOWER(:search)")
            params["search"] = f"%{search}%"
        if is_active is not None:
            where.append("is_active = :is_active")
            params["is_active"] = is_active
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        offset = (page - 1) * limit
        rows_sql = text(
            f"""
            SELECT emag_id, name, is_active, updated_at
            FROM app.emag_products
            {where_sql}
            ORDER BY updated_at DESC NULLS LAST
            LIMIT :limit OFFSET :offset
            """,
        )
        params.update({"limit": limit, "offset": offset})

        count_sql = text(
            f"""
            SELECT COUNT(*)
            FROM app.emag_products
            {where_sql}
            """,
        )

        result = await db.execute(rows_sql, params)
        items = [dict(r._mapping) for r in result.fetchall()]
        total = (await db.execute(count_sql, params)).scalar() or 0

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
        )
