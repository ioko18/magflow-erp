"""
Product Management API with comprehensive editing and history tracking.

Features:
- Inline field updates with validation
- SKU history tracking
- Change log for all fields
- Bulk operations support
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from app.db import get_db
from app.models.product import Product
from app.models.product_history import ProductChangeLog, ProductSKUHistory
from app.models.supplier import SupplierProduct
from app.models.user import User
from app.security.jwt import get_current_user

router = APIRouter(prefix="/products", tags=["product-management"])


# ============================================================================
# Request/Response Models
# ============================================================================


class ProductUpdateRequest(BaseModel):
    """Request to update product fields."""

    sku: str | None = Field(None, max_length=100, description="Product SKU")
    name: str | None = Field(None, max_length=255, description="Product name")
    chinese_name: str | None = Field(
        None, max_length=500, description="Chinese product name"
    )
    image_url: str | None = Field(
        None, max_length=1000, description="Primary product image URL"
    )
    invoice_name_ro: str | None = Field(
        None, max_length=200, description="Romanian invoice name"
    )
    invoice_name_en: str | None = Field(
        None, max_length=200, description="English invoice name"
    )
    ean: str | None = Field(None, max_length=18, description="EAN code")
    base_price: float | None = Field(None, ge=0, description="Base price")
    recommended_price: float | None = Field(
        None, ge=0, description="Recommended price"
    )
    brand: str | None = Field(None, max_length=100, description="Brand")
    manufacturer: str | None = Field(
        None, max_length=100, description="Manufacturer"
    )
    description: str | None = Field(None, description="Product description")
    short_description: str | None = Field(
        None, max_length=500, description="Short description"
    )
    weight_kg: float | None = Field(None, ge=0, description="Weight in kg")
    is_active: bool | None = Field(None, description="Active status")
    is_discontinued: bool | None = Field(None, description="Discontinued status")
    change_reason: str | None = Field(None, description="Reason for the change")

    @field_validator("base_price", "recommended_price")
    @classmethod
    def validate_price(cls, v):
        if v is not None and v < 0:
            raise ValueError("Price must be non-negative")
        return v

    @field_validator("sku")
    @classmethod
    def validate_sku(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("SKU cannot be empty")
            if len(v) > 100:
                raise ValueError("SKU too long (max 100 characters)")
        return v


class BulkUpdateRequest(BaseModel):
    """Request to update multiple products."""

    updates: list[dict[str, Any]] = Field(
        ..., description="List of product updates with product_id"
    )


class ReorderProductsRequest(BaseModel):
    """Request to reorder products."""

    product_orders: list[dict[str, int]] = Field(
        ..., description="List of {product_id: display_order} mappings"
    )

    @field_validator("product_orders")
    @classmethod
    def validate_orders(cls, v):
        if not v:
            raise ValueError("At least one product order must be specified")
        return v


class UpdateDisplayOrderRequest(BaseModel):
    """Request to update a single product's display order."""

    display_order: int = Field(..., ge=0, description="New display order (0-based)")
    auto_adjust: bool = Field(
        default=True,
        description="Automatically adjust other products if order conflicts",
    )


class SKUHistoryResponse(BaseModel):
    """Response with SKU history."""

    id: int
    product_id: int
    old_sku: str
    new_sku: str
    changed_at: datetime
    changed_by_email: str | None
    change_reason: str | None
    ip_address: str | None

    class Config:
        from_attributes = True


class ChangeLogResponse(BaseModel):
    """Response with change log."""

    id: int
    product_id: int
    field_name: str
    old_value: str | None
    new_value: str | None
    changed_at: datetime
    changed_by_email: str | None
    change_type: str

    class Config:
        from_attributes = True


class ProductDetailResponse(BaseModel):
    """Detailed product response with history."""

    id: int
    sku: str
    name: str
    chinese_name: str | None
    image_url: str | None
    invoice_name_ro: str | None
    invoice_name_en: str | None
    ean: str | None
    base_price: float
    recommended_price: float | None
    brand: str | None
    manufacturer: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    sku_history_count: int
    change_log_count: int

    class Config:
        from_attributes = True


# ============================================================================
# Helper Functions
# ============================================================================


