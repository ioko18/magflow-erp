from __future__ import annotations

import base64
import json
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.rate_limiting import RateLimiter

from ..core.config import settings
from ..crud.product import ProductCRUD
from ..db import get_db
from ..models.product import Product
from ..schemas.auth import UserInDB
from ..schemas.product import (
    ProductBulkCreate,
    ProductBulkCreateResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    ProductValidationResult,
)
from ..security.jwt import get_current_active_user
from ..services.infrastructure.redis import CacheManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])

# Rate limit configuration
rate_limit = RateLimiter(
    times=int(settings.RATE_LIMIT_DEFAULT.split("/")[0]),
    seconds=60,  # Default to 1 minute window
)


# Cursor pagination models
class CursorPagination(BaseModel):
    items: list[dict[str, Any]]
    next_cursor: str | None = None
    has_more: bool = False
    total: int | None = None


# Cursor encoding/decoding
def encode_cursor(created_at: datetime, id: int) -> str:
    cursor_data = {"created_at": created_at.isoformat(), "id": id}
    return base64.b64encode(json.dumps(cursor_data).encode()).decode()


def decode_cursor(cursor: str) -> dict[str, Any]:
    try:
        data = json.loads(base64.b64decode(cursor.encode()).decode())
        return {
            "created_at": datetime.fromisoformat(data["created_at"]),
            "id": data["id"],
        }
    except (json.JSONDecodeError, UnicodeDecodeError, KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail="Invalid cursor format") from e


def _normalize_categories(raw: Any) -> list[dict[str, Any]]:
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


def _decode_cursor(cursor: str | None) -> dict[str, Any] | None:
    """Decode base64-encoded cursor to dictionary."""
    if not cursor:
        return None
    try:
        data = json.loads(base64.b64decode(cursor.encode()).decode())
        return {
            "created_at": datetime.fromisoformat(data["created_at"]),
            "id": data["id"],
        }
    except (json.JSONDecodeError, UnicodeDecodeError, KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail="Invalid cursor format") from e


