from __future__ import annotations

import base64
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from app.core.rate_limiting import RateLimiter
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.product import Product
from ..services.redis import CacheManager
from ..core.config import settings
from ..db import get_db
from ..schemas.product import ProductCreate, ProductUpdate, ProductResponse
from ..security.jwt import get_current_active_user
from ..schemas.auth import UserInDB
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])

# Rate limit configuration
rate_limit = RateLimiter(
    times=int(settings.RATE_LIMIT_DEFAULT.split("/")[0]),
    seconds=60,  # Default to 1 minute window
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


def _normalize_categories(raw: Any) -> List[Dict[str, Any]]:
    if not raw:
        return []
    if isinstance(raw, list):
        if raw and isinstance(raw[0], dict):
            return raw
        if raw and isinstance(raw[0], (list, tuple)) and len(raw[0]) >= 2:
            return [{"id": item[0], "name": item[1]} for item in raw]
        return raw
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            return []
    return []


async def get_product_with_categories(db: AsyncSession, product_id: int):
    """Get product with associated categories"""
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.categories))
        .where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    if product is None:
        return None

    categories = [
        {"id": category.id, "name": category.name}
        for category in (product.categories or [])
    ]

    return {
        "id": product.id,
        "name": product.name,
        "sku": product.sku,
        "base_price": (
            float(product.base_price) if product.base_price is not None else None
        ),
        "description": product.description,
        "is_active": product.is_active,
        "currency": getattr(product, "currency", None),
        "created_at": product.created_at,
        "updated_at": product.updated_at,
        "categories": categories,
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


async def get_products_with_cursor(
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
            detail="Cannot specify both 'after' and 'before' cursors",
        )

    # Base query with categories as array
    query = """
        SELECT p.id, p.name, p.sku, p.base_price, p.description, p.is_active, p.created_at, p.updated_at,
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

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    # Group by product fields for the array_agg
    query += f"""
        GROUP BY p.id, p.name, p.sku, p.base_price, p.description, p.is_active, p.created_at, p.updated_at
        ORDER BY p.created_at {order_direction}, p.id {order_direction}
        LIMIT :limit
        """
    # Set limit parameter (add 1 to check for more items)
    params["limit"] = limit + 1

    # Execute query with await since we're using async session
    result = await db.execute(text(query), params)
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
        categories = _normalize_categories(row.categories)
        base_price = None
        if row.base_price is not None:
            base_price = float(row.base_price)
        products.append(
            {
                "id": row.id,
                "name": row.name,
                "sku": row.sku,
                "base_price": base_price,
                "description": row.description,
                "is_active": row.is_active,
                "currency": row.currency,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
                "categories": categories,
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


@router.get("/", response_model=CursorPagination)
async def list_products(
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user),
    limit: int = Query(
        10,
        ge=1,
        le=100,
        description="Maximum number of items to return",
    ),
    after: Optional[str] = Query(None, description="Cursor for forward pagination"),
    before: Optional[str] = Query(None, description="Cursor for backward pagination"),
    search_query: Optional[str] = Query(
        None, description="Search term for product name"
    ),
    db: AsyncSession = Depends(get_db),
):
    """List products with cursor-based pagination.

    This endpoint uses keyset pagination for better performance with large datasets.
    Use the `after` cursor to fetch the next page of results or `before` to fetch the previous page.
    """
    try:
        # Get products with cursor-based pagination
        products, next_cursor, prev_cursor, has_more = await get_products_with_cursor(
            db=db, limit=limit, after=after, before=before, search_query=search_query
        )

        # Get total count of products (without pagination)
        count_query = "SELECT COUNT(*) as total FROM app.products"
        if search_query:
            count_query += " WHERE name ILIKE :search_pattern"
            count_params = {"search_pattern": f"%{search_query}%"}
        else:
            count_params = {}

        count_result = await db.execute(text(count_query), count_params)
        total = count_result.scalar()

        # Build response
        response = {
            "items": products,
            "next_cursor": next_cursor,
            "prev_cursor": prev_cursor,
            "has_more": has_more,
            "total": total,
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
    current_user: UserInDB = Depends(get_current_active_user),
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
    product = await get_product_with_categories(db, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Prepare response
    response = ProductResponse(**product)

    # Cache the response for 60 seconds
    await CacheManager.set_json(cache_key, response.model_dump(), expire=60)

    return response


@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(
    request: Request,
    product: ProductCreate,
    current_user: UserInDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new product."""
    # Apply rate limiting
    try:
        await rate_limit(request, None)
    except Exception as e:
        logger.error(f"Rate limiting error: {str(e)}")
        raise

    # Check for duplicate name
    existing = await db.execute(
        text("SELECT id FROM app.products WHERE name = :name"), {"name": product.name}
    )
    if existing.fetchone():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this name already exists",
        )

    # Prepare product data
    price_value = (
        product.base_price
        if getattr(product, "base_price", None) is not None
        else getattr(product, "price", None)
    )
    if price_value is None:
        price_value = 0.0

    product_data = {
        "name": product.name,
        "sku": getattr(product, "sku", ""),
        "price": price_value,
        "description": getattr(product, "description", ""),
        "is_active": getattr(product, "is_active", True),
        "currency": getattr(product, "currency", "RON"),
        "is_discontinued": getattr(product, "is_discontinued", False),
    }
    logger.info(f"Inserting product with data: {product_data}")
    # Insert new product
    result = await db.execute(
        text(
            """
            INSERT INTO app.products (
                name, sku, base_price, description, is_active, currency, is_discontinued,
                created_at, updated_at
            ) VALUES (
                :name, :sku, :price, :description, :is_active, :currency, :is_discontinued,
                NOW(), NOW()
            )
            RETURNING id, name, sku, base_price, description, is_active, currency,
                      is_discontinued, created_at, updated_at
            """
        ),
        product_data,
    )
    result = result.mappings().first()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve inserted product data",
        )
    result_dict = dict(result)
    # Convert Decimal/base_price to float for JSON serialization
    if "base_price" in result_dict and result_dict["base_price"] is not None:
        result_dict["base_price"] = float(result_dict["base_price"])
    # Handle categories if any
    category_ids = (
        getattr(product, "category_ids", None)
        or getattr(product, "categories", None)
        or []
    )
    logger.info(f"Processing categories for product: {category_ids}")
    if category_ids:
        categories_result = await db.execute(
            text("SELECT id, name FROM app.categories WHERE id = ANY(:category_ids)"),
            {"category_ids": category_ids},
        )
        categories = categories_result.fetchall()
        if categories:
            category_associations = [
                {"product_id": result_dict["id"], "category_id": cat.id}
                for cat in categories
            ]
            await db.execute(
                text(
                    """
                    INSERT INTO app.product_categories (product_id, category_id)
                    VALUES (:product_id, :category_id)
                    """
                ),
                category_associations,
            )
            result_dict["categories"] = [
                {"id": cat.id, "name": cat.name} for cat in categories
            ]
    await db.commit()
    await CacheManager.invalidate_prefix("products:list")
    detail_cache_key = f"products:detail:{result_dict['id']}"
    await CacheManager.delete(detail_cache_key)

    product_detail = await get_product_with_categories(db, result_dict["id"])
    if not product_detail:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve product",
        )
    logger.debug(
        "Create product response payload", extra={"product_detail": product_detail}
    )
    return ProductResponse(**product_detail)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    request: Request,
    product_id: int,
    product: ProductUpdate,
    current_user: UserInDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing product."""
    # Apply rate limiting
    try:
        await rate_limit(request, None)
    except Exception as e:
        logger.error(f"Rate limiting error: {str(e)}")
        raise

    # Fetch existing product
    existing = await db.execute(
        text("SELECT id FROM app.products WHERE id = :id"), {"id": product_id}
    )
    if not existing.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    # Prepare update data
    update_data: Dict[str, Any] = {}
    if product.name is not None:
        update_data["name"] = product.name
    if getattr(product, "sku", None) is not None:
        update_data["sku"] = product.sku
    price_value = (
        product.base_price
        if getattr(product, "base_price", None) is not None
        else getattr(product, "price", None)
    )
    if price_value is not None:
        update_data["base_price"] = price_value
    if getattr(product, "description", None) is not None:
        update_data["description"] = product.description
    if getattr(product, "is_active", None) is not None:
        update_data["is_active"] = product.is_active
    if getattr(product, "currency", None) is not None:
        update_data["currency"] = product.currency

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update"
        )

    set_clause = ", ".join([f"{key} = :{key}" for key in update_data.keys()])
    sql = f"""
        UPDATE app.products SET {set_clause}, updated_at = NOW() WHERE id = :product_id RETURNING id, name, sku, base_price, description, is_active, currency, created_at, updated_at
    """
    params = {**update_data, "product_id": product_id}
    result = await db.execute(text(sql), params)
    updated = result.mappings().first()
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update product",
        )
    await db.commit()
    await CacheManager.invalidate_prefix("products:list")
    await CacheManager.delete(f"products:detail:{product_id}")

    product_detail = await get_product_with_categories(db, product_id)
    if not product_detail:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load updated product",
        )
    logger.debug(
        "Update product response payload", extra={"product_detail": product_detail}
    )
    return ProductResponse(**product_detail)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    request: Request,
    product_id: int,
    current_user: UserInDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an existing product."""
    try:
        await rate_limit(request, None)
    except Exception as e:
        logger.error(f"Rate limiting error: {str(e)}")
        raise

    exists_query = text("SELECT id FROM app.products WHERE id = :id")
    existing = await db.execute(exists_query, {"id": product_id})
    if not existing.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    await db.execute(
        text("DELETE FROM app.product_categories WHERE product_id = :product_id"),
        {"product_id": product_id},
    )
    await db.execute(
        text("DELETE FROM app.products WHERE id = :product_id"),
        {"product_id": product_id},
    )
    await db.commit()

    await CacheManager.invalidate_prefix("products:list")
    await CacheManager.delete(f"products:detail:{product_id}")

    return Response(status_code=status.HTTP_204_NO_CONTENT)
