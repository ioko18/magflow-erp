"""
This module provides REST API endpoints for managing suppliers including:
- CRUD operations for suppliers
- Product matching with 1688.com data
- Purchase order management
- Supplier performance tracking
"""

import csv
import logging
import re
from datetime import UTC, datetime
from io import BytesIO, StringIO
from typing import Any

import pandas as pd
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.product import Product
from app.models.purchase import PurchaseOrder
from app.models.supplier import Supplier, SupplierPerformance, SupplierProduct
from app.security.jwt import get_current_user
from app.services.duplicate_match_service import DuplicateMatchService
from app.services.excel_generator import ExcelGeneratorService
from app.services.jieba_matching_service import JiebaMatchingService
from app.services.product.product_matching import ProductMatchingService
from app.services.suppliers.supplier_service import SupplierService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get("", response_model=dict[str, Any])
async def list_suppliers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    country: str | None = Query(None),
    active_only: bool = Query(True),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List suppliers with optional filtering."""

    # Build query
    query = select(Supplier)

    if active_only:
        query = query.where(Supplier.is_active)

    if country:
        query = query.where(Supplier.country == country)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                Supplier.name.ilike(search_filter),
                Supplier.contact_person.ilike(search_filter),
                Supplier.email.ilike(search_filter),
            )
        )

    # Execute query with pagination
    # Sort by display_order (manual order), then by name as fallback
    result = await db.execute(
        query.order_by(Supplier.display_order, Supplier.name).offset(skip).limit(limit)
    )
    suppliers = result.scalars().all()

    # Get total count for pagination
    count_query = select(func.count(Supplier.id))
    if active_only:
        count_query = count_query.where(Supplier.is_active)
    if country:
        count_query = count_query.where(Supplier.country == country)
    if search:
        count_query = count_query.where(
            or_(
                Supplier.name.ilike(search_filter),
                Supplier.contact_person.ilike(search_filter),
                Supplier.email.ilike(search_filter),
            )
        )

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    return {
        "status": "success",
        "data": {
            "suppliers": [
                {
                    "id": supplier.id,
                    "name": supplier.name,
                    "country": supplier.country,
                    "contact_person": supplier.contact_person,
                    "email": supplier.email,
                    "phone": supplier.phone,
                    "lead_time_days": supplier.lead_time_days,
                    "rating": supplier.rating,
                    "is_active": supplier.is_active,
                    "total_orders": supplier.total_orders,
                    "display_order": supplier.display_order,
                    "created_at": supplier.created_at.isoformat()
                    if supplier.created_at
                    else None,
                }
                for supplier in suppliers
            ],
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": skip + limit < total,
            },
        },
    }


@router.post("", response_model=dict[str, Any])
async def create_supplier(
    supplier_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a new supplier."""

    supplier_service = SupplierService(db)

    try:
        supplier = await supplier_service.create_supplier(supplier_data)
        await db.commit()

        return {
            "status": "success",
            "data": {
                "id": supplier.id,
                "name": supplier.name,
                "country": supplier.country,
                "message": "Supplier created successfully",
            },
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{supplier_id}", response_model=dict[str, Any])
async def get_supplier(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get detailed supplier information."""

    query = select(Supplier).where(Supplier.id == supplier_id)
    result = await db.execute(query)
    supplier = result.scalar_one_or_none()

    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Get supplier performance metrics
    perf_query = (
        select(SupplierPerformance)
        .where(SupplierPerformance.supplier_id == supplier_id)
        .order_by(SupplierPerformance.created_at.desc())
        .limit(10)
    )
    perf_result = await db.execute(perf_query)
    performance_records = perf_result.scalars().all()

    # Get recent purchase orders
    po_query = (
        select(PurchaseOrder)
        .where(PurchaseOrder.supplier_id == supplier_id)
        .order_by(PurchaseOrder.created_at.desc())
        .limit(5)
    )
    po_result = await db.execute(po_query)
    purchase_orders = po_result.scalars().all()

    return {
        "status": "success",
        "data": {
            "supplier": {
                "id": supplier.id,
                "name": supplier.name,
                "country": supplier.country,
                "contact_person": supplier.contact_person,
                "email": supplier.email,
                "phone": supplier.phone,
                "website": supplier.website,
                "lead_time_days": supplier.lead_time_days,
                "min_order_value": supplier.min_order_value,
                "min_order_qty": supplier.min_order_qty,
                "currency": supplier.currency,
                "payment_terms": supplier.payment_terms,
                "specializations": supplier.specializations,
                "product_categories": supplier.product_categories,
                "rating": supplier.rating,
                "total_orders": supplier.total_orders,
                "on_time_delivery_rate": supplier.on_time_delivery_rate,
                "quality_score": supplier.quality_score,
                "is_active": supplier.is_active,
                "notes": supplier.notes,
                "tags": supplier.tags,
                "created_at": supplier.created_at.isoformat()
                if supplier.created_at
                else None,
                "updated_at": supplier.updated_at.isoformat()
                if supplier.updated_at
                else None,
            },
            "performance": [
                {
                    "metric_type": record.metric_type,
                    "metric_value": record.metric_value,
                    "created_at": record.created_at.isoformat()
                    if record.created_at
                    else None,
                    "notes": record.notes,
                }
                for record in performance_records
            ],
            "recent_orders": [
                {
                    "id": order.id,
                    "order_number": order.order_number,
                    "status": order.status,
                    "total_value": order.total_value,
                    "order_date": order.order_date.isoformat()
                    if order.order_date
                    else None,
                    "expected_delivery_date": order.expected_delivery_date.isoformat()
                    if order.expected_delivery_date
                    else None,
                }
                for order in purchase_orders
            ],
        },
    }


@router.put("/{supplier_id}", response_model=dict[str, Any])
async def update_supplier(
    supplier_id: int,
    update_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update supplier information."""

    supplier_service = SupplierService(db)

    try:
        supplier = await supplier_service.update_supplier(supplier_id, update_data)
        await db.commit()

        return {
            "status": "success",
            "data": {
                "id": supplier.id,
                "name": supplier.name,
                "message": "Supplier updated successfully",
            },
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/{supplier_id}", response_model=dict[str, Any])
async def delete_supplier(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Soft delete a supplier."""

    supplier_service = SupplierService(db)

    try:
        await supplier_service.delete_supplier(supplier_id)
        await db.commit()

        return {
            "status": "success",
            "data": {"message": "Supplier deleted successfully"},
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch("/batch-update-order")
async def batch_update_supplier_order(
    order_data: dict[str, list[dict[str, int]]],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Batch update display order for suppliers.

    Request body:
    {
        "suppliers": [
            {"id": 1, "display_order": 1},
            {"id": 2, "display_order": 2},
            ...
        ]
    }
    """

    try:
        suppliers_order = order_data.get("suppliers", [])

        if not suppliers_order:
            raise HTTPException(status_code=422, detail="suppliers list is required")

        # Update each supplier's display_order
        updated_count = 0
        for supplier_data in suppliers_order:
            supplier_id = supplier_data.get("id")
            display_order = supplier_data.get("display_order")

            if supplier_id is None or display_order is None:
                continue

            # Update supplier
            stmt = (
                update(Supplier)
                .where(Supplier.id == supplier_id)
                .values(display_order=display_order)
            )

            result = await db.execute(stmt)
            if result.rowcount > 0:
                updated_count += 1

        await db.commit()

        return {
            "status": "success",
            "data": {
                "updated_count": updated_count,
                "message": f"Updated display order for {updated_count} suppliers",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{supplier_id}/products/import")
async def import_supplier_products(
    supplier_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Import products from 1688.com CSV/Excel file for a supplier."""

    # Validate file type
    if not file.filename.endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(
            status_code=400, detail="Only CSV and Excel files are supported"
        )

    # Validate supplier exists
    supplier_query = select(Supplier).where(Supplier.id == supplier_id)
    supplier_result = await db.execute(supplier_query)
    supplier = supplier_result.scalar_one_or_none()

    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Process file in background
    background_tasks.add_task(
        process_1688_import,
        supplier_id,
        file.file.read(),
        file.filename,
        current_user.id,
    )

    return {
        "status": "success",
        "data": {
            "message": "File uploaded successfully. Processing will start in background.",
            "supplier_id": supplier_id,
            "filename": file.filename,
        },
    }


@router.get("/{supplier_id}/products")
async def get_supplier_products(
    supplier_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    confirmed_only: bool = Query(False),
    status: str | None = Query(None),  # 'all', 'unmatched', 'pending', 'confirmed'
    search: str | None = Query(None),
    include_tokens: bool = Query(
        False, description="Include common tokens in response for matched products"
    ),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all products for a specific supplier with optional status filtering and token analysis."""

    # Build query
    query = select(SupplierProduct).where(SupplierProduct.supplier_id == supplier_id)

    # Apply status filter
    if status == "unmatched":
        query = query.where(SupplierProduct.local_product_id.is_(None))
    elif status == "pending":
        query = query.where(
            and_(
                SupplierProduct.local_product_id.isnot(None),
                ~SupplierProduct.manual_confirmed,
            )
        )
    elif status == "confirmed":
        query = query.where(SupplierProduct.manual_confirmed)
    # 'all' or None - no additional filter

    # Legacy parameter support
    if confirmed_only and not status:
        query = query.where(SupplierProduct.manual_confirmed.is_(True))

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                SupplierProduct.supplier_product_name.ilike(search_filter),
            )
        )

    # Get total count with same filters
    count_query = select(func.count(SupplierProduct.id)).where(
        SupplierProduct.supplier_id == supplier_id
    )

    # Apply same status filter to count
    if status == "unmatched":
        count_query = count_query.where(SupplierProduct.local_product_id.is_(None))
    elif status == "pending":
        count_query = count_query.where(
            and_(
                SupplierProduct.local_product_id.isnot(None),
                ~SupplierProduct.manual_confirmed,
            )
        )
    elif status == "confirmed":
        count_query = count_query.where(SupplierProduct.manual_confirmed)

    # Legacy parameter support
    if confirmed_only and not status:
        count_query = count_query.where(SupplierProduct.manual_confirmed.is_(True))

    if search:
        count_query = count_query.where(
            SupplierProduct.supplier_product_name.ilike(search_filter)
        )

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Execute query with pagination
    result = await db.execute(
        query.order_by(SupplierProduct.created_at.desc()).offset(skip).limit(limit)
    )
    supplier_products = result.scalars().all()

    # Load supplier info for supplier_name
    supplier_query = select(Supplier.name).where(Supplier.id == supplier_id)
    supplier_result = await db.execute(supplier_query)
    supplier_name = supplier_result.scalar()

    # Initialize jieba service if tokens are requested
    jieba_service = None
    if include_tokens:
        jieba_service = JiebaMatchingService(db)

    # Load related data
    products_data = []
    for sp in supplier_products:
        # Load local product - only specific fields to avoid relationship loading issues
        local_product_query = select(
            Product.id,
            Product.name,
            Product.sku,
            Product.brand,
            Product.image_url,
            Product.chinese_name,
        ).where(Product.id == sp.local_product_id)
        local_product_result = await db.execute(local_product_query)
        local_product_row = local_product_result.first()

        # Normalize confidence_score to 0-1 range
        # Some old data might be stored as 0-100, normalize it
        confidence_normalized = sp.confidence_score
        if confidence_normalized and confidence_normalized > 1:
            confidence_normalized = confidence_normalized / 100.0

        # Build base product data
        product_dict = {
            "id": sp.id,
            "supplier_id": sp.supplier_id,
            "supplier_name": supplier_name,
            "supplier_product_name": sp.supplier_product_name,
            "supplier_product_chinese_name": sp.supplier_product_chinese_name,
            "supplier_product_specification": sp.supplier_product_specification,
            "supplier_product_url": sp.supplier_product_url,
            "supplier_image_url": sp.supplier_image_url,
            "supplier_price": sp.supplier_price,
            "supplier_currency": sp.supplier_currency,
            "local_product_id": sp.local_product_id,
            "confidence_score": confidence_normalized,  # Normalized to 0-1
            "manual_confirmed": sp.manual_confirmed,
            "is_active": sp.is_active,
            "import_source": sp.import_source,
            "last_price_update": sp.last_price_update.isoformat()
            if sp.last_price_update
            else None,
            "created_at": sp.created_at.isoformat() if sp.created_at else None,
            "local_product": {
                "id": local_product_row[0],
                "name": local_product_row[1],
                "sku": local_product_row[2],
                "brand": local_product_row[3],
                "image_url": local_product_row[4],
                "chinese_name": local_product_row[5],
                "category": None,  # Not available in this query
            }
            if local_product_row
            else None,
        }

        # Calculate and include common tokens if requested and product is matched
        if (
            include_tokens
            and jieba_service
            and sp.local_product_id
            and local_product_row
        ):
            try:
                # Get local product chinese name
                local_chinese_name = local_product_row[5]  # chinese_name

                # Get supplier product name (prefer chinese)
                supplier_product_name = (
                    sp.supplier_product_chinese_name or sp.supplier_product_name
                )

                if local_chinese_name and supplier_product_name:
                    # Tokenize both names
                    search_tokens = set(
                        jieba_service.tokenize_clean(local_chinese_name)
                    )
                    product_tokens = set(
                        jieba_service.tokenize_clean(supplier_product_name)
                    )

                    # Calculate common tokens
                    common_tokens = search_tokens & product_tokens

                    # Add token information to response
                    product_dict["common_tokens"] = sorted(common_tokens)
                    product_dict["common_tokens_count"] = len(common_tokens)
                    product_dict["search_tokens_count"] = len(search_tokens)
                    product_dict["product_tokens_count"] = len(product_tokens)
            except Exception as e:
                # If token calculation fails, just log and continue without tokens
                import logging

                logging.warning(f"Failed to calculate tokens for product {sp.id}: {e}")

        products_data.append(product_dict)

    return {
        "status": "success",
        "data": {
            "products": products_data,
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": skip + limit < total,
            },
        },
    }


@router.get("/{supplier_id}/products/statistics")
async def get_supplier_products_statistics(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get statistics for supplier products."""

    # Total products
    total_query = select(func.count(SupplierProduct.id)).where(
        SupplierProduct.supplier_id == supplier_id
    )
    total_result = await db.execute(total_query)
    total_products = total_result.scalar()

    # Confirmed products
    confirmed_query = select(func.count(SupplierProduct.id)).where(
        and_(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.manual_confirmed.is_(True),
        )
    )
    confirmed_result = await db.execute(confirmed_query)
    confirmed_products = confirmed_result.scalar()

    # Active products
    active_query = select(func.count(SupplierProduct.id)).where(
        and_(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.is_active.is_(True),
        )
    )
    active_result = await db.execute(active_query)
    active_products = active_result.scalar()

    # Average confidence score
    avg_confidence_query = select(func.avg(SupplierProduct.confidence_score)).where(
        SupplierProduct.supplier_id == supplier_id
    )
    avg_confidence_result = await db.execute(avg_confidence_query)
    avg_confidence = avg_confidence_result.scalar() or 0.0

    return {
        "status": "success",
        "data": {
            "total_products": total_products,
            "confirmed_products": confirmed_products,
            "pending_products": total_products - confirmed_products,
            "active_products": active_products,
            "average_confidence": float(avg_confidence),
            "confirmation_rate": (confirmed_products / total_products * 100)
            if total_products > 0
            else 0.0,
        },
    }


@router.get("/{supplier_id}/products/match")
async def get_product_matches(
    supplier_id: int,
    confidence_threshold: float = Query(0.5, ge=0.0, le=1.0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get product matching suggestions for a supplier."""

    matching_service = ProductMatchingService(db)

    try:
        matches = await matching_service.find_matches_for_supplier(
            supplier_id, confidence_threshold=confidence_threshold, limit=limit
        )

        return {
            "status": "success",
            "data": {
                "matches": [
                    {
                        "id": match.id,
                        "local_product": {
                            "id": match.local_product.id,
                            "name": match.local_product.name,
                            "sku": match.local_product.sku,
                            "brand": match.local_product.brand,
                        },
                        "supplier_product": {
                            "name_chinese": match.supplier_product_name,
                            "price": match.supplier_price,
                            "currency": match.supplier_currency,
                            "image_url": match.supplier_image_url,
                            "url": match.supplier_product_url,
                        },
                        "confidence_score": match.confidence_score,
                        "manual_confirmed": match.manual_confirmed,
                        "created_at": match.created_at.isoformat()
                        if match.created_at
                        else None,
                    }
                    for match in matches
                ],
                "total_matches": len(matches),
                "threshold": confidence_threshold,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{supplier_id}/products/{match_id}/confirm")
async def confirm_product_match(
    supplier_id: int,
    match_id: int,
    confirmation_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Confirm or reject a product match."""

    confirmed = confirmation_data.get("confirmed", True)
    matching_service = ProductMatchingService(db)

    try:
        if confirmed:
            await matching_service.confirm_match(match_id, current_user.id)
        else:
            await matching_service.reject_match(match_id)

        await db.commit()

        return {
            "status": "success",
            "data": {
                "message": "Match confirmed successfully"
                if confirmed
                else "Match rejected"
            },
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{supplier_id}/matching/statistics")
async def get_matching_statistics(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get matching statistics for a supplier."""

    # Total matches
    total_query = select(func.count(SupplierProduct.id)).where(
        SupplierProduct.supplier_id == supplier_id
    )
    total_result = await db.execute(total_query)
    total_matches = total_result.scalar()

    # Unmatched products (no local_product_id)
    unmatched_query = select(func.count(SupplierProduct.id)).where(
        and_(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.local_product_id.is_(None),
        )
    )
    unmatched_result = await db.execute(unmatched_query)
    total_unmatched = unmatched_result.scalar()

    # Matched products (has local_product_id)
    total_matched = total_matches - total_unmatched

    # Confirmed matches
    confirmed_query = select(func.count(SupplierProduct.id)).where(
        and_(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.manual_confirmed.is_(True),
            SupplierProduct.local_product_id.isnot(None),
        )
    )
    confirmed_result = await db.execute(confirmed_query)
    confirmed_matches = confirmed_result.scalar()

    # Pending confirmation (matched but not confirmed)
    pending_confirmation = total_matched - confirmed_matches

    # Average confidence
    avg_query = select(func.avg(SupplierProduct.confidence_score)).where(
        and_(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.local_product_id.isnot(None),
        )
    )
    avg_result = await db.execute(avg_query)
    average_confidence = avg_result.scalar() or 0.0

    return {
        "status": "success",
        "data": {
            "total_unmatched": total_unmatched,
            "total_matched": total_matched,
            "pending_confirmation": pending_confirmation,
            "confirmed_matches": confirmed_matches,
            "average_confidence": float(average_confidence),
        },
    }


@router.get("/{supplier_id}/products/unmatched")
async def get_unmatched_products(
    supplier_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get unmatched supplier products (products without local_product_id)."""

    # Build query for unmatched products
    query = select(SupplierProduct).where(
        and_(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.local_product_id.is_(None),
        )
    )

    # Get total count
    count_query = select(func.count(SupplierProduct.id)).where(
        and_(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.local_product_id.is_(None),
        )
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Execute query with pagination
    result = await db.execute(
        query.order_by(SupplierProduct.created_at.desc()).offset(skip).limit(limit)
    )
    supplier_products = result.scalars().all()

    # Get supplier info
    supplier_query = select(Supplier).where(Supplier.id == supplier_id)
    supplier_result = await db.execute(supplier_query)
    supplier = supplier_result.scalar_one_or_none()

    # Load related data
    products_data = []
    for sp in supplier_products:
        products_data.append(
            {
                "id": sp.id,
                "supplier_id": sp.supplier_id,
                "supplier_name": supplier.name if supplier else "Unknown",
                "supplier_product_name": sp.supplier_product_name,
                "supplier_product_url": sp.supplier_product_url,
                "supplier_image_url": sp.supplier_image_url,
                "supplier_price": sp.supplier_price,
                "supplier_currency": sp.supplier_currency,
                "confidence_score": sp.confidence_score,
                "manual_confirmed": sp.manual_confirmed,
                "local_product_id": sp.local_product_id,
                "is_active": sp.is_active,
                "created_at": sp.created_at.isoformat() if sp.created_at else None,
            }
        )

    return {
        "status": "success",
        "data": {
            "products": products_data,
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": skip + limit < total,
            },
        },
    }


@router.post("/{supplier_id}/products/{product_id}/match")
async def match_supplier_product(
    supplier_id: int,
    product_id: int,
    match_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Manually match a supplier product to a local product."""

    try:
        # Get supplier product
        sp_query = select(SupplierProduct).where(
            and_(
                SupplierProduct.id == product_id,
                SupplierProduct.supplier_id == supplier_id,
            )
        )
        sp_result = await db.execute(sp_query)
        supplier_product = sp_result.scalar_one_or_none()

        if not supplier_product:
            raise HTTPException(status_code=404, detail="Supplier product not found")

        # Update supplier product with match
        supplier_product.local_product_id = match_data.get("local_product_id")
        supplier_product.confidence_score = match_data.get("confidence_score", 1.0)
        supplier_product.manual_confirmed = match_data.get("manual_confirmed", True)
        supplier_product.confirmed_by = current_user.id
        supplier_product.confirmed_at = datetime.now(UTC)

        await db.commit()

        return {
            "status": "success",
            "data": {
                "message": "Product matched successfully",
                "supplier_product_id": product_id,
                "local_product_id": match_data.get("local_product_id"),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/{supplier_id}/products/{product_id}/match")
async def unmatch_supplier_product(
    supplier_id: int,
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Remove match between supplier product and local product."""

    try:
        # Get supplier product
        query = select(SupplierProduct).where(
            and_(
                SupplierProduct.supplier_id == supplier_id,
                SupplierProduct.id == product_id,
            )
        )
        result = await db.execute(query)
        supplier_product = result.scalar_one_or_none()

        if not supplier_product:
            raise HTTPException(status_code=404, detail="Supplier product not found")

        # Check if product is already unmatched
        if supplier_product.local_product_id is None:
            logger.info(
                f"Product {product_id} from supplier {supplier_id} is already unmatched"
            )
            return {
                "status": "success",
                "data": {
                    "message": "Product is already unmatched",
                    "supplier_product_id": product_id,
                },
            }

        # Remove match
        supplier_product.local_product_id = None
        supplier_product.confidence_score = (
            0.0  # Must be 0.0, not None (NOT NULL constraint)
        )
        supplier_product.manual_confirmed = (
            False  # Must be False, not None (NOT NULL constraint)
        )
        supplier_product.confirmed_by = None
        supplier_product.confirmed_at = None
        # updated_at will be set automatically by SQLAlchemy's onupdate

        await db.commit()

        logger.info(
            f"Successfully unmatched product {product_id} from supplier {supplier_id}"
        )

        return {
            "status": "success",
            "data": {
                "message": "Match removed successfully",
                "supplier_product_id": product_id,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error unmatching product {product_id} from supplier {supplier_id}: {str(e)}",
            exc_info=True,
        )
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{supplier_id}/products/auto-match")
async def auto_match_products(
    supplier_id: int,
    threshold: float = Query(0.3, ge=0.1, le=1.0),
    auto_confirm_threshold: float = Query(0.7, ge=0.5, le=1.0),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    DISABLED: Auto-match functionality has been disabled.
    Only manual matching is allowed.
    """
    raise HTTPException(
        status_code=410,
        detail="Auto-match functionality has been disabled. Please use manual matching only.",
    )


@router.post("/{supplier_id}/products/jieba-search")
async def jieba_search_products(
    supplier_id: int,
    search_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Search supplier products using jieba tokenization.

    Request body:
    {
        "search_term": "电源适配器",
        "threshold": 0.3,
        "limit": 50
    }
    """

    try:
        search_term = search_data.get("search_term", "")
        threshold = search_data.get("threshold", 0.3)
        limit = search_data.get("limit", 50)

        if not search_term:
            raise HTTPException(status_code=422, detail="search_term is required")

        jieba_service = JiebaMatchingService(db)

        matches = await jieba_service.search_supplier_products(
            search_term=search_term,
            threshold=threshold,
            limit=limit,
            supplier_id=supplier_id,
        )

        return {
            "status": "success",
            "data": {
                "search_term": search_term,
                "threshold": threshold,
                "matches_count": len(matches),
                "matches": matches,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{supplier_id}/products/{product_id}/jieba-suggestions")
async def get_jieba_match_suggestions(
    supplier_id: int,
    product_id: int,
    threshold: float = Query(0.3, ge=0.1, le=1.0),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get jieba-based match suggestions for a specific supplier product.

    Returns top N local products that match based on Chinese tokenization.
    """

    try:
        jieba_service = JiebaMatchingService(db)

        matches = await jieba_service.find_matches_for_supplier_product(
            supplier_product_id=product_id, threshold=threshold, limit=limit
        )

        return {
            "status": "success",
            "data": {
                "supplier_product_id": product_id,
                "threshold": threshold,
                "suggestions_count": len(matches),
                "suggestions": matches,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{supplier_id}/products/bulk-confirm")
async def bulk_confirm_matches(
    supplier_id: int,
    product_data: dict[str, list[int]],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Bulk confirm multiple product matches in one transaction.

    This is more efficient than confirming products one by one.
    """

    try:
        product_ids = product_data.get("product_ids", [])

        if not product_ids:
            raise HTTPException(status_code=422, detail="product_ids list is required")

        # Verify all products belong to this supplier
        verify_query = select(SupplierProduct).where(
            and_(
                SupplierProduct.id.in_(product_ids),
                SupplierProduct.supplier_id == supplier_id,
            )
        )
        verify_result = await db.execute(verify_query)
        products = verify_result.scalars().all()

        if len(products) != len(product_ids):
            raise HTTPException(
                status_code=404,
                detail="Some products not found or don't belong to this supplier",
            )

        # Bulk update using SQLAlchemy update statement
        stmt = (
            update(SupplierProduct)
            .where(
                and_(
                    SupplierProduct.id.in_(product_ids),
                    SupplierProduct.supplier_id == supplier_id,
                    SupplierProduct.local_product_id.isnot(None),
                )
            )
            .values(manual_confirmed=True)
        )

        result = await db.execute(stmt)
        await db.commit()

        updated_count = result.rowcount

        return {
            "status": "success",
            "data": {
                "updated_count": updated_count,
                "message": f"Confirmed {updated_count} product matches",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{supplier_id}/products/bulk-unmatch")
async def bulk_unmatch_products(
    supplier_id: int,
    product_data: dict[str, list[int]],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Bulk unmatch multiple products in one transaction."""

    try:
        product_ids = product_data.get("product_ids", [])

        if not product_ids:
            raise HTTPException(status_code=422, detail="product_ids list is required")

        # Bulk update to remove matches
        stmt = (
            update(SupplierProduct)
            .where(
                and_(
                    SupplierProduct.id.in_(product_ids),
                    SupplierProduct.supplier_id == supplier_id,
                )
            )
            .values(
                local_product_id=None,
                confidence_score=0.0,  # Must be 0.0, not None (NOT NULL constraint)
                manual_confirmed=False,
            )
        )

        result = await db.execute(stmt)
        await db.commit()

        updated_count = result.rowcount

        return {
            "status": "success",
            "data": {
                "updated_count": updated_count,
                "message": f"Unmatched {updated_count} products",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{supplier_id}/products/import-excel")
async def import_supplier_products_from_excel(
    supplier_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Import supplier products from Excel file with scraping data.

    Expected Excel columns:
    - url_image_scrapping: Product image URL
    - url_product_scrapping: Product page URL
    - chinese_name_scrapping: Chinese product name
    - price_scrapping: Price in format "CN ¥ 2.45"
    """

    try:
        # Verify supplier exists
        supplier_query = select(Supplier).where(Supplier.id == supplier_id)
        supplier_result = await db.execute(supplier_query)
        supplier = supplier_result.scalar_one_or_none()

        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

        # Read Excel file
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))

        # Validate required columns
        required_columns = [
            "url_image_scrapping",
            "url_product_scrapping",
            "chinese_name_scrapping",
            "price_scrapping",
        ]

        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}",
            )

        # Process each row
        imported_count = 0
        skipped_count = 0
        errors = []

        for index, row in df.iterrows():
            try:
                # Parse price from "CN ¥ 2.45" format
                price_str = str(row["price_scrapping"])
                price_match = re.search(r"[\d,]+\.?\d*", price_str.replace(",", ""))

                if price_match:
                    price = float(price_match.group())
                else:
                    errors.append(
                        f"Row {index + 2}: Invalid price format '{price_str}'"
                    )
                    skipped_count += 1
                    continue

                # Check if product already exists (by URL)
                existing_query = select(SupplierProduct).where(
                    and_(
                        SupplierProduct.supplier_id == supplier_id,
                        SupplierProduct.supplier_product_url
                        == str(row["url_product_scrapping"]),
                    )
                )
                existing_result = await db.execute(existing_query)
                existing_product = existing_result.scalar_one_or_none()

                if existing_product:
                    # Update existing product
                    existing_product.supplier_product_name = str(
                        row["chinese_name_scrapping"]
                    )
                    existing_product.supplier_image_url = str(
                        row["url_image_scrapping"]
                    )
                    existing_product.supplier_price = price
                    existing_product.supplier_currency = "CNY"
                    existing_product.updated_at = datetime.now(UTC).replace(tzinfo=None)
                else:
                    # Create new product
                    new_product = SupplierProduct(
                        supplier_id=supplier_id,
                        supplier_product_name=str(row["chinese_name_scrapping"]),
                        supplier_product_url=str(row["url_product_scrapping"]),
                        supplier_image_url=str(row["url_image_scrapping"]),
                        supplier_price=price,
                        supplier_currency="CNY",
                        is_active=True,
                        created_at=datetime.now(UTC).replace(tzinfo=None),
                        updated_at=datetime.now(UTC).replace(tzinfo=None),
                    )
                    db.add(new_product)

                imported_count += 1

            except Exception as e:
                errors.append(f"Row {index + 2}: {str(e)}")
                skipped_count += 1
                continue

        await db.commit()

        return {
            "status": "success",
            "data": {
                "message": f"Import completed: {imported_count} products imported, {skipped_count} skipped",
                "imported_count": imported_count,
                "skipped_count": skipped_count,
                "total_rows": len(df),
                "errors": errors[:10] if errors else [],  # Return first 10 errors
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}") from e


@router.get("/{supplier_id}/orders/generate")
async def generate_supplier_order_excel(
    supplier_id: int,
    product_ids: list[int] = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Generate Excel order file for selected products."""

    excel_service = ExcelGeneratorService()

    try:
        # Get supplier and products
        supplier_query = select(Supplier).where(Supplier.id == supplier_id)
        supplier_result = await db.execute(supplier_query)
        supplier = supplier_result.scalar_one_or_none()

        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

        # Get supplier-product mappings for selected products
        mappings_query = select(SupplierProduct).where(
            and_(
                SupplierProduct.supplier_id == supplier_id,
                SupplierProduct.local_product_id.in_(product_ids),
                SupplierProduct.manual_confirmed,
            )
        )
        mappings_result = await db.execute(mappings_query)
        mappings = mappings_result.scalars().all()

        if not mappings:
            raise HTTPException(
                status_code=400,
                detail="No confirmed supplier mappings found for selected products",
            )

        # Generate Excel
        excel_data = await excel_service.generate_supplier_order_excel(
            supplier, mappings
        )

        return {
            "status": "success",
            "data": {
                "filename": f"order_{supplier.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "excel_data": excel_data,
                "supplier_id": supplier_id,
                "product_count": len(mappings),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{supplier_id}/performance")
async def get_supplier_performance(
    supplier_id: int,
    period_days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get supplier performance metrics."""

    supplier_service = SupplierService(db)

    try:
        performance = await supplier_service.get_supplier_performance(
            supplier_id, period_days=period_days
        )

        return {"status": "success", "data": performance}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{supplier_id}/products/duplicates")
async def get_duplicate_matches(
    supplier_id: int,
    min_duplicates: int = Query(2, ge=2),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get all duplicate matches for a supplier.

    Returns local products that have multiple supplier products matched.
    """

    try:
        duplicate_service = DuplicateMatchService(db)

        duplicates = await duplicate_service.find_duplicate_matches(
            supplier_id=supplier_id, min_duplicates=min_duplicates
        )

        stats = await duplicate_service.get_duplicate_statistics(
            supplier_id=supplier_id
        )

        return {
            "status": "success",
            "data": {
                "duplicates": duplicates,
                "statistics": stats,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{supplier_id}/products/duplicates/resolve")
async def resolve_duplicate_matches(
    supplier_id: int,
    resolve_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Resolve duplicate matches using specified strategy.

    Request body:
    {
        "strategy": "highest_confidence" | "most_recent" | "manual_confirmed" | "google_sheets",
        "dry_run": false
    }
    """

    try:
        strategy = resolve_data.get("strategy", "highest_confidence")
        dry_run = resolve_data.get("dry_run", False)

        duplicate_service = DuplicateMatchService(db)

        result = await duplicate_service.resolve_all_duplicates(
            supplier_id=supplier_id, strategy=strategy, dry_run=dry_run
        )

        return {"status": "success", "data": result}

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{supplier_id}/products/{product_id}/check-duplicate")
async def check_duplicate_before_match(
    supplier_id: int,
    product_id: int,
    match_data: dict[str, int],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Check if matching would create a duplicate.

    Request body:
    {
        "local_product_id": 123
    }
    """

    try:
        local_product_id = match_data.get("local_product_id")

        if not local_product_id:
            raise HTTPException(status_code=422, detail="local_product_id is required")

        duplicate_service = DuplicateMatchService(db)

        result = await duplicate_service.prevent_duplicate_match(
            supplier_product_id=product_id, local_product_id=local_product_id
        )

        return {"status": "success", "data": result}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{supplier_id}/products/export")
async def export_supplier_products(
    supplier_id: int,
    format: str = Query("csv", regex="^(csv|excel)$"),
    status: str | None = Query(None),
    include_tokens: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Export supplier products in CSV or Excel format."""

    try:
        # Build query with same filters as get_supplier_products
        query = select(SupplierProduct).where(
            SupplierProduct.supplier_id == supplier_id
        )

        # Apply status filter
        if status == "unmatched":
            query = query.where(SupplierProduct.local_product_id.is_(None))
        elif status == "pending":
            query = query.where(
                and_(
                    SupplierProduct.local_product_id.isnot(None),
                    ~SupplierProduct.manual_confirmed,
                )
            )
        elif status == "confirmed":
            query = query.where(SupplierProduct.manual_confirmed)

        result = await db.execute(query.order_by(SupplierProduct.created_at.desc()))
        products = result.scalars().all()

        # Get supplier name
        supplier_query = select(Supplier.name).where(Supplier.id == supplier_id)
        supplier_result = await db.execute(supplier_query)
        supplier_name = supplier_result.scalar()

        if format == "csv":
            # Generate CSV
            output = StringIO()
            writer = csv.writer(output)

            # Header
            headers = [
                "ID",
                "Supplier",
                "Product Name",
                "Chinese Name",
                "Specification",
                "Price",
                "Currency",
                "URL",
                "Image URL",
                "Confidence Score",
                "Status",
                "Local Product ID",
                "Local Product Name",
                "Created At",
            ]

            if include_tokens:
                headers.extend(
                    ["Common Tokens", "Common Tokens Count", "Search Tokens Count"]
                )

            writer.writerow(headers)

            # Data rows
            for product in products:
                # Get local product if exists
                local_product_name = None
                if product.local_product_id:
                    local_product_query = select(Product.name).where(
                        Product.id == product.local_product_id
                    )
                    local_product_result = await db.execute(local_product_query)
                    local_product_name = local_product_result.scalar()

                status_text = (
                    "Confirmed"
                    if product.manual_confirmed
                    else ("Pending" if product.local_product_id else "Unmatched")
                )

                row = [
                    product.id,
                    supplier_name,
                    product.supplier_product_name,
                    product.supplier_product_chinese_name or "",
                    product.supplier_product_specification or "",
                    product.supplier_price,
                    product.supplier_currency,
                    product.supplier_product_url,
                    product.supplier_image_url,
                    product.confidence_score or "",
                    status_text,
                    product.local_product_id or "",
                    local_product_name or "",
                    product.created_at.isoformat() if product.created_at else "",
                ]

                if include_tokens:
                    # Calculate tokens if requested
                    row.extend(["", "", ""])  # Placeholder for now

                writer.writerow(row)

            output.seek(0)
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=products_{supplier_id}.csv"
                },
            )

        else:  # excel format
            # For Excel, we'd use openpyxl or similar
            # For now, return CSV as fallback
            return {"status": "error", "message": "Excel export not yet implemented"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/products/{local_product_id}/price-comparison")
async def get_price_comparison(
    local_product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get price comparison across all suppliers for a local product."""

    try:
        # Get all supplier products for this local product
        query = (
            select(SupplierProduct)
            .where(SupplierProduct.local_product_id == local_product_id)
            .order_by(SupplierProduct.supplier_price.asc())
        )

        result = await db.execute(query)
        supplier_products = result.scalars().all()

        if not supplier_products:
            return {
                "status": "success",
                "data": {
                    "local_product_id": local_product_id,
                    "suppliers": [],
                    "price_range": None,
                },
            }

        # Get supplier names
        suppliers_data = []
        for sp in supplier_products:
            supplier_query = select(Supplier.name).where(Supplier.id == sp.supplier_id)
            supplier_result = await db.execute(supplier_query)
            supplier_name = supplier_result.scalar()

            suppliers_data.append(
                {
                    "supplier_id": sp.supplier_id,
                    "supplier_name": supplier_name,
                    "supplier_product_id": sp.id,
                    "price": float(sp.supplier_price),
                    "currency": sp.supplier_currency,
                    "is_cheapest": sp.supplier_price
                    == supplier_products[0].supplier_price,
                    "url": sp.supplier_product_url,
                    "confidence_score": float(sp.confidence_score)
                    if sp.confidence_score
                    else None,
                    "manual_confirmed": sp.manual_confirmed,
                }
            )

        prices = [float(sp.supplier_price) for sp in supplier_products]

        return {
            "status": "success",
            "data": {
                "local_product_id": local_product_id,
                "suppliers": suppliers_data,
                "price_range": {
                    "min": min(prices),
                    "max": max(prices),
                    "avg": sum(prices) / len(prices),
                    "count": len(prices),
                },
            },
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# Background task for processing 1688 imports
async def process_1688_import(
    supplier_id: int, file_data: bytes, filename: str, user_id: int
):
    """Background task to process 1688.com product imports."""
    # This would be implemented in the actual service
    # For now, just a placeholder
    logger.info(
        "Processing 1688 import for supplier %s, file: %s, user: %s",
        supplier_id,
        filename,
        user_id,
    )
