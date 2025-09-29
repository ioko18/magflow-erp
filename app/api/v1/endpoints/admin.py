"""Admin dashboard API endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models.order import Order, OrderLine
from app.security.jwt import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard_data(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get dashboard metrics and data."""
    try:
        # Get eMAG sync statistics
        emag_result = await db.execute(
            text(
                """
            SELECT
                COUNT(*) as total_products,
                COUNT(*) FILTER (WHERE ep.updated_at > NOW() - INTERVAL '24 hours') as recent_updates
            FROM app.emag_products ep
        """,
            ),
        )
        emag_data = emag_result.fetchone()

        # Get recent sync status
        sync_result = await db.execute(
            text(
                """
            SELECT sync_id, status, total_offers_processed,
                   started_at, completed_at,
                   EXTRACT(EPOCH FROM (completed_at - started_at)) as duration_seconds
            FROM app.emag_offer_syncs
            ORDER BY created_at DESC
            LIMIT 5
        """,
            ),
        )
        syncs = sync_result.fetchall()

        # Mock data for development
        return {
            "status": "success",
            "data": {
                "totalSales": 45670.89,
                "totalOrders": 234,
                "totalCustomers": 89,
                "emagProducts": emag_data.total_products if emag_data else 0,
                "inventoryValue": 123400.50,
                "syncStatus": "success",
                "recentOrders": [
                    {
                        "id": 1,
                        "customer": "John Doe",
                        "amount": 299.99,
                        "status": "completed",
                        "date": "2024-01-15",
                    },
                    {
                        "id": 2,
                        "customer": "Jane Smith",
                        "amount": 149.50,
                        "status": "processing",
                        "date": "2024-01-15",
                    },
                    {
                        "id": 3,
                        "customer": "Bob Johnson",
                        "amount": 79.99,
                        "status": "shipped",
                        "date": "2024-01-14",
                    },
                ],
                "salesData": [
                    {"name": "Jan", "sales": 4000, "orders": 24},
                    {"name": "Feb", "sales": 3000, "orders": 18},
                    {"name": "Mar", "sales": 2000, "orders": 12},
                    {"name": "Apr", "sales": 2780, "orders": 15},
                    {"name": "May", "sales": 1890, "orders": 11},
                    {"name": "Jun", "sales": 2390, "orders": 16},
                ],
                "topProducts": [
                    {"name": "iPhone 15", "value": 35, "sales": 15420},
                    {"name": "MacBook Pro", "value": 25, "sales": 28900},
                    {"name": "iPad Air", "value": 20, "sales": 8750},
                    {"name": "AirPods Pro", "value": 20, "sales": 3240},
                ],
                "recentSyncs": [
                    {
                        "sync_id": sync.sync_id,
                        "status": sync.status,
                        "offers_processed": sync.total_offers_processed,
                        "started_at": (
                            sync.started_at.isoformat() if sync.started_at else None
                        ),
                        "completed_at": (
                            sync.completed_at.isoformat() if sync.completed_at else None
                        ),
                        "duration_seconds": sync.duration_seconds,
                    }
                    for sync in syncs
                ],
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/emag-products-by-account", response_model=Dict[str, Any])
async def admin_get_emag_products_by_account(
    account_type: str = Query(..., description="Account type: main, fbe or both"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Number of records to return"),
    status: Optional[str] = Query("active", description="Product status filter: active, inactive, all"),
    availability: Optional[bool] = Query(None, description="Filter by availability flag"),
    search: Optional[str] = Query(None, description="Search by SKU or name"),
    sort_by: Optional[str] = Query(
        None,
        description="Sort field: effective_price, price, sale_price, created_at, updated_at, name",
    ),
    sort_order: Optional[str] = Query(
        "desc",
        description="Sort order: asc or desc",
    ),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Surface enhanced eMAG catalog data in the admin dashboard."""

    normalized_account = account_type.lower()
    if normalized_account not in {"main", "fbe", "both"}:
        raise HTTPException(status_code=400, detail="Invalid account_type")

    normalized_status = (status or "active").lower()
    if normalized_status not in {"active", "inactive", "all"}:
        normalized_status = "active"

    try:
        price_expression = "COALESCE(o.sale_price, o.price, 0)"

        filters: List[str] = []
        params: Dict[str, Any] = {}

        if normalized_account in {"main", "fbe"}:
            filters.append("p.account_type = :account_type")
            params["account_type"] = normalized_account

        if normalized_status == "active":
            filters.append("p.is_active = true")
        elif normalized_status == "inactive":
            filters.append("p.is_active = false")

        if availability is not None:
            if availability:
                filters.append("COALESCE(o.available_stock, o.stock, 0) > 0")
            else:
                filters.append("COALESCE(o.available_stock, o.stock, 0) <= 0")

        if search:
            filters.append("(p.sku ILIKE :search OR p.name ILIKE :search)")
            params["search"] = f"%{search}%"

        where_clause = " AND ".join(filters) if filters else "TRUE"

        sort_map = {
            "effective_price": price_expression,
            "price": price_expression,
            "sale_price": price_expression,
            "created_at": "p.created_at",
            "updated_at": "p.updated_at",
            "name": "p.name",
        }

        sort_key = (sort_by or "effective_price").lower()
        sort_column = sort_map.get(sort_key, price_expression)
        sort_direction = "ASC" if (sort_order or "desc").lower() == "asc" else "DESC"

        base_from = (
            " FROM app.emag_products_v2 p "
            "LEFT JOIN app.emag_product_offers o ON o.sku = p.sku AND o.account_type = p.account_type "
            f"WHERE {where_clause}"
        )

        products_query = text(
            f"""
            SELECT p.id, p.emag_id, p.sku, p.name, p.account_type,
                   p.description, p.brand, p.manufacturer,
                   {price_expression} AS price,
                   o.sale_price AS sale_price,
                   o.original_price,
                   p.currency,
                   COALESCE(o.available_stock, o.stock, p.stock_quantity, 0) AS stock_quantity,
                   o.reserved_stock, o.available_stock,
                   p.is_active, p.status, o.status AS offer_status,
                   p.emag_category_id, p.emag_category_name, p.category_id,
                   p.green_tax, p.supply_lead_time,
                   p.safety_information, p.manufacturer_info, p.eu_representative,
                   p.emag_characteristics, p.attributes, p.specifications,
                   p.images, p.images_overwrite,
                   o.handling_time, o.shipping_weight, o.shipping_size,
                   o.marketplace_status, o.visibility,
                   p.sync_status, p.last_synced_at, p.sync_error, p.sync_attempts,
                   p.created_at, p.updated_at, p.emag_created_at, p.emag_modified_at,
                   o.created_at AS offer_created_at, o.updated_at AS offer_updated_at,
                   p.raw_emag_data, o.raw_emag_data AS offer_raw_data
            {base_from}
            ORDER BY {sort_column} {sort_direction}, p.updated_at DESC
            LIMIT :limit OFFSET :skip
            """
        )

        count_query = text(
            f"SELECT COUNT(*) {base_from}"
        )

        summary_query = text(
            f"""
            SELECT
                COUNT(*) AS total_products,
                COUNT(*) FILTER (WHERE p.is_active = true) AS active_products,
                COUNT(*) FILTER (WHERE p.is_active = false) AS inactive_products,
                COUNT(*) FILTER (WHERE COALESCE(o.available_stock, o.stock, p.stock_quantity, 0) > 0) AS available_products,
                COUNT(*) FILTER (WHERE COALESCE(o.available_stock, o.stock, p.stock_quantity, 0) <= 0) AS unavailable_products,
                COUNT(*) FILTER (WHERE {price_expression} = 0) AS zero_price_products,
                AVG({price_expression}) AS avg_price,
                MIN({price_expression}) AS min_price,
                MAX({price_expression}) AS max_price
            {base_from}
            """
        )

        top_brands_query = text(
            f"""
            SELECT COALESCE(p.brand, 'Necunoscut') AS brand, COUNT(*) AS product_count
            {base_from}
            GROUP BY p.brand
            ORDER BY product_count DESC
            LIMIT 5
            """
        )

        base_params = dict(params)
        product_params = dict(base_params)
        product_params.update({"limit": limit, "skip": skip})

        product_rows = (await db.execute(products_query, product_params)).mappings().all()
        total_count = (await db.execute(count_query, base_params)).scalar_one_or_none() or 0
        summary_row = (await db.execute(summary_query, base_params)).mappings().first() or {}
        brand_rows = (await db.execute(top_brands_query, base_params)).mappings().all()

        mapped_products = []
        for row in product_rows:
            price_value = row.get("price") or 0
            sale_price_value = row.get("sale_price")
            original_price_value = row.get("original_price")
            
            # These fields will come from attributes if available
            min_sale_price_value = None
            max_sale_price_value = None
            recommended_price_value = None
            
            # Parse JSON fields safely
            def safe_json_parse(value):
                if value is None:
                    return None
                if isinstance(value, (dict, list)):
                    return value
                try:
                    import json
                    return json.loads(value) if isinstance(value, str) else value
                except (json.JSONDecodeError, TypeError, ValueError):
                    return value
            
            # Extract EAN codes from attributes or characteristics
            ean_codes = []
            attributes = safe_json_parse(row.get("attributes"))
            characteristics = safe_json_parse(row.get("emag_characteristics"))
            
            if isinstance(attributes, dict):
                ean_codes.extend(attributes.get("ean", []) if isinstance(attributes.get("ean"), list) else [attributes.get("ean")] if attributes.get("ean") else [])
            if isinstance(characteristics, dict):
                ean_codes.extend(characteristics.get("ean", []) if isinstance(characteristics.get("ean"), list) else [characteristics.get("ean")] if characteristics.get("ean") else [])
            
            # Clean and deduplicate EAN codes
            ean_codes = list(set([str(ean).strip() for ean in ean_codes if ean and str(ean).strip()]))
            
            # Extract pricing info from attributes if available
            if isinstance(attributes, dict):
                min_sale_price_value = attributes.get("min_sale_price")
                max_sale_price_value = attributes.get("max_sale_price")
                recommended_price_value = attributes.get("recommended_price")
            
            mapped_products.append(
                {
                    # Basic identification
                    "id": row.get("id"),
                    "emag_id": row.get("emag_id") or row.get("sku"),
                    "name": row.get("name"),
                    "part_number": row.get("sku"),
                    "part_number_key": row.get("sku"),
                    "account_type": row.get("account_type"),
                    
                    # Product information
                    "description": row.get("description"),
                    "brand": row.get("brand"),
                    "manufacturer": row.get("manufacturer"),
                    
                    # Pricing information
                    "price": float(price_value) if price_value is not None else None,
                    "sale_price": float(sale_price_value) if sale_price_value is not None else None,
                    "original_price": float(original_price_value) if original_price_value is not None else None,
                    "min_sale_price": float(min_sale_price_value) if min_sale_price_value is not None else None,
                    "max_sale_price": float(max_sale_price_value) if max_sale_price_value is not None else None,
                    "recommended_price": float(recommended_price_value) if recommended_price_value is not None else None,
                    "effective_price": float(sale_price_value if sale_price_value is not None else price_value) if (sale_price_value is not None or price_value is not None) else None,
                    "currency": row.get("currency") or "RON",
                    
                    # Stock information
                    "stock": int(row.get("stock_quantity") or 0),
                    "reserved_stock": int(row.get("reserved_stock") or 0),
                    "available_stock": int(row.get("available_stock") or 0),
                    
                    # Status information
                    "status": "active" if row.get("is_active") else "inactive",
                    "offer_status": row.get("offer_status"),
                    "marketplace_status": row.get("marketplace_status"),
                    "visibility": row.get("visibility"),
                    "is_available": bool((row.get("available_stock") or row.get("stock_quantity") or 0) > 0),
                    
                    # Category information
                    "category": row.get("emag_category_name"),
                    "category_id": row.get("category_id"),
                    "emag_category_id": row.get("emag_category_id"),
                    
                    # eMAG specific fields
                    "green_tax": float(row.get("green_tax")) if row.get("green_tax") is not None else None,
                    "supply_lead_time": row.get("supply_lead_time"),
                    "handling_time": row.get("handling_time"),
                    "shipping_weight": float(row.get("shipping_weight")) if row.get("shipping_weight") is not None else None,
                    "shipping_size": safe_json_parse(row.get("shipping_size")),
                    
                    # Safety and compliance
                    "safety_information": row.get("safety_information"),
                    "manufacturer_info": safe_json_parse(row.get("manufacturer_info")),
                    "eu_representative": safe_json_parse(row.get("eu_representative")),
                    
                    # Product attributes
                    "ean": ean_codes if ean_codes else None,
                    "attributes": attributes,
                    "emag_characteristics": characteristics,
                    "specifications": safe_json_parse(row.get("specifications")),
                    
                    # Media
                    "images": safe_json_parse(row.get("images")),
                    "images_overwrite": bool(row.get("images_overwrite")),
                    
                    # Sync information
                    "sync_status": row.get("sync_status"),
                    "last_synced_at": row.get("last_synced_at").isoformat() if row.get("last_synced_at") else None,
                    "sync_error": row.get("sync_error"),
                    "sync_attempts": row.get("sync_attempts"),
                    
                    # Timestamps
                    "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
                    "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
                    "emag_created_at": row.get("emag_created_at").isoformat() if row.get("emag_created_at") else None,
                    "emag_modified_at": row.get("emag_modified_at").isoformat() if row.get("emag_modified_at") else None,
                    "offer_created_at": row.get("offer_created_at").isoformat() if row.get("offer_created_at") else None,
                    "offer_updated_at": row.get("offer_updated_at").isoformat() if row.get("offer_updated_at") else None,
                    
                    # Raw data for debugging
                    "raw_emag_data": safe_json_parse(row.get("raw_emag_data")),
                    "offer_raw_data": safe_json_parse(row.get("offer_raw_data")),
                }
            )

        summary = {
            "total_products": int(summary_row.get("total_products") or 0),
            "active_products": int(summary_row.get("active_products") or 0),
            "inactive_products": int(summary_row.get("inactive_products") or 0),
            "available_products": int(summary_row.get("available_products") or 0),
            "unavailable_products": int(summary_row.get("unavailable_products") or 0),
            "zero_price_products": int(summary_row.get("zero_price_products") or 0),
            "avg_price": float(summary_row.get("avg_price") or 0),
            "min_price": float(summary_row.get("min_price") or 0),
            "max_price": float(summary_row.get("max_price") or 0),
            "top_brands": [
                {"brand": row["brand"], "count": int(row["product_count"] or 0)}
                for row in brand_rows
            ],
        }

        return {
            "status": "success",
            "data": {
                "products": mapped_products,
                "pagination": {
                    "skip": skip,
                    "limit": limit,
                    "total": total_count,
                    "page": (skip // limit) + 1 if limit else 1,
                    "pages": ((total_count + limit - 1) // limit) if limit else 1,
                },
                "summary": summary,
            },
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch products: {exc}")


@router.post("/sync-emag", response_model=Dict[str, Any])
async def sync_emag_offers(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Trigger eMAG synchronization."""
    try:
        # Import and run the sync function
        from app.emag.sync_emag import sync_emag_offers

        result = await sync_emag_offers()

        return {
            "status": "success" if result["status"] == "success" else "error",
            "message": result.get("message", "Sync completed"),
            "data": result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/emag-orders", response_model=Dict[str, Any])
async def get_emag_orders(
    skip: int = 0,
    limit: int = 10,
    status: Optional[str] = None,
    channel: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get eMAG orders with filtering and pagination."""
    try:
        # Build base query
        query = select(Order).options(
            selectinload(Order.customer),
            selectinload(Order.order_lines).selectinload(OrderLine.product),
        )

        # Apply filters
        if status:
            query = query.where(Order.status == status)

        if channel:
            query = query.where(Order.external_source == f"emag_{channel}")

        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                query = query.where(Order.order_date >= start_dt)
            except ValueError:
                pass

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                query = query.where(Order.order_date <= end_dt)
            except ValueError:
                pass

        # Get total count
        count_query = select(func.count(Order.id)).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Apply pagination and get orders
        query = query.order_by(Order.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        orders = result.scalars().all()

        # Format orders for frontend
        formatted_orders = []
        for order in orders:
            # Calculate items count from order lines
            items_count = len(order.order_lines) if order.order_lines else 0

            # Determine channel from external_source
            channel_value = "other"
            if order.external_source:
                if "fbe" in order.external_source:
                    channel_value = "fbe"
                elif "main" in order.external_source:
                    channel_value = "main"

            formatted_orders.append(
                {
                    "id": order.id,
                    "order_number": f"EM-{order.id}",
                    "customer": {
                        "name": (
                            order.customer.full_name if order.customer else "Unknown"
                        ),
                        "email": order.customer.email if order.customer else None,
                        "phone": (
                            getattr(order.customer, "phone", None)
                            if order.customer
                            else None
                        ),
                        "city": (
                            getattr(order.customer, "city", None)
                            if order.customer
                            else None
                        ),
                    },
                    "channel": channel_value,
                    "status": order.status,
                    "total_amount": order.total_amount,
                    "currency": "RON",
                    "order_date": (
                        order.order_date.isoformat() if order.order_date else None
                    ),
                    "created_at": (
                        order.created_at.isoformat() if order.created_at else None
                    ),
                    "updated_at": (
                        order.updated_at.isoformat() if order.updated_at else None
                    ),
                    "items_count": items_count,
                    "notes": None,
                }
            )

        # Calculate summary
        summary = {
            "total_value": sum(order["total_amount"] for order in formatted_orders),
            "status_breakdown": {},
            "channel_breakdown": {},
        }

        # Status breakdown
        status_counts = {}
        for order in formatted_orders:
            status = order["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        summary["status_breakdown"] = status_counts

        # Channel breakdown
        channel_counts = {}
        for order in formatted_orders:
            channel = order["channel"]
            channel_counts[channel] = channel_counts.get(channel, 0) + 1
        summary["channel_breakdown"] = channel_counts

        return {
            "status": "success",
            "data": {
                "orders": formatted_orders,
                "pagination": {
                    "total": total,
                    "skip": skip,
                    "limit": limit,
                },
                "summary": summary,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
