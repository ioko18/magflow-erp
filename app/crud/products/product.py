"""Product CRUD operations with comprehensive validation and eMAG integration."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.category import Category
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate, ProductValidationResult

logger = logging.getLogger(__name__)


class ProductCRUD:
    """Comprehensive CRUD operations for products."""

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        product_id: int,
        include_categories: bool = True,
    ) -> Product | None:
        """Get product by ID with optional category loading."""
        query = select(Product).where(Product.id == product_id)

        if include_categories:
            query = query.options(selectinload(Product.categories))

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_sku(
        db: AsyncSession,
        sku: str,
        include_categories: bool = False,
    ) -> Product | None:
        """Get product by SKU."""
        query = select(Product).where(Product.sku == sku.upper())

        if include_categories:
            query = query.options(selectinload(Product.categories))

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_emag_part_number_key(
        db: AsyncSession,
        part_number_key: str,
    ) -> Product | None:
        """Get product by eMAG part number key."""
        result = await db.execute(
            select(Product).where(Product.emag_part_number_key == part_number_key)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_products(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        search: str | None = None,
        is_active: bool | None = None,
        is_discontinued: bool | None = None,
        category_ids: list[int] | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        has_emag_mapping: bool | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Product], int]:
        """List products with filtering and pagination."""
        # Build base query
        query = select(Product).options(selectinload(Product.categories))
        count_query = select(func.count(Product.id))

        # Apply filters
        filters = []

        if search:
            search_term = f"%{search}%"
            filters.append(
                or_(
                    Product.name.ilike(search_term),
                    Product.sku.ilike(search_term),
                    Product.description.ilike(search_term),
                    Product.brand.ilike(search_term),
                )
            )

        if is_active is not None:
            filters.append(Product.is_active == is_active)

        if is_discontinued is not None:
            filters.append(Product.is_discontinued == is_discontinued)

        if min_price is not None:
            filters.append(Product.base_price >= min_price)

        if max_price is not None:
            filters.append(Product.base_price <= max_price)

        if has_emag_mapping is not None:
            if has_emag_mapping:
                filters.append(
                    or_(
                        Product.emag_part_number_key.isnot(None),
                        Product.ean.isnot(None),
                    )
                )
            else:
                filters.append(
                    and_(
                        Product.emag_part_number_key.is_(None),
                        Product.ean.is_(None),
                    )
                )

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        # Apply sorting
        sort_column = getattr(Product, sort_by, Product.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        query = query.offset(skip).limit(limit)

        # Execute queries
        result = await db.execute(query)
        products = list(result.scalars().all())

        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        return products, total

    @staticmethod
    async def create_product(
        db: AsyncSession,
        product_data: ProductCreate,
    ) -> Product:
        """Create a new product with validation."""
        # Check for duplicate SKU
        existing = await ProductCRUD.get_by_sku(db, product_data.sku)
        if existing:
            raise ValueError(f"Product with SKU '{product_data.sku}' already exists")

        # Check for duplicate eMAG part number key if provided
        if product_data.emag_part_number_key:
            existing_emag = await ProductCRUD.get_by_emag_part_number_key(
                db, product_data.emag_part_number_key
            )
            if existing_emag:
                raise ValueError(
                    "Product with eMAG part number key "
                    f"'{product_data.emag_part_number_key}' already exists"
                )

        # Prepare product data
        product_dict = product_data.model_dump(
            exclude={
                "category_ids",
                "auto_publish_emag",
                "characteristics",
                "images",
                "attachments",
            }
        )

        # Handle JSON fields
        if product_data.characteristics:
            product_dict["characteristics"] = json.dumps(product_data.characteristics)

        if product_data.images:
            product_dict["images"] = json.dumps(product_data.images)

        if product_data.attachments:
            product_dict["attachments"] = json.dumps(product_data.attachments)

        # Create product
        product = Product(**product_dict)
        db.add(product)
        await db.flush()

        # Add categories
        if product_data.category_ids:
            categories_result = await db.execute(
                select(Category).where(Category.id.in_(product_data.category_ids))
            )
            categories = list(categories_result.scalars().all())
            product.categories = categories

        await db.commit()
        await db.refresh(product, ["categories"])

        logger.info(f"Created product: {product.sku} (ID: {product.id})")
        return product

    @staticmethod
    async def update_product(
        db: AsyncSession,
        product_id: int,
        update_data: ProductUpdate,
    ) -> Product:
        """Update an existing product."""
        # Get existing product
        product = await ProductCRUD.get_by_id(db, product_id, include_categories=True)
        if not product:
            raise ValueError(f"Product with ID {product_id} not found")

        # Check for SKU conflicts if SKU is being updated
        if update_data.sku and update_data.sku != product.sku:
            existing = await ProductCRUD.get_by_sku(db, update_data.sku)
            if existing and existing.id != product_id:
                raise ValueError(f"Product with SKU '{update_data.sku}' already exists")

        # Prepare update data
        update_dict = update_data.model_dump(
            exclude_unset=True,
            exclude={
                "category_ids",
                "sync_to_emag",
                "characteristics",
                "images",
                "attachments",
            },
        )

        # Handle JSON fields
        if update_data.characteristics is not None:
            update_dict["characteristics"] = json.dumps(update_data.characteristics)

        if update_data.images is not None:
            update_dict["images"] = json.dumps(update_data.images)

        if update_data.attachments is not None:
            update_dict["attachments"] = json.dumps(update_data.attachments)

        # Update product fields
        for key, value in update_dict.items():
            setattr(product, key, value)

        # Update categories if provided
        if update_data.category_ids is not None:
            categories_result = await db.execute(
                select(Category).where(Category.id.in_(update_data.category_ids))
            )
            categories = list(categories_result.scalars().all())
            product.categories = categories

        await db.commit()
        await db.refresh(product, ["categories"])

        logger.info(f"Updated product: {product.sku} (ID: {product.id})")
        return product

    @staticmethod
    async def delete_product(
        db: AsyncSession,
        product_id: int,
        soft_delete: bool = True,
    ) -> bool:
        """Delete a product (soft or hard delete)."""
        product = await ProductCRUD.get_by_id(db, product_id, include_categories=False)
        if not product:
            raise ValueError(f"Product with ID {product_id} not found")

        if soft_delete:
            # Soft delete: mark as inactive and discontinued
            product.is_active = False
            product.is_discontinued = True
            await db.commit()
            logger.info(f"Soft deleted product: {product.sku} (ID: {product.id})")
        else:
            # Hard delete: remove from database
            await db.delete(product)
            await db.commit()
            logger.info(f"Hard deleted product: {product.sku} (ID: {product.id})")

        return True

    @staticmethod
    async def validate_product(
        db: AsyncSession,
        product_data: ProductCreate | ProductUpdate,
        product_id: int | None = None,
    ) -> ProductValidationResult:
        """Validate product data for completeness and eMAG readiness."""
        errors = []
        warnings = []
        missing_fields = []

        # Basic validation
        if isinstance(product_data, ProductCreate):
            if not product_data.name or len(product_data.name.strip()) < 3:
                errors.append("Product name must be at least 3 characters")

            if not product_data.sku or len(product_data.sku.strip()) < 2:
                errors.append("SKU must be at least 2 characters")

        # Price validation
        if hasattr(product_data, "base_price") and product_data.base_price is not None:
            if product_data.base_price <= 0:
                errors.append("Base price must be greater than 0")
            elif product_data.base_price < 1:
                warnings.append("Base price is very low (< 1 RON)")

        # eMAG readiness check (API v4.4.9 requirements)
        emag_ready = True

        # Required fields per eMAG API v4.4.9
        if not product_data.emag_category_id:
            missing_fields.append("emag_category_id")
            emag_ready = False

        if not product_data.base_price or product_data.base_price <= 0:
            missing_fields.append("base_price (sale_price)")
            emag_ready = False

        if not product_data.description or len(product_data.description.strip()) < 10:
            missing_fields.append("description (min 10 chars)")
            emag_ready = False

        if not product_data.brand:
            missing_fields.append("brand")
            emag_ready = False

        # Part number validation (required, max 25 chars)
        if hasattr(product_data, "part_number") and product_data.part_number:
            if len(product_data.part_number) > 25:
                errors.append("Part number must not exceed 25 characters")

        # EAN validation (recommended, category-dependent)
        if not product_data.ean:
            missing_fields.append("ean")
            warnings.append("EAN code may be mandatory depending on category")
        elif isinstance(product_data.ean, list):
            for ean in product_data.ean:
                if not (6 <= len(str(ean)) <= 14):
                    errors.append(f"EAN '{ean}' must be between 6-14 digits")

        # Warranty validation (category-dependent)
        if hasattr(product_data, "warranty_months") and (
            product_data.warranty_months is not None
            and product_data.warranty_months < 0
        ):
            errors.append("Warranty months cannot be negative")

        # Price range validation for eMAG
        if hasattr(product_data, "min_sale_price") and product_data.min_sale_price:
            if hasattr(product_data, "max_sale_price") and product_data.max_sale_price:
                if product_data.min_sale_price >= product_data.max_sale_price:
                    errors.append("min_sale_price must be less than max_sale_price")

                if product_data.base_price:
                    if product_data.base_price < product_data.min_sale_price:
                        errors.append("sale_price cannot be below min_sale_price")
                    if product_data.base_price > product_data.max_sale_price:
                        errors.append("sale_price cannot exceed max_sale_price")

        # Weight and dimensions for shipping
        if not product_data.weight_kg:
            missing_fields.append("weight_kg")
            warnings.append("Weight is required for accurate shipping calculations")

        # Dimension validation
        dimensions = [
            product_data.length_cm,
            product_data.width_cm,
            product_data.height_cm,
        ]
        if any(d is not None and d > 0 for d in dimensions):
            if not all(d is not None and d > 0 for d in dimensions):
                warnings.append("All dimensions (L/W/H) should be provided together")

        is_valid = len(errors) == 0

        return ProductValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            emag_ready=emag_ready,
            missing_fields=missing_fields,
        )

    @staticmethod
    async def bulk_create_products(
        db: AsyncSession,
        products_data: list[ProductCreate],
    ) -> tuple[list[Product], list[dict[str, Any]]]:
        """Bulk create products with error handling."""
        created_products = []
        failed_products = []

        for idx, product_data in enumerate(products_data):
            try:
                # Validate product
                validation = await ProductCRUD.validate_product(db, product_data)
                if not validation.is_valid:
                    failed_products.append(
                        {
                            "index": idx,
                            "sku": product_data.sku,
                            "errors": validation.errors,
                        }
                    )
                    continue

                # Create product
                product = await ProductCRUD.create_product(db, product_data)
                created_products.append(product)

            except Exception as e:
                logger.error(f"Failed to create product at index {idx}: {str(e)}")
                failed_products.append(
                    {
                        "index": idx,
                        "sku": product_data.sku
                        if hasattr(product_data, "sku")
                        else "unknown",
                        "errors": [str(e)],
                    }
                )

        return created_products, failed_products

    @staticmethod
    async def get_product_statistics(db: AsyncSession) -> dict[str, Any]:
        """Get product statistics."""
        # Total products
        total_result = await db.execute(select(func.count(Product.id)))
        total = total_result.scalar() or 0

        # Active products
        active_result = await db.execute(
            select(func.count(Product.id)).where(Product.is_active.is_(True))
        )
        active = active_result.scalar() or 0

        # Discontinued products
        discontinued_result = await db.execute(
            select(func.count(Product.id)).where(Product.is_discontinued.is_(True))
        )
        discontinued = discontinued_result.scalar() or 0

        # Products with eMAG mapping
        emag_mapped_result = await db.execute(
            select(func.count(Product.id)).where(
                or_(
                    Product.emag_part_number_key.isnot(None),
                    Product.ean.isnot(None),
                )
            )
        )
        emag_mapped = emag_mapped_result.scalar() or 0

        # Average price
        avg_price_result = await db.execute(
            select(func.avg(Product.base_price)).where(
                and_(
                    Product.base_price.isnot(None),
                    Product.base_price > 0,
                )
            )
        )
        avg_price = avg_price_result.scalar() or 0

        return {
            "total": total,
            "active": active,
            "inactive": total - active,
            "discontinued": discontinued,
            "emag_mapped": emag_mapped,
            "emag_unmapped": total - emag_mapped,
            "average_price": float(avg_price) if avg_price else 0,
        }
