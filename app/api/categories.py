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
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db import get_db
from ..schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/categories", tags=["categories"])

# Rate limit configuration
rate_limit = RateLimiter(
    times=settings.rate_limit.split()[0],
    seconds=int(settings.rate_limit.split()[2]),
)


# Cursor pagination models
class CursorPagination(BaseModel):
    items: List[Dict[str, Any]]
    next_cursor: Optional[str] = None
    prev_cursor: Optional[str] = None
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


def _decode_cursor(cursor: Optional[str]) -> Optional[Dict[str, Any]]:
    if not cursor:
        return None
    try:
        return decode_cursor(cursor)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error decoding cursor: {e!s}")
        raise HTTPException(status_code=400, detail="Invalid cursor format")


async def get_categories_with_cursor(
    db: Session,
    limit: int,
    after: Optional[str] = None,
    before: Optional[str] = None,
    search_query: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str], Optional[str], bool]:
    """Fetch categories with cursor-based pagination using composite index.

    Args:
        db: Database session
        limit: Maximum number of items to return
        after: Base64-encoded cursor for forward pagination
        before: Base64-encoded cursor for backward pagination
        search_query: Optional search term

    Returns:
        Tuple of (categories, next_cursor, prev_cursor, has_more)

    """
    if after and before:
        raise HTTPException(
            status_code=400,
            detail="Cannot specify both 'after' and 'before' cursors",
        )

    # Base query
    query = """
        SELECT id, name, created_at
        FROM app.categories
    """

    # Build WHERE conditions
    conditions = []
    params = {}
    order_direction = "DESC"

    # Handle forward pagination (after cursor)
    if after:
        cursor_data = _decode_cursor(after)
        conditions.append("(created_at, id) < (:cursor_created_at, :cursor_id)")
        params.update(
            {
                "cursor_created_at": cursor_data["created_at"],
                "cursor_id": cursor_data["id"],
            },
        )
    # Handle backward pagination (before cursor)
    elif before:
        cursor_data = _decode_cursor(before)
        conditions.append("(created_at, id) > (:cursor_created_at, :cursor_id)")
        params.update(
            {
                "cursor_created_at": cursor_data["created_at"],
                "cursor_id": cursor_data["id"],
            },
        )
        order_direction = "ASC"  # Reverse order for backward pagination

    # Add search condition if provided
    if search_query:
        conditions.append("name ILIKE :search_pattern")
        params["search_pattern"] = f"%{search_query}%"

    # Add WHERE clause if we have conditions
    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    # Add ORDER BY and LIMIT
    query += f"""
        ORDER BY created_at {order_direction}, id {order_direction}
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
    categories = []
    for row in rows:
        categories.append(
            {"id": row.id, "name": row.name, "created_at": row.created_at},
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

    return categories, next_cursor, prev_cursor, has_more


# Register the same handler for both /categories and /categories/
@router.get("", response_model=CursorPagination, include_in_schema=False)
@router.get("/", response_model=CursorPagination)
async def list_categories(
    request: Request,
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Maximum number of items to return",
    ),
    after: Optional[str] = Query(None, description="Cursor for forward pagination"),
    before: Optional[str] = Query(None, description="Cursor for backward pagination"),
    q: Optional[str] = Query(None, description="Search query for category names"),
    db: Session = Depends(get_db),
):
    """List categories with cursor-based pagination.

    This endpoint uses keyset pagination for better performance with large datasets.
    Use the `after` cursor to fetch the next page of results or `before` to fetch the previous page.
    """
    try:
        # Get categories with cursor-based pagination
        (
            categories,
            next_cursor,
            prev_cursor,
            has_more,
        ) = await get_categories_with_cursor(
            db=db,
            limit=limit,
            after=after,
            before=before,
            search_query=q,
        )

        # Build response
        response = {
            "items": [CategoryResponse(**category) for category in categories],
            "next_cursor": next_cursor,
            "prev_cursor": prev_cursor,
            "has_more": has_more,
            "total": None,  # Total count is not provided for performance reasons
        }

        return response

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error listing categories")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list categories",
        )


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    request: Request,
    category_id: int,
    db: Session = Depends(get_db),
):
    # Apply rate limiting
    await rate_limit(request)
    """Get a specific category by ID"""
    query = text(
        """
        SELECT id, name
        FROM app.categories
        WHERE id = :category_id
    """,
    )
    result = db.execute(query, {"category_id": category_id}).first()

    if not result:
        raise HTTPException(status_code=404, detail="Category not found")

    return CategoryResponse(id=result.id, name=result.name)


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
    """Create a new category"""
    try:
        insert_query = text(
            """
            INSERT INTO app.categories (name)
            VALUES (:name)
            RETURNING id, name
        """,
        )
        result = db.execute(insert_query, {"name": category.name})
        created_category = result.fetchone()
        db.commit()

        return CategoryResponse(id=created_category.id, name=created_category.name)

    except Exception as e:
        db.rollback()
        # Check if it's a unique constraint violation
        if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
            raise HTTPException(status_code=400, detail="Category name already exists")
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
    """Update a category"""
    # Check if category exists
    existing_query = text("SELECT id, name FROM app.categories WHERE id = :category_id")
    existing = db.execute(existing_query, {"category_id": category_id}).fetchone()

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
            RETURNING id, name
        """,
        )

        result = db.execute(
            update_query,
            {"name": category_update.name, "category_id": category_id},
        )
        updated_category = result.fetchone()
        db.commit()

        return CategoryResponse(id=updated_category.id, name=updated_category.name)

    except Exception as e:
        db.rollback()
        # Check if it's a unique constraint violation
        if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
            raise HTTPException(status_code=400, detail="Category name already exists")
        raise HTTPException(status_code=500, detail="Failed to update category")


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    request: Request,
    category_id: int,
    db: Session = Depends(get_db),
):
    # Apply rate limiting with stricter limits for delete operations
    await RateLimiter(times=2, seconds=10)(request)
    """Delete a category"""
    # Check if category exists
    existing_query = text("SELECT id FROM app.categories WHERE id = :category_id")
    existing = db.execute(existing_query, {"category_id": category_id}).fetchone()

    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")

    try:
        # Delete category (cascade will handle product_categories)
        delete_query = text("DELETE FROM app.categories WHERE id = :category_id")
        db.execute(delete_query, {"category_id": category_id})
        db.commit()
    except Exception as error:
        db.rollback()
        logger.error(f"Failed to delete category {category_id}: {error!s}")
        raise HTTPException(status_code=500, detail="Failed to delete category")
