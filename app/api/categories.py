from __future__ import annotations

import base64
import json
import logging

# datetime is used in the response models
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from app.core.rate_limiting import RateLimiter
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..services.redis import CacheManager
from ..core.config import settings
from ..db import get_db
from ..schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate

# Response models are defined in the function signatures

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/categories", tags=["categories"])

# Rate limit configuration
rate_limit = RateLimiter(
    times=settings.RATE_LIMIT_DEFAULT.split("/")[0],
    seconds=int(
        settings.RATE_LIMIT_DEFAULT.split("/")[1]
        .replace("minute", "60")
        .replace("second", "1")
    ),
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


def get_categories_with_cursor(
    db: Session,
    limit: int,
    cursor: Optional[str] = None,
    search_query: Optional[str] = None,
    before: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str], Optional[str], bool]:
    """Get categories with cursor-based pagination using composite index.

    Args:
        db: Database session
        limit: Maximum number of items to return
        cursor: Base64-encoded cursor string for forward pagination
        before: Base64-encoded cursor string for backward pagination
        search_query: Optional search query for category names

    Returns:
        Tuple of (categories, next_cursor, prev_cursor, has_more)

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
        SELECT c.id, c.name, c.created_at,
               COALESCE(array_agg(DISTINCT p.name) FILTER (WHERE p.name IS NOT NULL), '{}') as products
        FROM app.categories c
        LEFT JOIN app.product_categories pc ON c.id = pc.category_id
        LEFT JOIN app.products p ON pc.product_id = p.id
    """

    # Build WHERE clause
    where_clauses = []
    params = {"limit": limit + 1}  # Fetch one extra to check if there are more

    if cursor_data:
        # Forward pagination: get items after the cursor
        where_clauses.append("(c.created_at, c.id) < (:cursor_created_at, :cursor_id)")
        params.update(
            {
                "cursor_created_at": cursor_data["created_at"],
                "cursor_id": cursor_data["id"],
            },
        )
    elif before_data:
        # Backward pagination: get items before the cursor
        where_clauses.append("(c.created_at, c.id) > (:before_created_at, :before_id)")
        params.update(
            {
                "before_created_at": before_data["created_at"],
                "before_id": before_data["id"],
            },
        )

    if search_query:
        where_clauses.append("c.name ILIKE :search_pattern")
        params["search_pattern"] = f"%{search_query}%"

    # Add WHERE clause if needed
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    # Add GROUP BY and ORDER BY
    query += """
        GROUP BY c.id, c.name, c.created_at
    """

    # For backward pagination, we need to reverse the order and then reverse the results
    if before_data:
        query += """
            ORDER BY c.created_at ASC, c.id ASC
            LIMIT :limit
        """
    else:
        query += """
            ORDER BY c.created_at DESC, c.id DESC
            LIMIT :limit
        """

    # Execute query
    result = db.execute(text(query), params)
    rows = result.fetchall()

    # For backward pagination, reverse the results to maintain consistent order
    if before_data:
        rows = list(reversed(rows))

    # Process results
    categories = []
    for row in rows:
        categories.append(
            {
                "id": row.id,
                "name": row.name,
                "created_at": row.created_at,
                "products": row.products,
            },
        )

    # Check if there are more items
    has_more = len(categories) > limit
    if has_more:
        categories = categories[:-1]  # Remove the extra item

    # Generate cursors
    next_cursor = None
    prev_cursor = None

    if has_more and categories:
        last_item = categories[-1]
        next_cursor = encode_cursor(
            {"created_at": last_item["created_at"].isoformat(), "id": last_item["id"]},
        )

    if categories:
        first_item = categories[0]
        prev_cursor = encode_cursor(
            {
                "created_at": first_item["created_at"].isoformat(),
                "id": first_item["id"],
            },
        )

    return categories, next_cursor, prev_cursor, has_more


