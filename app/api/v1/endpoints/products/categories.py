"""Categories API endpoints for MagFlow ERP.

This module provides REST API endpoints for managing product categories.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.category import Category
from app.security.jwt import get_current_user

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=dict[str, Any])
async def list_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True),
    parent_id: int | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List categories with optional filtering."""

    # Build query
    query = select(Category)

    if active_only:
        query = query.where(Category.is_active)

    if parent_id is not None:
        if parent_id == 0:
            # Root categories (no parent)
            query = query.where(Category.parent_id.is_(None))
        else:
            query = query.where(Category.parent_id == parent_id)

    if search:
        search_filter = f"%{search}%"
        query = query.where(Category.name.ilike(search_filter))

    # Execute query with pagination
    result = await db.execute(query.order_by(Category.name).offset(skip).limit(limit))
    categories = result.scalars().all()

    # Get total count for pagination
    count_query = select(func.count(Category.id))
    if active_only:
        count_query = count_query.where(Category.is_active)
    if parent_id is not None:
        if parent_id == 0:
            count_query = count_query.where(Category.parent_id.is_(None))
        else:
            count_query = count_query.where(Category.parent_id == parent_id)
    if search:
        count_query = count_query.where(Category.name.ilike(search_filter))

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    return {
        "status": "success",
        "data": {
            "categories": [
                {
                    "id": category.id,
                    "name": category.name,
                    "description": category.description,
                    "parent_id": category.parent_id,
                    "is_active": category.is_active,
                    "created_at": category.created_at.isoformat()
                    if category.created_at
                    else None,
                }
                for category in categories
            ],
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": skip + limit < total,
            },
        },
    }


@router.get("/{category_id}", response_model=dict[str, Any])
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get detailed category information."""

    query = select(Category).where(Category.id == category_id)
    result = await db.execute(query)
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Get child categories
    children_query = (
        select(Category)
        .where(and_(Category.parent_id == category_id, Category.is_active))
        .order_by(Category.name)
    )
    children_result = await db.execute(children_query)
    children = children_result.scalars().all()

    # Get product count for this category
    # Note: This requires the product_categories association table to be properly imported
    # For now, return 0 to avoid errors - will be fixed when product relationships are established
    product_count = 0
    # TODO: Implement proper product count query when product_categories table is available

    return {
        "status": "success",
        "data": {
            "category": {
                "id": category.id,
                "name": category.name,
                "description": category.description,
                "parent_id": category.parent_id,
                "is_active": category.is_active,
                "created_at": category.created_at.isoformat()
                if category.created_at
                else None,
                "updated_at": category.updated_at.isoformat()
                if category.updated_at
                else None,
            },
            "children": [
                {
                    "id": child.id,
                    "name": child.name,
                    "description": child.description,
                }
                for child in children
            ],
            "product_count": product_count,
        },
    }


@router.post("", response_model=dict[str, Any])
async def create_category(
    category_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a new category."""

    # Check for duplicate category name
    existing_query = select(Category).where(
        and_(
            Category.name == category_data["name"],
            Category.parent_id == category_data.get("parent_id"),
        )
    )
    existing_result = await db.execute(existing_query)
    existing_category = existing_result.scalar_one_or_none()

    if existing_category:
        raise HTTPException(
            status_code=400, detail=f"Category '{category_data['name']}' already exists"
        )

    # Validate parent category exists if specified
    if category_data.get("parent_id"):
        parent_query = select(Category).where(Category.id == category_data["parent_id"])
        parent_result = await db.execute(parent_query)
        parent_category = parent_result.scalar_one_or_none()

        if not parent_category:
            raise HTTPException(status_code=400, detail="Parent category not found")

    # Create category
    category = Category(**category_data)
    db.add(category)
    await db.commit()
    await db.refresh(category)

    return {
        "status": "success",
        "data": {
            "id": category.id,
            "name": category.name,
            "message": "Category created successfully",
        },
    }


@router.put("/{category_id}", response_model=dict[str, Any])
async def update_category(
    category_id: int,
    update_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update category information."""

    query = select(Category).where(Category.id == category_id)
    result = await db.execute(query)
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check for duplicate name if name is being updated
    if "name" in update_data:
        existing_query = select(Category).where(
            and_(Category.name == update_data["name"], Category.id != category_id)
        )
        existing_result = await db.execute(existing_query)
        existing_category = existing_result.scalar_one_or_none()

        if existing_category:
            raise HTTPException(
                status_code=400,
                detail=f"Category '{update_data['name']}' already exists",
            )

    # Update fields
    for field, value in update_data.items():
        if hasattr(category, field):
            setattr(category, field, value)

    await db.commit()

    return {
        "status": "success",
        "data": {
            "id": category.id,
            "name": category.name,
            "message": "Category updated successfully",
        },
    }


@router.delete("/{category_id}", response_model=dict[str, Any])
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Soft delete a category."""

    query = select(Category).where(Category.id == category_id)
    result = await db.execute(query)
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check if category has children
    children_query = select(Category).where(Category.parent_id == category_id)
    children_result = await db.execute(children_query)
    children = children_result.scalars().all()

    if children:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete category with {len(children)} child categories",
        )

    # Check if category has products
    # TODO: Implement proper product count check when product_categories table is available
    # For now, allow deletion - will be enhanced later

    # Soft delete
    category.is_active = False
    await db.commit()

    return {"status": "success", "data": {"message": "Category deleted successfully"}}