async def get_products_with_cursor(
    db: AsyncSession,
    limit: int,
    after: str | None = None,
    before: str | None = None,
    search_query: str | None = None,
) -> tuple[list[dict[str, Any]], str | None, str | None, bool]:
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

    # Base query with categories as array and old SKU search support
    query = (
        "\n        SELECT DISTINCT\n"
        "            p.id,\n"
        "            p.name,\n"
        "            p.sku,\n"
        "            p.base_price,\n"
        "            p.currency,\n"
        "            p.description,\n"
        "            p.is_active,\n"
        "            p.created_at,\n"
        "            p.updated_at,\n"
        "            COALESCE(\n"
        "                array_agg(DISTINCT c.name) FILTER (WHERE c.name IS NOT NULL),\n"
        "                '{}'\n"
        "            ) as categories\n"
        "        FROM app.products p\n"
        "        LEFT JOIN app.product_categories pc ON p.id = pc.product_id\n"
        "        LEFT JOIN app.categories c ON pc.category_id = c.id\n"
        "        LEFT JOIN app.product_sku_history psh ON p.id = psh.product_id\n"
    )

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

    # Add search condition if provided - search in name, current SKU, and old SKUs
    if search_query:
        conditions.append(
            "(p.name ILIKE :search_pattern OR "
            "p.sku ILIKE :search_pattern OR "
            "psh.old_sku ILIKE :search_pattern)"
        )
        params["search_pattern"] = f"%{search_query}%"

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    # Group by product fields for the array_agg
    query += (
        "\n        GROUP BY\n"
        "            p.id,\n"
        "            p.name,\n"
        "            p.sku,\n"
        "            p.base_price,\n"
        "            p.currency,\n"
        "            p.description,\n"
        "            p.is_active,\n"
        "            p.created_at,\n"
        "            p.updated_at\n"
        f"        ORDER BY p.created_at {order_direction}, p.id {order_direction}\n"
        "        LIMIT :limit\n"
    )
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
    after: str | None = Query(None, description="Cursor for forward pagination"),
    before: str | None = Query(None, description="Cursor for backward pagination"),
    search_query: str | None = Query(
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
        count_query = """
            SELECT COUNT(DISTINCT p.id) as total
            FROM app.products p
            LEFT JOIN app.product_sku_history psh ON p.id = psh.product_id
        """
        if search_query:
            count_query += (
                " WHERE ("
                "p.name ILIKE :search_pattern OR "
                "p.sku ILIKE :search_pattern OR "
                "psh.old_sku ILIKE :search_pattern"
                ")"
            )
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
    except Exception as e:
        logger.exception("Error listing products")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list products",
        ) from e


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
    """Create a new product with comprehensive validation.

    This endpoint creates a new product with all fields including:
    - Basic information (name, SKU, description, brand, manufacturer)
    - Pricing (base price, recommended price, currency)
    - Physical properties (weight, dimensions)
    - eMAG integration fields (category, brand, warranty, EAN)
    - Media (images, attachments)
    - Categories

    The product can optionally be auto-published to eMAG if `auto_publish_emag` is set to true.
    """
    try:
        await rate_limit(request, None)
    except Exception as e:
        logger.error(f"Rate limiting error: {str(e)}")
        raise

    try:
        # Create product using CRUD service
        created_product = await ProductCRUD.create_product(db, product)

        # Invalidate cache
        await CacheManager.invalidate_prefix("products:list")
        await CacheManager.delete(f"products:detail:{created_product.id}")

        logger.info(
            f"Successfully created product: {created_product.sku} (ID: {created_product.id})"
        )
        return ProductResponse.model_validate(created_product)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception(f"Error creating product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create product: {str(e)}",
        ) from e


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    request: Request,
    product_id: int,
    product: ProductUpdate,
    current_user: UserInDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing product.

    All fields are optional. Only provided fields will be updated.
    Set `sync_to_emag` to true to automatically sync changes to eMAG.
    """
    try:
        await rate_limit(request, None)
    except Exception as e:
        logger.error(f"Rate limiting error: {str(e)}")
        raise

    try:
        # Update product using CRUD service
        updated_product = await ProductCRUD.update_product(db, product_id, product)

        # Invalidate cache
        await CacheManager.invalidate_prefix("products:list")
        await CacheManager.delete(f"products:detail:{product_id}")

        logger.info(
            f"Successfully updated product: {updated_product.sku} (ID: {product_id})"
        )
        return ProductResponse.model_validate(updated_product)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND
            if "not found" in str(e).lower()
            else status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception(f"Error updating product {product_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update product: {str(e)}",
        ) from e


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    request: Request,
    product_id: int,
    hard_delete: bool = Query(
        False, description="Perform hard delete (permanent removal)"
    ),
    current_user: UserInDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a product.

    By default, performs a soft delete (marks as inactive and discontinued).
    Set `hard_delete=true` to permanently remove the product from the database.
    """
    try:
        await rate_limit(request, None)
    except Exception as e:
        logger.error(f"Rate limiting error: {str(e)}")
        raise

    try:
        # Delete product using CRUD service
        await ProductCRUD.delete_product(db, product_id, soft_delete=not hard_delete)

        # Invalidate cache
        await CacheManager.invalidate_prefix("products:list")
        await CacheManager.delete(f"products:detail:{product_id}")

        logger.info(
            f"Successfully {'hard' if hard_delete else 'soft'} deleted product ID: {product_id}"
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception(f"Error deleting product {product_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete product: {str(e)}",
        ) from e


@router.post("/validate", response_model=ProductValidationResult)
async def validate_product(
    request: Request,
    product: ProductCreate,
    current_user: UserInDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Validate a product without creating it.

    This endpoint checks if the product data is valid and ready for eMAG integration.
    Returns validation errors, warnings, and missing fields for eMAG compliance.
    """
    try:
        validation_result = await ProductCRUD.validate_product(db, product)
        return validation_result
    except Exception as e:
        logger.exception(f"Error validating product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate product: {str(e)}",
        ) from e


@router.post("/bulk", response_model=ProductBulkCreateResponse, status_code=201)
async def bulk_create_products(
    request: Request,
    bulk_data: ProductBulkCreate,
    current_user: UserInDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk create products (max 100 at a time).

    This endpoint allows creating multiple products in a single request.
    Returns both successfully created products and failed products with error messages.
    """
    try:
        await rate_limit(request, None)
    except Exception as e:
        logger.error(f"Rate limiting error: {str(e)}")
        raise

    try:
        created, failed = await ProductCRUD.bulk_create_products(db, bulk_data.products)

        # Invalidate cache
        await CacheManager.invalidate_prefix("products:list")

        response = ProductBulkCreateResponse(
            created=[ProductResponse.model_validate(p) for p in created],
            failed=failed,
            total_created=len(created),
            total_failed=len(failed),
        )

        logger.info(
            f"Bulk create completed: {len(created)} created, {len(failed)} failed"
        )
        return response

    except Exception as e:
        logger.exception(f"Error in bulk create: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk create products: {str(e)}",
        ) from e


@router.get("/statistics", response_model=dict[str, Any])
async def get_product_statistics(
    request: Request,
    current_user: UserInDB = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get product statistics.

    Returns aggregate statistics about products including:
    - Total, active, inactive, discontinued counts
    - eMAG mapped vs unmapped products
    - Average price
    """
    try:
        stats = await ProductCRUD.get_product_statistics(db)
        return stats
    except Exception as e:
        logger.exception(f"Error getting product statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get product statistics: {str(e)}",
        ) from e