async def log_field_change(
    db: AsyncSession,
    product_id: int,
    field_name: str,
    old_value: Any,
    new_value: Any,
    user_id: int | None,
    ip_address: str | None = None,
):
    """Log a field change to the change log."""
    # Convert values to strings for storage
    old_str = str(old_value) if old_value is not None else None
    new_str = str(new_value) if new_value is not None else None

    if old_str == new_str:
        return  # No change

    change_log = ProductChangeLog(
        product_id=product_id,
        field_name=field_name,
        old_value=old_str,
        new_value=new_str,
        changed_at=datetime.now(UTC),
        changed_by_id=user_id,
        change_type="update",
        ip_address=ip_address,
    )
    db.add(change_log)


async def log_sku_change(
    db: AsyncSession,
    product_id: int,
    old_sku: str,
    new_sku: str,
    user_id: int | None,
    change_reason: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
):
    """Log SKU change to history."""
    if old_sku == new_sku:
        return  # No change

    sku_history = ProductSKUHistory(
        product_id=product_id,
        old_sku=old_sku,
        new_sku=new_sku,
        changed_at=datetime.now(UTC),
        changed_by_id=user_id,
        change_reason=change_reason,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(sku_history)


def get_client_ip(request: Request) -> str | None:
    """Extract client IP from request."""
    if request.client:
        return request.client.host
    return None


def get_user_agent(request: Request) -> str | None:
    """Extract user agent from request."""
    return request.headers.get("user-agent")


# ============================================================================
# Product Update Endpoints
# ============================================================================


@router.patch("/{product_id}", response_model=ProductDetailResponse)
async def update_product(
    product_id: int,
    update_data: ProductUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update product fields with automatic history tracking.

    Features:
    - Updates any editable field
    - Tracks SKU changes in separate history table
    - Logs all field changes
    - Validates data before update

    Example:
    ```json
    {
        "name": "Updated Product Name",
        "base_price": 99.99,
        "invoice_name_ro": "Nume scurt",
        "change_reason": "Price correction"
    }
    ```
    """
    # Fetch product
    query = select(Product).where(Product.id == product_id)
    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    # Get client info
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    # Track changes
    update_dict = update_data.dict(exclude_unset=True, exclude={"change_reason"})

    for field_name, new_value in update_dict.items():
        if hasattr(product, field_name):
            old_value = getattr(product, field_name)

            # Special handling for SKU changes
            if field_name == "sku" and old_value != new_value:
                # Check if new SKU already exists
                existing_query = select(Product).where(
                    Product.sku == new_value, Product.id != product_id
                )
                existing_result = await db.execute(existing_query)
                if existing_result.scalar_one_or_none():
                    raise HTTPException(
                        status_code=400, detail=f"SKU '{new_value}' already exists"
                    )

                # Log SKU change
                await log_sku_change(
                    db=db,
                    product_id=product_id,
                    old_sku=old_value,
                    new_sku=new_value,
                    user_id=current_user.id,
                    change_reason=update_data.change_reason,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

            # Log field change
            await log_field_change(
                db=db,
                product_id=product_id,
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
                user_id=current_user.id,
                ip_address=ip_address,
            )

            # Update field
            setattr(product, field_name, new_value)

    # Commit changes
    await db.commit()
    await db.refresh(product)

    # Count history entries
    sku_history_query = select(ProductSKUHistory).where(
        ProductSKUHistory.product_id == product_id
    )
    sku_history_result = await db.execute(sku_history_query)
    sku_history_count = len(sku_history_result.scalars().all())

    change_log_query = select(ProductChangeLog).where(
        ProductChangeLog.product_id == product_id
    )
    change_log_result = await db.execute(change_log_query)
    change_log_count = len(change_log_result.scalars().all())

    return ProductDetailResponse(
        id=product.id,
        sku=product.sku,
        name=product.name,
        chinese_name=product.chinese_name,
        image_url=product.image_url,
        invoice_name_ro=product.invoice_name_ro,
        invoice_name_en=product.invoice_name_en,
        ean=product.ean,
        base_price=product.base_price,
        recommended_price=product.recommended_price,
        brand=product.brand,
        manufacturer=product.manufacturer,
        is_active=product.is_active,
        created_at=product.created_at,
        updated_at=product.updated_at,
        sku_history_count=sku_history_count,
        change_log_count=change_log_count,
    )


@router.get("/{product_id}/sku-history", response_model=list[SKUHistoryResponse])
async def get_sku_history(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get SKU change history for a product.

    Returns chronological list of all SKU changes with:
    - Old and new SKU values
    - Who made the change
    - When it was changed
    - Reason for change (if provided)
    - IP address
    """
    # Verify product exists
    product_query = select(Product).where(Product.id == product_id)
    product_result = await db.execute(product_query)
    product = product_result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    # Fetch SKU history
    query = (
        select(ProductSKUHistory)
        .where(ProductSKUHistory.product_id == product_id)
        .order_by(ProductSKUHistory.changed_at.desc())
    )

    result = await db.execute(query)
    history_entries = result.scalars().all()

    return [
        SKUHistoryResponse(
            id=entry.id,
            product_id=entry.product_id,
            old_sku=entry.old_sku,
            new_sku=entry.new_sku,
            changed_at=entry.changed_at,
            changed_by_email=entry.changed_by.email if entry.changed_by else None,
            change_reason=entry.change_reason,
            ip_address=entry.ip_address,
        )
        for entry in history_entries
    ]


@router.get("/{product_id}/change-log", response_model=list[ChangeLogResponse])
async def get_change_log(
    product_id: int,
    field_name: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get complete change log for a product.

    Optional filters:
    - field_name: Filter by specific field
    - limit: Maximum number of entries to return

    Returns all field changes with old/new values.
    """
    # Verify product exists
    product_query = select(Product).where(Product.id == product_id)
    product_result = await db.execute(product_query)
    product = product_result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    # Build query
    query = select(ProductChangeLog).where(ProductChangeLog.product_id == product_id)

    if field_name:
        query = query.where(ProductChangeLog.field_name == field_name)

    query = query.order_by(ProductChangeLog.changed_at.desc()).limit(limit)

    result = await db.execute(query)
    log_entries = result.scalars().all()

    return [
        ChangeLogResponse(
            id=entry.id,
            product_id=entry.product_id,
            field_name=entry.field_name,
            old_value=entry.old_value,
            new_value=entry.new_value,
            changed_at=entry.changed_at,
            changed_by_email=entry.changed_by.email if entry.changed_by else None,
            change_type=entry.change_type,
        )
        for entry in log_entries
    ]


@router.post("/bulk-update")
async def bulk_update_products(
    bulk_request: BulkUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update multiple products at once.

    Example:
    ```json
    {
        "updates": [
            {
                "product_id": 1,
                "base_price": 99.99,
                "is_active": true
            },
            {
                "product_id": 2,
                "name": "Updated Name",
                "brand": "New Brand"
            }
        ]
    }
    ```
    """
    results = []
    ip_address = get_client_ip(request)

    for update_item in bulk_request.updates:
        try:
            product_id = update_item.get("product_id")
            if not product_id:
                results.append(
                    {
                        "product_id": None,
                        "status": "error",
                        "message": "Missing product_id",
                    }
                )
                continue

            # Fetch product
            query = select(Product).where(Product.id == product_id)
            result = await db.execute(query)
            product = result.scalar_one_or_none()

            if not product:
                results.append(
                    {
                        "product_id": product_id,
                        "status": "error",
                        "message": "Product not found",
                    }
                )
                continue

            # Update fields
            updated_fields = []
            for field_name, new_value in update_item.items():
                if field_name == "product_id":
                    continue

                if hasattr(product, field_name):
                    old_value = getattr(product, field_name)

                    # Log change
                    await log_field_change(
                        db=db,
                        product_id=product_id,
                        field_name=field_name,
                        old_value=old_value,
                        new_value=new_value,
                        user_id=current_user.id,
                        ip_address=ip_address,
                    )

                    setattr(product, field_name, new_value)
                    updated_fields.append(field_name)

            results.append(
                {
                    "product_id": product_id,
                    "status": "success",
                    "updated_fields": updated_fields,
                }
            )

        except Exception as e:
            results.append(
                {
                    "product_id": update_item.get("product_id"),
                    "status": "error",
                    "message": str(e),
                }
            )

    await db.commit()

    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = sum(1 for r in results if r["status"] == "error")

    return {
        "status": "success",
        "message": f"Updated {success_count} products, {error_count} errors",
        "data": {
            "results": results,
            "summary": {
                "total": len(results),
                "success": success_count,
                "errors": error_count,
            },
        },
    }


# ============================================================================
# CRUD Endpoints for Products
# ============================================================================


@router.get("/statistics")
async def get_products_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get product statistics."""

    # Total products
    total_query = select(func.count(Product.id))
    total_result = await db.execute(total_query)
    total_products = total_result.scalar()

    # Active products
    active_query = select(func.count(Product.id)).where(Product.is_active.is_(True))
    active_result = await db.execute(active_query)
    active_products = active_result.scalar()

    # Inactive products
    inactive_products = total_products - active_products

    # Products in stock (assuming products with base_price > 0 are in stock)
    in_stock_query = select(func.count(Product.id)).where(
        and_(Product.is_active.is_(True), Product.base_price > 0)
    )
    in_stock_result = await db.execute(in_stock_query)
    in_stock = in_stock_result.scalar()

    # Out of stock
    out_of_stock = total_products - in_stock

    # Average price
    avg_price_query = select(func.avg(Product.base_price))
    avg_price_result = await db.execute(avg_price_query)
    average_price = avg_price_result.scalar() or 0.0

    return {
        "status": "success",
        "data": {
            "total_products": total_products,
            "active_products": active_products,
            "inactive_products": inactive_products,
            "in_stock": in_stock,
            "out_of_stock": out_of_stock,
            "average_price": float(average_price),
        },
    }


@router.get("")
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(False),
    status_filter: str | None = Query(
        None, description="Filter by status: all, active, inactive, discontinued"
    ),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List products with pagination and filtering.

    Status filter options:
    - all: Show all products (default)
    - active: Show only active products (is_active=true AND is_discontinued=false)
    - inactive: Show only inactive products (is_active=false)
    - discontinued: Show only discontinued products (is_discontinued=true)
    """

    # Build query
    query = select(Product)

    # Apply status filter (new logic)
    if status_filter == "active":
        query = query.where(
            and_(Product.is_active.is_(True), Product.is_discontinued.is_(False))
        )
    elif status_filter == "inactive":
        query = query.where(Product.is_active.is_(False))
    elif status_filter == "discontinued":
        query = query.where(Product.is_discontinued.is_(True))
    elif active_only:  # Legacy support for active_only parameter
        query = query.where(Product.is_active.is_(True))
    # else: show all products (no filter)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                Product.name.ilike(search_filter),
                Product.sku.ilike(search_filter),
                Product.ean.ilike(search_filter),
                Product.brand.ilike(search_filter),
                Product.manufacturer.ilike(search_filter),
            )
        )

    # Get total count with same filters
    count_query = select(func.count(Product.id))

    # Apply same status filter to count query
    if status_filter == "active":
        count_query = count_query.where(
            and_(Product.is_active.is_(True), Product.is_discontinued.is_(False))
        )
    elif status_filter == "inactive":
        count_query = count_query.where(Product.is_active.is_(False))
    elif status_filter == "discontinued":
        count_query = count_query.where(Product.is_discontinued.is_(True))
    elif active_only:
        count_query = count_query.where(Product.is_active.is_(True))

    if search:
        count_query = count_query.where(
            or_(
                Product.name.ilike(search_filter),
                Product.sku.ilike(search_filter),
                Product.ean.ilike(search_filter),
                Product.brand.ilike(search_filter),
                Product.manufacturer.ilike(search_filter),
            )
        )

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Execute query with pagination - load supplier_mappings for display
    # Sort by display_order first (NULLS LAST), then by created_at
    result = await db.execute(
        query.options(
            noload(Product.categories),
            noload(Product.inventory_items),
            selectinload(Product.supplier_mappings).selectinload(
                SupplierProduct.supplier
            ),
            noload(Product.sku_history),
            noload(Product.change_logs),
        )
        .order_by(Product.display_order.asc().nullslast(), Product.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    products = result.scalars().all()

    return {
        "status": "success",
        "data": {
            "products": [
                {
                    "id": p.id,
                    "name": p.name,
                    "chinese_name": p.chinese_name,
                    "image_url": p.image_url,
                    "sku": p.sku,
                    "emag_part_number_key": p.emag_part_number_key,
                    "ean": p.ean,
                    "brand": p.brand,
                    "manufacturer": p.manufacturer,
                    "base_price": p.base_price,
                    "recommended_price": p.recommended_price,
                    "currency": p.currency,
                    "weight_kg": p.weight_kg,
                    "is_active": p.is_active,
                    "is_discontinued": p.is_discontinued,
                    "description": p.description,
                    "short_description": p.short_description,
                    "display_order": p.display_order,
                    "suppliers": list(
                        {
                            sm.supplier.id: {
                                "id": sm.supplier.id,
                                "name": sm.supplier.name,
                                "country": sm.supplier.country,
                                "is_active": sm.is_active,
                                "supplier_price": sm.supplier_price,
                                "supplier_currency": sm.supplier_currency,
                            }
                            for sm in p.supplier_mappings
                            if sm.supplier
                        }.values()
                    )
                    if p.supplier_mappings
                    else [],
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                }
                for p in products
            ],
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": skip + limit < total,
            },
        },
    }


@router.get("/{product_id}")
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get product by ID."""

    query = select(Product).where(Product.id == product_id)
    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return {
        "status": "success",
        "data": {
            "id": product.id,
            "name": product.name,
            "chinese_name": product.chinese_name,
            "image_url": product.image_url,
            "sku": product.sku,
            "emag_part_number_key": product.emag_part_number_key,
            "ean": product.ean,
            "brand": product.brand,
            "manufacturer": product.manufacturer,
            "base_price": product.base_price,
            "recommended_price": product.recommended_price,
            "currency": product.currency,
            "weight_kg": product.weight_kg,
            "length_cm": product.length_cm,
            "width_cm": product.width_cm,
            "height_cm": product.height_cm,
            "is_active": product.is_active,
            "is_discontinued": product.is_discontinued,
            "description": product.description,
            "short_description": product.short_description,
            "created_at": product.created_at.isoformat()
            if product.created_at
            else None,
            "updated_at": product.updated_at.isoformat()
            if product.updated_at
            else None,
        },
    }


@router.post("")
async def create_product(
    product_data: dict[str, Any],
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new product."""

    try:
        # Check if SKU already exists
        existing_query = select(Product).where(Product.sku == product_data.get("sku"))
        existing_result = await db.execute(existing_query)
        existing_product = existing_result.scalar_one_or_none()

        if existing_product:
            raise HTTPException(
                status_code=400, detail="Product with this SKU already exists"
            )

        # Create product
        product = Product(
            name=product_data.get("name"),
            sku=product_data.get("sku"),
            ean=product_data.get("ean"),
            brand=product_data.get("brand"),
            manufacturer=product_data.get("manufacturer"),
            base_price=product_data.get("base_price", 0.0),
            recommended_price=product_data.get("recommended_price"),
            currency=product_data.get("currency", "RON"),
            weight_kg=product_data.get("weight_kg"),
            length_cm=product_data.get("length_cm"),
            width_cm=product_data.get("width_cm"),
            height_cm=product_data.get("height_cm"),
            description=product_data.get("description"),
            short_description=product_data.get("short_description"),
            is_active=product_data.get("is_active", True),
            is_discontinued=product_data.get("is_discontinued", False),
            chinese_name=product_data.get("chinese_name"),
            image_url=product_data.get("image_url"),
        )

        db.add(product)
        await db.flush()

        # Log creation
        ip_address = get_client_ip(request)
        change_log = ProductChangeLog(
            product_id=product.id,
            field_name="product",
            old_value=None,
            new_value="created",
            changed_at=datetime.now(UTC),
            changed_by_id=current_user.id,
            change_type="create",
            ip_address=ip_address,
        )
        db.add(change_log)

        await db.commit()
        await db.refresh(product)

        return {
            "status": "success",
            "data": {
                "id": product.id,
                "name": product.name,
                "sku": product.sku,
                "message": "Product created successfully",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{product_id}")
async def update_product_full(
    product_id: int,
    update_data: dict[str, Any],
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full update of a product (PUT method)."""

    try:
        # Get product
        query = select(Product).where(Product.id == product_id)
        result = await db.execute(query)
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Track changes
        ip_address = get_client_ip(request)

        # Update fields and log changes
        for field, new_value in update_data.items():
            if hasattr(product, field):
                old_value = getattr(product, field)

                if old_value != new_value:
                    # Special handling for SKU changes
                    if field == "sku":
                        await log_sku_change(
                            db,
                            product_id,
                            old_value,
                            new_value,
                            current_user.id,
                            None,
                            ip_address,
                            get_user_agent(request),
                        )

                    # Log field change
                    await log_field_change(
                        db,
                        product_id,
                        field,
                        old_value,
                        new_value,
                        current_user.id,
                        ip_address,
                    )

                    # Update field
                    setattr(product, field, new_value)

        product.updated_at = datetime.now(UTC)

        await db.commit()
        await db.refresh(product)

        return {
            "status": "success",
            "data": {
                "id": product.id,
                "name": product.name,
                "message": "Product updated successfully",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft delete a product (mark as inactive and discontinued)."""

    try:
        query = select(Product).where(Product.id == product_id)
        result = await db.execute(query)
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Soft delete
        product.is_active = False
        product.is_discontinued = True
        product.updated_at = datetime.now(UTC)

        # Log deletion
        ip_address = get_client_ip(request)
        change_log = ProductChangeLog(
            product_id=product.id,
            field_name="product",
            old_value="active",
            new_value="deleted",
            changed_at=datetime.now(UTC),
            changed_by_id=current_user.id,
            change_type="delete",
            ip_address=ip_address,
        )
        db.add(change_log)

        await db.commit()

        return {
            "status": "success",
            "data": {"message": "Product deleted successfully"},
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{product_id}/toggle-discontinued")
async def toggle_discontinued_status(
    product_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Toggle the discontinued status of a product.

    This endpoint allows quick toggling of the discontinued flag.
    When a product is marked as discontinued, it's recommended to also mark it as inactive.
    """
    try:
        query = select(Product).where(Product.id == product_id)
        result = await db.execute(query)
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Toggle discontinued status
        old_status = product.is_discontinued
        new_status = not old_status
        product.is_discontinued = new_status

        # If marking as discontinued, also mark as inactive (recommended)
        if new_status:
            product.is_active = False

        product.updated_at = datetime.now(UTC)

        # Log change
        ip_address = get_client_ip(request)
        await log_field_change(
            db=db,
            product_id=product_id,
            field_name="is_discontinued",
            old_value=old_status,
            new_value=new_status,
            user_id=current_user.id,
            ip_address=ip_address,
        )

        await db.commit()
        await db.refresh(product)

        return {
            "status": "success",
            "data": {
                "id": product.id,
                "sku": product.sku,
                "is_discontinued": product.is_discontinued,
                "is_active": product.is_active,
                "message": f"Product {'discontinued' if new_status else 'reactivated'} successfully",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bulk-toggle-discontinued")
async def bulk_toggle_discontinued(
    product_ids: list[int],
    discontinued: bool,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Bulk update discontinued status for multiple products.

    Args:
        product_ids: List of product IDs to update
        discontinued: New discontinued status (true/false)
    """
    try:
        ip_address = get_client_ip(request)
        updated_count = 0
        failed_count = 0
        results = []

        for product_id in product_ids:
            try:
                query = select(Product).where(Product.id == product_id)
                result = await db.execute(query)
                product = result.scalar_one_or_none()

                if not product:
                    results.append(
                        {
                            "product_id": product_id,
                            "status": "error",
                            "message": "Product not found",
                        }
                    )
                    failed_count += 1
                    continue

                old_status = product.is_discontinued
                product.is_discontinued = discontinued

                # If marking as discontinued, also mark as inactive
                if discontinued:
                    product.is_active = False

                product.updated_at = datetime.now(UTC)

                # Log change
                await log_field_change(
                    db=db,
                    product_id=product_id,
                    field_name="is_discontinued",
                    old_value=old_status,
                    new_value=discontinued,
                    user_id=current_user.id,
                    ip_address=ip_address,
                )

                results.append(
                    {
                        "product_id": product_id,
                        "sku": product.sku,
                        "status": "success",
                        "is_discontinued": product.is_discontinued,
                    }
                )
                updated_count += 1

            except Exception as e:
                results.append(
                    {"product_id": product_id, "status": "error", "message": str(e)}
                )
                failed_count += 1

        await db.commit()

        return {
            "status": "success",
            "data": {
                "message": f"Updated {updated_count} products, {failed_count} failed",
                "updated_count": updated_count,
                "failed_count": failed_count,
                "results": results,
            },
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Product Reordering Endpoints
# ============================================================================


@router.post("/{product_id}/display-order")
async def update_product_display_order(
    product_id: int,
    order_request: UpdateDisplayOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a single product's display order.

    If auto_adjust is True and the order conflicts with another product,
    all products with display_order >= new_order will be incremented by 1.

    Example:
    ```json
    {
        "display_order": 5,
        "auto_adjust": true
    }
    ```
    """
    # Fetch product
    query = select(Product).where(Product.id == product_id)
    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    new_order = order_request.display_order
    old_order = product.display_order

    if order_request.auto_adjust:
        # Check if new order conflicts with existing products
        conflict_query = select(Product).where(
            Product.display_order == new_order, Product.id != product_id
        )
        conflict_result = await db.execute(conflict_query)
        conflict_product = conflict_result.scalar_one_or_none()

        if conflict_product:
            # Shift all products with display_order >= new_order by +1
            shift_query = (
                select(Product)
                .where(Product.display_order >= new_order, Product.id != product_id)
                .order_by(Product.display_order.desc())
            )

            shift_result = await db.execute(shift_query)
            products_to_shift = shift_result.scalars().all()

            for p in products_to_shift:
                p.display_order = (p.display_order or 0) + 1

    # Update the product's display order
    product.display_order = new_order
    product.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(product)

    return {
        "status": "success",
        "data": {
            "product_id": product.id,
            "sku": product.sku,
            "name": product.name,
            "old_display_order": old_order,
            "new_display_order": product.display_order,
            "message": "Display order updated successfully",
        },
    }


@router.post("/reorder")
async def reorder_products(
    reorder_request: ReorderProductsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Bulk reorder products by setting display_order for multiple products at once.

    This is useful for drag & drop operations where you want to set the exact
    order of multiple products in one request.

    Example:
    ```json
    {
        "product_orders": [
            {"product_id": 1, "display_order": 0},
            {"product_id": 5, "display_order": 1},
            {"product_id": 3, "display_order": 2},
            {"product_id": 2, "display_order": 3}
        ]
    }
    ```
    """
    updated_products = []

    for order_item in reorder_request.product_orders:
        product_id = order_item.get("product_id")
        display_order = order_item.get("display_order")

        if product_id is None or display_order is None:
            continue

        # Fetch and update product
        query = select(Product).where(Product.id == product_id)
        result = await db.execute(query)
        product = result.scalar_one_or_none()

        if product:
            product.display_order = display_order
            product.updated_at = datetime.now(UTC)
            updated_products.append(
                {
                    "product_id": product.id,
                    "sku": product.sku,
                    "display_order": product.display_order,
                }
            )

    await db.commit()

    return {
        "status": "success",
        "data": {
            "message": f"Reordered {len(updated_products)} products",
            "updated_products": updated_products,
        },
    }


@router.delete("/{product_id}/display-order")
async def remove_product_display_order(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove custom display order from a product (set to NULL).

    This will make the product fall back to default sorting.
    """
    query = select(Product).where(Product.id == product_id)
    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    old_order = product.display_order
    product.display_order = None
    product.updated_at = datetime.now(UTC)

    await db.commit()

    return {
        "status": "success",
        "data": {
            "product_id": product.id,
            "sku": product.sku,
            "old_display_order": old_order,
            "message": "Display order removed successfully",
        },
    }