@router.get("", response_model=Dict[str, Any])
@router.get("/", response_model=Dict[str, Any], include_in_schema=False)
async def list_categories(
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
    q: Optional[str] = Query(None, description="Search query for category names"),
    db: Session = Depends(get_db),
):
    """List categories with cursor-based pagination.

    This endpoint uses keyset pagination for better performance with large datasets.
    Use the `after` cursor to fetch the next page or `before` to fetch the previous page.
    """
    try:
        # Get categories with cursor-based pagination
        categories, next_cursor, prev_cursor, has_more = get_categories_with_cursor(
            db=db,
            limit=limit,
            cursor=after,
            before=before,
            search_query=q,
        )

        # Build response with pagination metadata
        return {
            "data": [
                CategoryResponse(id=c["id"], name=c["name"], products=c["products"])
                for c in categories
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
        logger.error(f"Error fetching categories: {e!s}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching categories: {e!s}",
        )


# Keep existing endpoints for category CRUD operations
@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    request: Request,
    category_id: int,
    db: Session = Depends(get_db),
):
    # Apply rate limiting
    await rate_limit(request)

    # Generate cache key
    cache_key = f"categories:detail:{category_id}"

    # Try to get from cache
    cached = await CacheManager.get_json(cache_key)
    if cached is not None:
        return CategoryResponse(**cached)

    # Cache miss, fetch from database
    query = text(
        """
        SELECT id, name, created_at
        FROM app.categories
        WHERE id = :category_id
    """,
    )
    result = db.execute(query, {"category_id": category_id}).first()

    if not result:
        raise HTTPException(status_code=404, detail="Category not found")

    # Prepare response
    response = CategoryResponse(id=result.id, name=result.name)

    # Cache the response for 60 seconds
    await CacheManager.set_json(cache_key, response.dict(), ttl=60)

    return response


@router.post("", response_model=CategoryResponse, status_code=201)
@router.post(
    "/",
    response_model=CategoryResponse,
    status_code=201,
    include_in_schema=False,
)
async def create_category(
    request: Request,
    category: CategoryCreate,
    db: Session = Depends(get_db),
):
    # Apply rate limiting with stricter limits for write operations
    await RateLimiter(times=5, seconds=10)(request)

    try:
        insert_query = text(
            """
            INSERT INTO app.categories (name)
            VALUES (:name)
            RETURNING id, name, created_at
        """,
        )
        result = db.execute(insert_query, {"name": category.name})
        created_category = result.fetchone()
        db.commit()

        # Invalidate relevant caches
        await CacheManager.delete_matching("categories:list:*")

        return CategoryResponse(id=created_category.id, name=created_category.name)

    except Exception as e:
        db.rollback()
        # Check if it's a unique constraint violation
        if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
            raise HTTPException(status_code=400, detail="Category name already exists")
        logger.error(f"Failed to create category: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to create category")


@router.put("/{category_id}", response_model=CategoryResponse)
@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    request: Request,
    category_id: int,
    category_update: CategoryUpdate,
    db: Session = Depends(get_db),
):
    # Apply rate limiting with stricter limits for write operations
    await RateLimiter(times=5, seconds=10)(request)

    # Check if category exists
    existing_query = text(
        """
        SELECT id, name, created_at
        FROM app.categories
        WHERE id = :category_id
    """,
    )
    existing = db.execute(existing_query, {"category_id": category_id}).first()

    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")

    if category_update.name is None:
        # No fields to update, return existing category
        return CategoryResponse(id=existing.id, name=existing.name)

    try:
        update_query = text(
            """
            UPDATE app.categories
            SET name = :name
            WHERE id = :category_id
            RETURNING id, name, created_at
        """,
        )

        result = db.execute(
            update_query,
            {"name": category_update.name, "category_id": category_id},
        )
        updated_category = result.fetchone()
        db.commit()

        # Invalidate caches
        await CacheManager.delete_matching("categories:list:*")
        await CacheManager.delete(f"categories:detail:{category_id}")

        return CategoryResponse(id=updated_category.id, name=updated_category.name)

    except Exception as e:
        db.rollback()
        # Check if it's a unique constraint violation
        if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
            raise HTTPException(status_code=400, detail="Category name already exists")
        logger.error(f"Failed to update category {category_id}: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to update category")


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    request: Request,
    category_id: int,
    db: Session = Depends(get_db),
):
    # Apply rate limiting with stricter limits for delete operations
    await RateLimiter(times=2, seconds=10)(request)

    # Check if category exists
    existing_query = text(
        """
        SELECT id, name, created_at
        FROM app.categories
        WHERE id = :category_id
    """,
    )
    existing = db.execute(existing_query, {"category_id": category_id}).first()

    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")

    try:
        # Delete category (cascade will handle product_categories)
        delete_query = text(
            """
            DELETE FROM app.categories
            WHERE id = :category_id
        """,
        )
        db.execute(delete_query, {"category_id": category_id})
        db.commit()

        # Invalidate caches
        await CacheManager.delete_matching("categories:list:*")
        await CacheManager.delete(f"categories:detail:{category_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete category {category_id}: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to delete category")
