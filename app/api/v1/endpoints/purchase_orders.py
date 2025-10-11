"""Purchase Orders API endpoints."""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models.product import Product
from app.models.purchase import PurchaseOrder
from app.models.supplier import Supplier
from app.security.jwt import get_current_user
from app.services.purchase_order_service import PurchaseOrderService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])


@router.get("", response_model=dict[str, Any])
async def list_purchase_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: str | None = Query(None),
    supplier_id: int | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List purchase orders with filtering and pagination."""

    query = (
        select(PurchaseOrder, Supplier)
        .join(Supplier, PurchaseOrder.supplier_id == Supplier.id)
        .options(selectinload(PurchaseOrder.order_items_rel))
    )

    # Apply filters
    if status:
        query = query.where(PurchaseOrder.status == status)

    if supplier_id:
        query = query.where(PurchaseOrder.supplier_id == supplier_id)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                PurchaseOrder.order_number.ilike(search_filter),
                PurchaseOrder.notes.ilike(search_filter),
                Supplier.name.ilike(search_filter),
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    query = query.order_by(PurchaseOrder.order_date.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    orders = result.all()

    # Format response
    orders_data = []
    for po, supplier in orders:
        orders_data.append({
            "id": po.id,
            "order_number": po.order_number,
            "supplier": {
                "id": supplier.id,
                "name": supplier.name,
            },
            "order_date": po.order_date.isoformat() if po.order_date else None,
            "expected_delivery_date": po.expected_delivery_date.isoformat()
            if po.expected_delivery_date
            else None,
            "actual_delivery_date": po.actual_delivery_date.isoformat()
            if po.actual_delivery_date
            else None,
            "status": po.status,
            "total_amount": float(po.total_amount),
            "currency": po.currency,
            "total_items": len(po.order_lines),
            "total_ordered_quantity": po.total_ordered_quantity,
            "total_received_quantity": po.total_received_quantity,
            "is_fully_received": po.is_fully_received,
            "is_partially_received": po.is_partially_received,
            "tracking_number": po.tracking_number,
            "created_at": po.created_at.isoformat() if po.created_at else None,
        })

    return {
        "status": "success",
        "data": {
            "orders": orders_data,
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": skip + limit < total,
            },
        },
    }


@router.post("", response_model=dict[str, Any])
async def create_purchase_order(
    order_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a new purchase order."""

    service = PurchaseOrderService(db)

    try:
        po = await service.create_purchase_order(order_data, current_user.id)
        await db.commit()

        return {
            "status": "success",
            "data": {
                "id": po.id,
                "order_number": po.order_number,
                "message": "Purchase order created successfully",
            },
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating purchase order: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{po_id}", response_model=dict[str, Any])
async def get_purchase_order(
    po_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get detailed purchase order information."""

    query = (
        select(PurchaseOrder)
        .options(
            selectinload(PurchaseOrder.supplier),
            selectinload(PurchaseOrder.order_items_rel),
            selectinload(PurchaseOrder.unreceived_items),
        )
        .where(PurchaseOrder.id == po_id)
    )

    result = await db.execute(query)
    po = result.scalar_one_or_none()

    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    # Get product details for each line
    lines_data = []
    for line in po.order_lines:
        product_query = select(Product).where(Product.id == line.product_id)
        product_result = await db.execute(product_query)
        product = product_result.scalar_one_or_none()

        lines_data.append({
            "id": line.id,
            "product": {
                "id": product.id if product else None,
                "name": product.name if product else "Unknown",
                "sku": product.sku if product else None,
                "image_url": product.image_url if product else None,
            },
            "quantity": line.quantity,
            "received_quantity": line.received_quantity,
            "pending_quantity": line.quantity - line.received_quantity,
            "unit_cost": float(line.unit_cost),
            "line_total": float(line.line_total),
            "quality_status": line.quality_status,
            "quality_notes": line.quality_notes,
        })

    # Get unreceived items
    unreceived_data = []
    for item in po.unreceived_items:
        product_query = select(Product).where(Product.id == item.product_id)
        product_result = await db.execute(product_query)
        product = product_result.scalar_one_or_none()

        unreceived_data.append({
            "id": item.id,
            "product": {
                "id": product.id if product else None,
                "name": product.name if product else "Unknown",
                "sku": product.sku if product else None,
            },
            "ordered_quantity": item.ordered_quantity,
            "received_quantity": item.received_quantity,
            "unreceived_quantity": item.unreceived_quantity,
            "status": item.status,
            "notes": item.notes,
            "expected_date": item.expected_date.isoformat()
            if item.expected_date
            else None,
        })

    return {
        "status": "success",
        "data": {
            "id": po.id,
            "order_number": po.order_number,
            "supplier": {
                "id": po.supplier.id,
                "name": po.supplier.name,
                "email": po.supplier.email,
                "phone": po.supplier.phone,
            },
            "order_date": po.order_date.isoformat() if po.order_date else None,
            "expected_delivery_date": po.expected_delivery_date.isoformat()
            if po.expected_delivery_date
            else None,
            "actual_delivery_date": po.actual_delivery_date.isoformat()
            if po.actual_delivery_date
            else None,
            "status": po.status,
            "total_amount": float(po.total_amount),
            "currency": po.currency,
            "exchange_rate": float(po.exchange_rate),
            "notes": po.internal_notes,
            "delivery_address": po.delivery_address,
            "tracking_number": po.tracking_number,
            "lines": lines_data,
            "unreceived_items": unreceived_data,
            "total_ordered_quantity": po.total_ordered_quantity,
            "total_received_quantity": po.total_received_quantity,
            "is_fully_received": po.is_fully_received,
            "is_partially_received": po.is_partially_received,
            "created_at": po.created_at.isoformat() if po.created_at else None,
            "updated_at": po.updated_at.isoformat() if po.updated_at else None,
        },
    }


@router.patch("/{po_id}/status", response_model=dict[str, Any])
async def update_purchase_order_status(
    po_id: int,
    status_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update purchase order status."""

    service = PurchaseOrderService(db)

    try:
        new_status = status_data.get("status")
        notes = status_data.get("notes")
        metadata = status_data.get("metadata")

        if not new_status:
            raise HTTPException(status_code=400, detail="Status is required")

        po = await service.update_purchase_order_status(
            po_id, new_status, current_user.id, notes, metadata
        )
        await db.commit()

        return {
            "status": "success",
            "data": {
                "id": po.id,
                "order_number": po.order_number,
                "status": po.status,
                "message": f"Status updated to {new_status}",
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating purchase order status: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{po_id}/receive", response_model=dict[str, Any])
async def receive_purchase_order(
    po_id: int,
    receipt_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Record receipt of purchase order items."""

    service = PurchaseOrderService(db)

    try:
        receipt = await service.receive_purchase_order(
            po_id, receipt_data, current_user.id
        )
        await db.commit()

        return {
            "status": "success",
            "data": {
                "receipt_id": receipt.id,
                "receipt_number": receipt.receipt_number,
                "total_received_quantity": receipt.total_received_quantity,
                "message": "Receipt recorded successfully",
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        await db.rollback()
        logger.error(f"Error receiving purchase order: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{po_id}/history", response_model=dict[str, Any])
async def get_purchase_order_history(
    po_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get purchase order history."""

    service = PurchaseOrderService(db)

    try:
        history = await service.get_purchase_order_history(po_id)

        history_data = [
            {
                "id": h.id,
                "action": h.action,
                "old_status": h.old_status,
                "new_status": h.new_status,
                "notes": h.notes,
                "changed_by": h.changed_by,
                "changed_at": h.changed_at.isoformat() if h.changed_at else None,
                "extra_data": h.extra_data,
            }
            for h in history
        ]

        return {
            "status": "success",
            "data": {
                "history": history_data,
            },
        }
    except Exception as e:
        logger.error(f"Error getting purchase order history: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/unreceived-items/list", response_model=dict[str, Any])
async def list_unreceived_items(
    status: str | None = Query(None),
    supplier_id: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List unreceived items with filtering."""

    service = PurchaseOrderService(db)

    try:
        items = await service.get_unreceived_items(status, supplier_id)

        # Paginate
        total = len(items)
        items = items[skip : skip + limit]

        # Get product and supplier details
        items_data = []
        for item in items:
            product_query = select(Product).where(Product.id == item.product_id)
            product_result = await db.execute(product_query)
            product = product_result.scalar_one_or_none()

            po_query = (
                select(PurchaseOrder, Supplier)
                .join(Supplier, PurchaseOrder.supplier_id == Supplier.id)
                .where(PurchaseOrder.id == item.purchase_order_id)
            )
            po_result = await db.execute(po_query)
            po_data = po_result.first()

            if po_data:
                po, supplier = po_data
                items_data.append({
                    "id": item.id,
                    "purchase_order": {
                        "id": po.id,
                        "order_number": po.order_number,
                    },
                    "supplier": {
                        "id": supplier.id,
                        "name": supplier.name,
                    },
                    "product": {
                        "id": product.id if product else None,
                        "name": product.name if product else "Unknown",
                        "sku": product.sku if product else None,
                    },
                    "ordered_quantity": item.ordered_quantity,
                    "received_quantity": item.received_quantity,
                    "unreceived_quantity": item.unreceived_quantity,
                    "status": item.status,
                    "notes": item.notes,
                    "expected_date": item.expected_date.isoformat()
                    if item.expected_date
                    else None,
                    "follow_up_date": item.follow_up_date.isoformat()
                    if item.follow_up_date
                    else None,
                })

        return {
            "status": "success",
            "data": {
                "items": items_data,
                "pagination": {
                    "total": total,
                    "skip": skip,
                    "limit": limit,
                    "has_more": skip + limit < total,
                },
            },
        }
    except Exception as e:
        logger.error(f"Error listing unreceived items: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch("/unreceived-items/{item_id}/resolve", response_model=dict[str, Any])
async def resolve_unreceived_item(
    item_id: int,
    resolution_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Mark an unreceived item as resolved."""

    service = PurchaseOrderService(db)

    try:
        resolution_notes = resolution_data.get("resolution_notes", "")

        item = await service.resolve_unreceived_item(
            item_id, resolution_notes, current_user.id
        )
        await db.commit()

        return {
            "status": "success",
            "data": {
                "id": item.id,
                "status": item.status,
                "message": "Unreceived item resolved successfully",
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        await db.rollback()
        logger.error(f"Error resolving unreceived item: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/statistics/by-supplier/{supplier_id}", response_model=dict[str, Any])
async def get_supplier_order_statistics(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get order statistics for a supplier."""

    service = PurchaseOrderService(db)

    try:
        stats = await service.get_supplier_order_statistics(supplier_id)

        return {
            "status": "success",
            "data": stats,
        }
    except Exception as e:
        logger.error(f"Error getting supplier statistics: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/products/{product_id}/pending-orders", response_model=dict[str, Any])
async def get_pending_orders_for_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all pending purchase orders for a specific product."""

    service = PurchaseOrderService(db)

    try:
        pending_orders = await service.get_pending_orders_for_product(product_id)

        return {
            "status": "success",
            "data": {
                "product_id": product_id,
                "pending_orders": pending_orders,
                "total_pending_quantity": sum(
                    order["pending_quantity"] for order in pending_orders
                ),
            },
        }
    except Exception as e:
        logger.error(f"Error getting pending orders for product: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/bulk-create-drafts", response_model=dict[str, Any])
async def bulk_create_purchase_order_drafts(
    bulk_data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Create multiple purchase order drafts from low stock supplier selections.

    Request body format:
    {
        "selected_products": [
            {
                "product_id": 123,
                "sku": "PROD-001",
                "supplier_id": "sheet_45",
                "supplier_name": "Supplier ABC",
                "reorder_quantity": 50
            },
            ...
        ]
    }

    Groups products by supplier and creates one draft PO per supplier.
    """

    service = PurchaseOrderService(db)

    try:
        selected_products = bulk_data.get("selected_products", [])

        if not selected_products:
            raise HTTPException(
                status_code=400,
                detail="No products provided for draft creation"
            )

        # Group products by supplier name
        products_by_supplier = {}
        for item in selected_products:
            supplier_name = item.get("supplier_name", "Unknown")
            if supplier_name not in products_by_supplier:
                products_by_supplier[supplier_name] = {
                    "supplier_name": supplier_name,
                    "supplier_ids": set(),
                    "products": []
                }

            products_by_supplier[supplier_name]["products"].append(item)
            if item.get("supplier_id"):
                products_by_supplier[supplier_name]["supplier_ids"].add(item["supplier_id"])

        # Get or create suppliers in the database
        from app.models.supplier import Supplier

        created_orders = []
        errors = []

        for supplier_name, supplier_data in products_by_supplier.items():
            try:
                # Try to find existing supplier by name
                supplier_query = select(Supplier).where(
                    func.lower(Supplier.name) == supplier_name.lower()
                )
                supplier_result = await db.execute(supplier_query)
                supplier = supplier_result.scalar_one_or_none()

                # If supplier doesn't exist, create it
                if not supplier:
                    # Generate unique supplier code
                    code_base = "SUP-" + "".join(
                        c for c in supplier_name[:10].upper() if c.isalnum()
                    )

                    # Check if code exists and make it unique
                    code = code_base
                    counter = 1
                    while True:
                        check_query = select(Supplier).where(Supplier.code == code)
                        check_result = await db.execute(check_query)
                        if not check_result.scalar_one_or_none():
                            break
                        code = f"{code_base}-{counter}"
                        counter += 1

                    supplier = Supplier(
                        code=code,
                        name=supplier_name,
                        is_active=True,
                        lead_time_days=7,
                    )
                    db.add(supplier)
                    await db.flush()
                    logger.info(f"Created new supplier: {supplier_name} (ID: {supplier.id})")

                # Determine currency based on supplier type
                # Check if supplier is from China (1688, Google Sheets with CNY)
                from app.models.product_supplier_sheet import ProductSupplierSheet

                supplier_currency = "RON"  # Default
                exchange_rate = 1.0

                # Check if any supplier_id indicates Chinese supplier
                for supp_id in supplier_data["supplier_ids"]:
                    if supp_id.startswith("sheet_") or supp_id.startswith("1688_"):
                        supplier_currency = "CNY"
                        exchange_rate = 0.55  # Approximate CNY to RON rate (1 CNY ≈ 0.55 RON)
                        break

                # Prepare order lines with correct pricing
                order_lines = []
                for product_item in supplier_data["products"]:
                    product_id = product_item.get("product_id")
                    quantity = product_item.get("reorder_quantity", 0)
                    supplier_id = product_item.get("supplier_id")

                    if not product_id or quantity <= 0:
                        continue

                    # Get product to fetch base price
                    product_query = select(Product).where(Product.id == product_id)
                    product_result = await db.execute(product_query)
                    product = product_result.scalar_one_or_none()

                    if not product:
                        logger.warning(f"Product {product_id} not found, skipping")
                        continue

                    # Try to get supplier-specific price
                    unit_cost = 0.0

                    if supplier_id and supplier_id.startswith("sheet_"):
                        # Get price from ProductSupplierSheet
                        sheet_id = int(supplier_id.replace("sheet_", ""))
                        sheet_query = select(ProductSupplierSheet).where(
                            ProductSupplierSheet.id == sheet_id
                        )
                        sheet_result = await db.execute(sheet_query)
                        sheet = sheet_result.scalar_one_or_none()
                        if sheet and sheet.price_cny:
                            unit_cost = float(sheet.price_cny)

                    elif supplier_id and supplier_id.startswith("1688_"):
                        # Get price from SupplierProduct
                        from app.models.supplier import SupplierProduct
                        sp_id = int(supplier_id.replace("1688_", ""))
                        sp_query = select(SupplierProduct).where(SupplierProduct.id == sp_id)
                        sp_result = await db.execute(sp_query)
                        sp = sp_result.scalar_one_or_none()
                        if sp and sp.supplier_price:
                            unit_cost = float(sp.supplier_price)

                    # Fallback to product base_price
                    if unit_cost == 0.0 and product.base_price:
                        unit_cost = float(product.base_price)

                    order_lines.append({
                        "product_id": product_id,
                        "quantity": quantity,
                        "unit_cost": unit_cost,
                    })

                if not order_lines:
                    errors.append({
                        "supplier": supplier_name,
                        "error": "No valid products to order"
                    })
                    continue

                # Create purchase order draft
                order_data = {
                    "supplier_id": supplier.id,
                    "order_date": datetime.now(UTC).replace(tzinfo=None),  # Remove timezone for DB
                    "currency": supplier_currency,
                    "exchange_rate": exchange_rate,
                    "notes": f"Auto-generated draft from Low Stock Suppliers page. Products: {len(order_lines)}. Currency: {supplier_currency}",
                    "lines": order_lines,
                }

                po = await service.create_purchase_order(order_data, current_user.id)
                await db.flush()

                created_orders.append({
                    "id": po.id,
                    "order_number": po.order_number,
                    "supplier_name": supplier_name,
                    "supplier_id": supplier.id,
                    "total_products": len(order_lines),
                    "total_quantity": sum(line["quantity"] for line in order_lines),
                    "status": po.status,
                })

                logger.info(
                    f"Created draft PO {po.order_number} for supplier {supplier_name} "
                    f"with {len(order_lines)} products"
                )

            except Exception as e:
                logger.error(f"Error creating PO for supplier {supplier_name}: {e}")
                errors.append({
                    "supplier": supplier_name,
                    "error": str(e)
                })

        # Commit all changes
        await db.commit()

        return {
            "status": "success",
            "data": {
                "created_orders": created_orders,
                "total_orders_created": len(created_orders),
                "errors": errors,
                "message": f"Successfully created {len(created_orders)} purchase order draft(s)",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in bulk create drafts: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
