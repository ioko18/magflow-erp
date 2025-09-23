from __future__ import annotations

import base64
import json
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi_limiter.depends import RateLimiter
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..cache.redis import CacheManager
from ..core.config import settings
from ..db import get_db
from ..schemas.product import ProductResponse

# Response models are defined in the function signatures

router = APIRouter(prefix="/products", tags=["products"])

# Rate limit configuration
rate_limit = RateLimiter(
    times=settings.rate_limit.split()[0],
    seconds=int(settings.rate_limit.split()[2]),
)


def decode_cursor(cursor: Optional[str]) -> Optional[Dict[str, Any]]:
    """Decode base64-encoded cursor to dictionary."""
    if not cursor:
        return None
    try:
        return json.loads(base64.b64decode(cursor.encode()).decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid cursor format")


def encode_cursor(cursor_data: Dict[str, Any]) -> str:
    """Encode cursor dictionary to base64 string."""
    return base64.b64encode(json.dumps(cursor_data).encode()).decode()


def get_products_with_cursor(
    db: Session,
    limit: int,
    cursor: Optional[str] = None,
    search_query: Optional[str] = None,
    before: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str], Optional[str], bool]:
    """Get products with cursor-based pagination using composite index.

    Args:
        db: Database session
        limit: Maximum number of items to return
        cursor: Base64-encoded cursor string for forward pagination
        before: Base64-encoded cursor string for backward pagination
        search_query: Optional search query for product names

    Returns:
        Tuple of (products, next_cursor, prev_cursor, has_more)

    """
    if cursor and before:
        raise HTTPException(
            status_code=400,
            detail="Cannot specify both 'after' and 'before' cursors",
        )

    cursor_data = decode_cursor(cursor) if cursor else None
    before_data = decode_cursor(before) if before else None

    # Base query with required fields
    query = """
        SELECT p.id, p.name, p.price, p.created_at,
               COALESCE(array_agg(DISTINCT c.name) FILTER (WHERE c.name IS NOT NULL), '{}') as categories
        FROM app.products p
        LEFT JOIN app.product_categories pc ON p.id = pc.product_id
        LEFT JOIN app.categories c ON pc.category_id = c.id
    """

    # Build WHERE clause
    where_clauses = []
    params = {"limit": limit + 1}  # Fetch one extra to check if there are more

    if cursor_data:
        # Forward pagination: get items after the cursor
        where_clauses.append("(p.created_at, p.id) < (:cursor_created_at, :cursor_id)")
        params.update(
            {
                "cursor_created_at": cursor_data["created_at"],
                "cursor_id": cursor_data["id"],
            },
        )
    elif before_data:
        # Backward pagination: get items before the cursor
        where_clauses.append("(p.created_at, p.id) > (:before_created_at, :before_id)")
        params.update(
            {
                "before_created_at": before_data["created_at"],
                "before_id": before_data["id"],
            },
        )

    if search_query:
        where_clauses.append("p.name ILIKE :search_pattern")
        params["search_pattern"] = f"%{search_query}%"

    # Add WHERE clause if needed
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    # Add GROUP BY and ORDER BY
    query += """
        GROUP BY p.id, p.name, p.price, p.created_at
    """

    # For backward pagination, we need to reverse the order and then reverse the results
    if before_data:
        query += """
            ORDER BY p.created_at ASC, p.id ASC
            LIMIT :limit
        """
    else:
        query += """
            ORDER BY p.created_at DESC, p.id DESC
            LIMIT :limit
        """

    # Execute query
    result = db.execute(text(query), params)
    rows = result.fetchall()

    # For backward pagination, reverse the results to maintain consistent order
    if before_data:
        rows = list(reversed(rows))

    # Process results
    products = []
    for row in rows:
        products.append(
            {
                "id": row.id,
                "name": row.name,
                "price": row.price,
                "created_at": row.created_at,
                "categories": row.categories,
            },
        )

    # Check if there are more items
    has_more = len(products) > limit
    if has_more:
        products = products[:-1]  # Remove the extra item

    # Generate cursors
    next_cursor = None
    prev_cursor = None

    if has_more and products:
        last_item = products[-1]
        next_cursor = encode_cursor(
            {"created_at": last_item["created_at"].isoformat(), "id": last_item["id"]},
        )

    if products:
        first_item = products[0]
        prev_cursor = encode_cursor(
            {
                "created_at": first_item["created_at"].isoformat(),
                "id": first_item["id"],
            },
        )

    return products, next_cursor, prev_cursor, has_more


@router.get("", response_model=Dict[str, Any])
@router.get("/", response_model=Dict[str, Any], include_in_schema=False)
async def list_products(
    request: Request,
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Maximum number of items to return",
    ),
    after: Optional[str] = Query(
        None,
        description="Cursor for forward pagination (next page)",
    ),
    before: Optional[str] = Query(
        None,
        description="Cursor for backward pagination (previous page)",
    ),
    q: Optional[str] = Query(None, description="Search query for product names"),
    db: Session = Depends(get_db),
):
    """List products with cursor-based pagination.

    This endpoint uses keyset pagination for better performance with large datasets.
    Use the `after` cursor to fetch the next page or `before` to fetch the previous page.
    """
    try:
        # Get products with cursor-based pagination
        products, next_cursor, prev_cursor, has_more = get_products_with_cursor(
            db=db,
            limit=limit,
            cursor=after,
            before=before,
            search_query=q,
        )

        # Build response with pagination metadata
        return {
            "data": [
                ProductResponse(
                    id=p["id"],
                    name=p["name"],
                    price=p["price"],
                    categories=p["categories"],
                )
                for p in products
            ],
            "pagination": {
                "next": next_cursor,
                "prev": prev_cursor,
                "has_more": has_more,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching products: {e!s}",
        )
    return {
        "data": [
            ProductResponse(
                id=p["id"],
                name=p["name"],
                price=p["price"],
                categories=p["categories"],
            )
            for p in products
        ],
        "pagination": {"next": next_cursor, "prev": prev_cursor, "has_more": has_more},
    }


# Keep existing endpoints for product CRUD operations
@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(request: Request, product_id: int, db: Session = Depends(get_db)):
    # Apply rate limiting
    await rate_limit(request)

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

    # Cache the response for 60 seconds
    response = ProductResponse(**product)
    await CacheManager.set_json(cache_key, response.dict(), ttl=60)

    return response


def get_product_with_categories(db: Session, product_id: int):
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
