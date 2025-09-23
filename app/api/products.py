from __future__ import annotations

import base64
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..cache.redis import CacheManager
from ..core.config import settings
from ..db import get_db
from ..schemas.product import ProductCreate, ProductResponse, ProductUpdate

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])

# Rate limit configuration
rate_limit = RateLimiter(
    times=settings.rate_limit.split()[0],
    seconds=int(settings.rate_limit.split()[2]),
)


# Cursor pagination models
class CursorPagination(BaseModel):
    items: List[Dict[str, Any]]
    next_cursor: Optional[str] = None
    has_more: bool = False
    total: Optional[int] = None


# Cursor encoding/decoding
def encode_cursor(created_at: datetime, id: int) -> str:
    cursor_data = {"created_at": created_at.isoformat(), "id": id}
    return base64.b64encode(json.dumps(cursor_data).encode()).decode()


def decode_cursor(cursor: str) -> Dict[str, Any]:
    try:
        data = json.loads(base64.b64decode(cursor.encode()).decode())
        return {
            "created_at": datetime.fromisoformat(data["created_at"]),
            "id": data["id"],
        }
    except (json.JSONDecodeError, UnicodeDecodeError, KeyError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid cursor format")


def get_product_with_categories(db: AsyncSession, product_id: int):
    """Get product with associated categories"""
    query = text(
        """
        SELECT p.id, p.name, p.price, p.created_at,
               COALESCE(array_agg(c.name) FILTER (WHERE c.name IS NOT NULL), '{}') as categories
        FROM app.products p
        LEFT JOIN app.product_categories pc ON p.id = pc.product_id
        LEFT JOIN app.categories c ON pc.category_id = c.id
        WHERE p.id = :product_id
        GROUP BY p.id, p.name, p.price, p.created_at
    """,
    )
    result = db.execute(query, {"product_id": product_id}).fetchone()
    if not result:
        return None

    return {
        "id": result.id,
        "name": result.name,
        "price": result.price,
        "created_at": result.created_at,
        "categories": result.categories or [],
    }


def _decode_cursor(cursor: Optional[str]) -> Optional[Dict[str, Any]]:
    """Decode base64-encoded cursor to dictionary."""
    if not cursor:
        return None
    try:
        data = json.loads(base64.b64decode(cursor.encode()).decode())
        return {
            "created_at": datetime.fromisoformat(data["created_at"]),
            "id": data["id"],
        }
    except (json.JSONDecodeError, UnicodeDecodeError, KeyError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid cursor format")


def get_products_with_cursor(
    db: AsyncSession,
    limit: int,
    after: Optional[str] = None,
    before: Optional[str] = None,
    search_query: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str], Optional[str], bool]:
    """Fetch products with cursor-based pagination using composite index.

    Args:
        db: Database session
        limit: Maximum number of items to return
        after: Base64-encoded cursor for forward pagination
        before: Base64-encoded cursor for backward pagination
        search_query: Optional search term

    Returns:
        Tuple of (products, next_cursor, prev_cursor, has_more)

    """
    if after and before:
        raise HTTPException(
            status_code=400,
            detail="Cannot specify both 'after' and 'before' cursors",
        )

    # Base query with categories as array
    query = """
        SELECT p.id, p.name, p.price, p.created_at,
               COALESCE(array_agg(c.name) FILTER (WHERE c.name IS NOT NULL), '{}') as categories
        FROM app.products p
        LEFT JOIN app.product_categories pc ON p.id = pc.product_id
        LEFT JOIN app.categories c ON pc.category_id = c.id
    """

    # Build WHERE conditions
    conditions = []
    params = {}
    order_direction = "DESC"

    # Handle forward pagination (after cursor)
    if after:
        cursor_data = _decode_cursor(after)
        conditions.append("(p.created_at, p.id) < (:cursor_created_at, :cursor_id)")
        params.update(
            {
                "cursor_created_at": cursor_data["created_at"],
                "cursor_id": cursor_data["id"],
            },
        )
    # Handle backward pagination (before cursor)
    elif before:
        cursor_data = _decode_cursor(before)
        conditions.append("(p.created_at, p.id) > (:cursor_created_at, :cursor_id)")
        params.update(
            {
                "cursor_created_at": cursor_data["created_at"],
                "cursor_id": cursor_data["id"],
            },
        )
        order_direction = "ASC"  # Reverse order for backward pagination

    # Add search condition if provided
    if search_query:
        conditions.append("p.name ILIKE :search_pattern")
        params["search_pattern"] = f"%{search_query}%"

    # Add WHERE clause if we have conditions
    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    # Group by product fields for the array_agg
    query += f"""
        GROUP BY p.id, p.name, p.price, p.created_at
        ORDER BY p.created_at {order_direction}, p.id {order_direction}
        LIMIT :limit
    """

    # Add 1 to limit to check if there are more items
    params["limit"] = limit + 1

    # Execute query
    result = db.execute(text(query), params)
    rows = result.fetchall()

    # For backward pagination, we need to reverse the results after fetching
    if before:
        rows = list(reversed(rows))

    # Check if we have more items
    has_more = len(rows) > limit
    rows = rows[:limit]  # Return only the requested number of items

    # Format results
    products = []
    for row in rows:
        products.append(
            {
                "id": row.id,
                "name": row.name,
                "price": row.price,
                "created_at": row.created_at,
                "categories": row.categories or [],
            },
        )

    # Generate next and previous cursors
    next_cursor = None
    prev_cursor = None

    if rows:
        if (
            has_more or before
        ):  # Only set next_cursor if there are more items or we're in backward pagination
            last_row = rows[-1]
            next_cursor = encode_cursor(last_row.created_at, last_row.id)

        # Set previous cursor for backward pagination
        if after or (before and len(rows) > 0):
            first_row = rows[0]
            prev_cursor = encode_cursor(first_row.created_at, first_row.id)

    return products, next_cursor, prev_cursor, has_more


@router.get("", response_model=CursorPagination)
@router.get("/", response_model=CursorPagination, include_in_schema=False)
async def list_products(
    request: Request,
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Maximum number of items to return",
    ),
    after: Optional[str] = Query(None, description="Cursor for forward pagination"),
    before: Optional[str] = Query(None, description="Cursor for backward pagination"),
    q: Optional[str] = Query(None, description="Search query for product names"),
    db: AsyncSession = Depends(get_db),
):
    """List products with cursor-based pagination.

    This endpoint uses keyset pagination for better performance with large datasets.
    Use the `after` cursor to fetch the next page of results or `before` to fetch the previous page.
    """
    try:
        # Get products with cursor-based pagination
        products, next_cursor, prev_cursor, has_more = get_products_with_cursor(
            db=db,
            limit=limit,
            after=after,
            before=before,
            search_query=q,
        )

        # Build response
        response = {
            "items": products,
            "next_cursor": next_cursor,
            "prev_cursor": prev_cursor,
            "has_more": has_more,
            "total": None,  # Total count is not provided for performance reasons
        }

        return response

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error listing products")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list products",
        )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    request: Request,
    product_id: int,
    db: AsyncSession = Depends(get_db),
):
    # Apply rate limiting
    response = None
    await rate_limit(request, response)

    # Generate cache key
    cache_key = f"products:detail:{product_id}"

    # Try to get from cache
    cached = await CacheManager.get_json(cache_key)
    if cached is not None:
        return ProductResponse(**cached)

    # Cache miss, fetch from database
    product = get_product_with_categories(db, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Prepare response
    response = ProductResponse(**product)

    # Cache the response for 60 seconds
    await CacheManager.set_json(cache_key, response.dict(), ttl=60)

    return response


@router.post("", response_model=ProductResponse, status_code=201)
@router.post(
    "/",
    response_model=ProductResponse,
    status_code=201,
    include_in_schema=False,
)
async def create_product(
    request: Request,
    product: ProductCreate,
    db: AsyncSession = Depends(get_db),
):
    # Apply rate limiting
    response = None
    await rate_limit(request, response)

    # Check if product with same name already exists
    existing = db.execute(
        text("SELECT id FROM app.products WHERE name = :name"),
        {"name": product.name},
    ).fetchone()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this name already exists",
        )

    # Start a transaction
    try:
        # Insert new product
        result = db.execute(
            text(
                """
                INSERT INTO app.products (name, price, description)
                VALUES (:name, :price, :description)
                RETURNING id, name, price, description, created_at, updated_at
            """,
            ),
            product.dict(),
        ).fetchone()

        # Insert categories if any
        if product.categories:
            db.execute(
                text(
                    """
                    INSERT INTO app.product_categories (product_id, category_id)
                    SELECT :product_id, id FROM app.categories
                    WHERE name = ANY(:categories)
                """,
                ),
                {"product_id": result.id, "categories": product.categories},
            )

        # Invalidate relevant caches
        await CacheManager.invalidate_prefix("products:list")

        db.commit()

        # Get the full product with categories
        created_product = get_product_with_categories(db, result.id)

        # Cache the new product
        cache_key = f"products:detail:{result.id}"
        response = ProductResponse(**created_product)
        await CacheManager.set_json(cache_key, response.dict(), ttl=60)

        return response

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create product",
        )


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    request: Request,
    product_id: int,
    product_update: ProductUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing product.

    This endpoint updates a product with the provided ID. Only the fields that are provided
    in the request body will be updated.
    """
    try:
        # Apply rate limiting
        response = None
        await rate_limit(request, response)

        # Get existing product
        existing = get_product_with_categories(db, product_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )

        # Update fields if they are provided in the request
        update_data = product_update.dict(exclude_unset=True)

        # Check if name is being updated and if it already exists
        if "name" in update_data and update_data["name"] != existing["name"]:
            name_exists = db.execute(
                text("SELECT 1 FROM app.products WHERE name = :name AND id != :id"),
                {"name": update_data["name"], "id": product_id},
            ).scalar()
            if name_exists:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A product with this name already exists",
                )

        # Update product in database
        update_query = """
            UPDATE app.products
            SET name = COALESCE(:name, name),
                price = COALESCE(:price, price),
                updated_at = now()
            WHERE id = :id
            RETURNING id, name, price, created_at
        """

        result = db.execute(
            text(update_query),
            {
                "id": product_id,
                "name": update_data.get("name"),
                "price": update_data.get("price"),
            },
        )

        result.fetchone()  # We don't use this directly, but need to fetch to complete the query
        db.commit()

        # Get updated product with categories
        updated = get_product_with_categories(db, product_id)

        # Invalidate cache
        cache_key = f"products:detail:{product_id}"
        await CacheManager.delete(cache_key)

        return ProductResponse(**updated)

    except HTTPException:
        raise
    except Exception:
        db.rollback()
        logger.exception("Error updating product")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update product",
        )
