"""
This module provides REST API endpoints for managing suppliers including:
- CRUD operations for suppliers
- Product matching with 1688.com data
- Purchase order management
- Supplier performance tracking
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from io import BytesIO
import re

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, UploadFile, File
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd

from app.db import get_db
from app.models.supplier import Supplier, SupplierProduct, SupplierPerformance, PurchaseOrder
from app.models.product import Product
from app.security.jwt import get_current_user
from app.services.supplier_service import SupplierService
from app.services.product_matching import ProductMatchingService
from app.services.excel_generator import ExcelGeneratorService

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get("", response_model=Dict[str, Any])
async def list_suppliers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    country: Optional[str] = Query(None),
    active_only: bool = Query(True),
    search: Optional[str] = Query(None),
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
                Supplier.email.ilike(search_filter)
            )
        )

    # Execute query with pagination
    result = await db.execute(query.order_by(Supplier.name).offset(skip).limit(limit))
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
                Supplier.email.ilike(search_filter)
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
                    "created_at": supplier.created_at.isoformat() if supplier.created_at else None,
                }
                for supplier in suppliers
            ],
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": skip + limit < total,
            }
        }
    }


@router.post("", response_model=Dict[str, Any])
async def create_supplier(
    supplier_data: Dict[str, Any],
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
                "message": "Supplier created successfully"
            }
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{supplier_id}", response_model=Dict[str, Any])
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
    perf_query = select(SupplierPerformance).where(
        SupplierPerformance.supplier_id == supplier_id
    ).order_by(SupplierPerformance.created_at.desc()).limit(10)
    perf_result = await db.execute(perf_query)
    performance_records = perf_result.scalars().all()

    # Get recent purchase orders
    po_query = select(PurchaseOrder).where(
        PurchaseOrder.supplier_id == supplier_id
    ).order_by(PurchaseOrder.created_at.desc()).limit(5)
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
                "created_at": supplier.created_at.isoformat() if supplier.created_at else None,
                "updated_at": supplier.updated_at.isoformat() if supplier.updated_at else None,
            },
            "performance": [
                {
                    "metric_type": record.metric_type,
                    "metric_value": record.metric_value,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
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
                    "order_date": order.order_date.isoformat() if order.order_date else None,
                    "expected_delivery_date": order.expected_delivery_date.isoformat() if order.expected_delivery_date else None,
                }
                for order in purchase_orders
            ]
        }
    }


@router.put("/{supplier_id}", response_model=Dict[str, Any])
async def update_supplier(
    supplier_id: int,
    update_data: Dict[str, Any],
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
                "message": "Supplier updated successfully"
            }
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{supplier_id}", response_model=Dict[str, Any])
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
            "data": {"message": "Supplier deleted successfully"}
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


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
    if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")

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
        current_user.id
    )

    return {
        "status": "success",
        "data": {
            "message": "File uploaded successfully. Processing will start in background.",
            "supplier_id": supplier_id,
            "filename": file.filename
        }
    }


@router.get("/{supplier_id}/products")
async def get_supplier_products(
    supplier_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    confirmed_only: bool = Query(False),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all products for a specific supplier."""

    # Build query
    query = select(SupplierProduct).where(SupplierProduct.supplier_id == supplier_id)

    if confirmed_only:
        query = query.where(SupplierProduct.manual_confirmed.is_(True))

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                SupplierProduct.supplier_product_name.ilike(search_filter),
            )
        )

    # Get total count
    count_query = select(func.count(SupplierProduct.id)).where(
        SupplierProduct.supplier_id == supplier_id
    )
    if confirmed_only:
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

    # Load related data
    products_data = []
    for sp in supplier_products:
        # Load local product - only specific fields to avoid relationship loading issues
        local_product_query = select(
            Product.id,
            Product.name,
            Product.sku,
            Product.brand,
            Product.image_url
        ).where(Product.id == sp.local_product_id)
        local_product_result = await db.execute(local_product_query)
        local_product_row = local_product_result.first()

        products_data.append({
            "id": sp.id,
            "supplier_product_name": sp.supplier_product_name,
            "supplier_product_url": sp.supplier_product_url,
            "supplier_image_url": sp.supplier_image_url,
            "supplier_price": sp.supplier_price,
            "supplier_currency": sp.supplier_currency,
            "confidence_score": sp.confidence_score,
            "manual_confirmed": sp.manual_confirmed,
            "is_active": sp.is_active,
            "last_price_update": sp.last_price_update.isoformat() if sp.last_price_update else None,
            "created_at": sp.created_at.isoformat() if sp.created_at else None,
            "local_product": {
                "id": local_product_row[0],
                "name": local_product_row[1],
                "sku": local_product_row[2],
                "brand": local_product_row[3],
                "image_url": local_product_row[4],
                "category": None,  # Not available in this query
            } if local_product_row else None
        })

    return {
        "status": "success",
        "data": {
            "products": products_data,
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": skip + limit < total,
            }
        }
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
            SupplierProduct.manual_confirmed.is_(True)
        )
    )
    confirmed_result = await db.execute(confirmed_query)
    confirmed_products = confirmed_result.scalar()

    # Active products
    active_query = select(func.count(SupplierProduct.id)).where(
        and_(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.is_active.is_(True)
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
            "confirmation_rate": (confirmed_products / total_products * 100) if total_products > 0 else 0.0
        }
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
            supplier_id,
            confidence_threshold=confidence_threshold,
            limit=limit
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
                        "created_at": match.created_at.isoformat() if match.created_at else None,
                    }
                    for match in matches
                ],
                "total_matches": len(matches),
                "threshold": confidence_threshold
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{supplier_id}/products/{match_id}/confirm")
async def confirm_product_match(
    supplier_id: int,
    match_id: int,
    confirmation_data: Dict[str, Any],
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
                "message": "Match confirmed successfully" if confirmed else "Match rejected"
            }
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


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
            SupplierProduct.local_product_id.is_(None)
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
            SupplierProduct.local_product_id.isnot(None)
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
            SupplierProduct.local_product_id.isnot(None)
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
            "average_confidence": float(average_confidence)
        }
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
            SupplierProduct.local_product_id.is_(None)
        )
    )

    # Get total count
    count_query = select(func.count(SupplierProduct.id)).where(
        and_(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.local_product_id.is_(None)
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
        products_data.append({
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
        })

    return {
        "status": "success",
        "data": {
            "products": products_data,
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": skip + limit < total,
            }
        }
    }


@router.post("/{supplier_id}/products/{product_id}/match")
async def match_supplier_product(
    supplier_id: int,
    product_id: int,
    match_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Manually match a supplier product to a local product."""

    try:
        # Get supplier product
        sp_query = select(SupplierProduct).where(
            and_(
                SupplierProduct.id == product_id,
                SupplierProduct.supplier_id == supplier_id
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
        supplier_product.confirmed_at = datetime.utcnow()

        await db.commit()

        return {
            "status": "success",
            "data": {
                "message": "Product matched successfully",
                "supplier_product_id": product_id,
                "local_product_id": match_data.get("local_product_id")
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


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
                SupplierProduct.id == product_id
            )
        )
        result = await db.execute(query)
        supplier_product = result.scalar_one_or_none()
        
        if not supplier_product:
            raise HTTPException(status_code=404, detail="Supplier product not found")
        
        # Remove match
        supplier_product.local_product_id = None
        supplier_product.confidence_score = None
        supplier_product.manual_confirmed = None
        supplier_product.confirmed_by = None
        supplier_product.confirmed_at = None
        supplier_product.updated_at = datetime.utcnow()
        
        await db.commit()
        
        return {
            "status": "success",
            "data": {
                "message": "Match removed successfully",
                "supplier_product_id": product_id
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{supplier_id}/products/auto-match")
async def auto_match_products(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Auto-match supplier products to local products based on chinese names and other criteria."""

    try:
        # Get unmatched supplier products
        sp_query = select(SupplierProduct).where(
            and_(
                SupplierProduct.supplier_id == supplier_id,
                SupplierProduct.local_product_id.is_(None)
            )
        )
        sp_result = await db.execute(sp_query)
        unmatched_products = sp_result.scalars().all()

        # Get all local products with chinese names
        local_query = select(
            Product.id,
            Product.name,
            Product.chinese_name,
            Product.sku
        ).where(Product.chinese_name.isnot(None))
        local_result = await db.execute(local_query)
        local_products = local_result.all()

        matched_count = 0

        # Simple matching logic based on chinese name similarity
        for sp in unmatched_products:
            supplier_name = sp.supplier_product_name.lower()
            
            for local_product in local_products:
                if local_product[2]:  # chinese_name exists
                    local_chinese = local_product[2].lower()
                    
                    # Simple substring matching
                    if local_chinese in supplier_name or supplier_name in local_chinese:
                        sp.local_product_id = local_product[0]
                        sp.confidence_score = 0.75  # Auto-match confidence
                        sp.manual_confirmed = False  # Needs manual confirmation
                        matched_count += 1
                        break

        await db.commit()

        return {
            "status": "success",
            "data": {
                "message": f"Auto-matched {matched_count} products",
                "matched_count": matched_count,
                "total_unmatched": len(unmatched_products)
            }
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


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
            'url_image_scrapping',
            'url_product_scrapping', 
            'chinese_name_scrapping',
            'price_scrapping'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        # Process each row
        imported_count = 0
        skipped_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Parse price from "CN ¥ 2.45" format
                price_str = str(row['price_scrapping'])
                price_match = re.search(r'[\d,]+\.?\d*', price_str.replace(',', ''))
                
                if price_match:
                    price = float(price_match.group())
                else:
                    errors.append(f"Row {index + 2}: Invalid price format '{price_str}'")
                    skipped_count += 1
                    continue
                
                # Check if product already exists (by URL)
                existing_query = select(SupplierProduct).where(
                    and_(
                        SupplierProduct.supplier_id == supplier_id,
                        SupplierProduct.supplier_product_url == str(row['url_product_scrapping'])
                    )
                )
                existing_result = await db.execute(existing_query)
                existing_product = existing_result.scalar_one_or_none()
                
                if existing_product:
                    # Update existing product
                    existing_product.supplier_product_name = str(row['chinese_name_scrapping'])
                    existing_product.supplier_image_url = str(row['url_image_scrapping'])
                    existing_product.supplier_price = price
                    existing_product.supplier_currency = 'CNY'
                    existing_product.updated_at = datetime.utcnow()
                else:
                    # Create new product
                    new_product = SupplierProduct(
                        supplier_id=supplier_id,
                        supplier_product_name=str(row['chinese_name_scrapping']),
                        supplier_product_url=str(row['url_product_scrapping']),
                        supplier_image_url=str(row['url_image_scrapping']),
                        supplier_price=price,
                        supplier_currency='CNY',
                        is_active=True,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
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
                "errors": errors[:10] if errors else []  # Return first 10 errors
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")


@router.get("/{supplier_id}/orders/generate")
async def generate_supplier_order_excel(
    supplier_id: int,
    product_ids: List[int] = Query(...),
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
                SupplierProduct.manual_confirmed
            )
        )
        mappings_result = await db.execute(mappings_query)
        mappings = mappings_result.scalars().all()

        if not mappings:
            raise HTTPException(
                status_code=400,
                detail="No confirmed supplier mappings found for selected products"
            )

        # Generate Excel
        excel_data = await excel_service.generate_supplier_order_excel(
            supplier,
            mappings
        )

        return {
            "status": "success",
            "data": {
                "filename": f"order_{supplier.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "excel_data": excel_data,
                "supplier_id": supplier_id,
                "product_count": len(mappings)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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
            supplier_id,
            period_days=period_days
        )

        return {
            "status": "success",
            "data": performance
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Background task for processing 1688 imports
async def process_1688_import(supplier_id: int, file_data: bytes, filename: str, user_id: int):
    """Background task to process 1688.com product imports."""
    # This would be implemented in the actual service
    # For now, just a placeholder
    print(f"Processing 1688 import for supplier {supplier_id}, file: {filename}")
