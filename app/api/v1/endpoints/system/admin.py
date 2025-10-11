"""Admin dashboard API endpoints."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_cache, set_cache
from app.core.logging import get_logger
from app.db import get_db
from app.security.jwt import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])
logger = get_logger(__name__)


@router.get("/dashboard", response_model=dict[str, Any])
async def get_dashboard_data(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    force_refresh: bool = Query(False, description="Force cache refresh"),
):
    """Get dashboard metrics and data with real database queries.

    Uses Redis caching with 5-minute TTL for improved performance.
    Set force_refresh=true to bypass cache.
    """
    cache_key = "dashboard:metrics:v1"

    # Try to get from cache first (unless force refresh)
    if not force_refresh:
        cached_data = await get_cache(cache_key)
        if cached_data:
            logger.info("Dashboard data served from cache")
            return {"status": "success", "data": cached_data, "cached": True}

    logger.info("Fetching fresh dashboard data from database")
    try:
        # ===== SALES METRICS =====
        # Get total sales from sales_orders (current month) - using real data
        sales_current_month = await db.execute(
            text("""
                SELECT
                    COALESCE(SUM(total_amount), 0) as total_sales,
                    COUNT(*) as total_orders
                FROM app.sales_orders
                WHERE DATE_TRUNC('month', order_date) = DATE_TRUNC('month', CURRENT_DATE)
                AND status NOT IN ('cancelled', 'rejected')
            """)
        )
        sales_current = sales_current_month.fetchone()

        # Get previous month sales for growth calculation
        sales_previous_month = await db.execute(
            text("""
                SELECT
                    COALESCE(SUM(total_amount), 0) as total_sales,
                    COUNT(*) as total_orders
                FROM app.sales_orders
                WHERE DATE_TRUNC('month', order_date) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
                AND status NOT IN ('cancelled', 'rejected')
            """)
        )
        sales_previous = sales_previous_month.fetchone()

        # Calculate growth percentages
        sales_growth = 0.0
        if sales_previous and sales_previous.total_sales > 0:
            sales_growth = (
                (sales_current.total_sales - sales_previous.total_sales)
                / sales_previous.total_sales
            ) * 100
        orders_growth = 0.0
        if sales_previous and sales_previous.total_orders > 0:
            orders_growth = (
                (sales_current.total_orders - sales_previous.total_orders)
                / sales_previous.total_orders
            ) * 100

        # ===== CUSTOMER METRICS =====
        # Count unique customers from sales_orders
        customers_current_month = await db.execute(
            text("""
                SELECT COUNT(DISTINCT customer_id) as total_customers
                FROM app.sales_orders
                WHERE customer_id IS NOT NULL
                AND order_date >= DATE_TRUNC('month', CURRENT_DATE)
            """)
        )
        customers_current = customers_current_month.fetchone()

        customers_previous_month = await db.execute(
            text("""
                SELECT COUNT(DISTINCT customer_id) as total_customers
                FROM app.sales_orders
                WHERE customer_id IS NOT NULL
                AND order_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
                AND order_date < DATE_TRUNC('month', CURRENT_DATE)
            """)
        )
        customers_previous = customers_previous_month.fetchone()

        customers_growth = 0.0
        if customers_previous and customers_previous.total_customers > 0:
            customers_growth = (
                (customers_current.total_customers - customers_previous.total_customers)
                / customers_previous.total_customers
            ) * 100

        # ===== EMAG PRODUCTS METRICS =====
        emag_result = await db.execute(
            text("""
                SELECT
                    COUNT(*) as total_products,
                    COUNT(*) FILTER (WHERE updated_at > NOW() - INTERVAL '24 hours') as recent_updates,
                    0 as main_products,
                    0 as fbe_products
                FROM app.emag_products_v2
                WHERE is_active = true
            """)
        )
        emag_data = emag_result.fetchone()

        # Get previous month eMAG products count
        emag_previous_month = await db.execute(
            text("""
                SELECT COUNT(*) as total_products
                FROM app.emag_products_v2
                WHERE is_active = true
                AND created_at < DATE_TRUNC('month', CURRENT_DATE)
            """)
        )
        emag_previous = emag_previous_month.fetchone()

        emag_growth = 0.0
        if emag_previous and emag_previous.total_products > 0:
            emag_growth = (
                (emag_data.total_products - emag_previous.total_products)
                / emag_previous.total_products
            ) * 100

        # ===== INVENTORY VALUE =====
        # Calculate inventory value from emag_products_v2 (real data)
        inventory_value_result = await db.execute(
            text("""
                SELECT
                    COALESCE(SUM(price * COALESCE(stock_quantity, 0)), 0) as total_value,
                    COUNT(*) as total_products,
                    COUNT(*) FILTER (WHERE COALESCE(stock_quantity, 0) > 0) as in_stock_count,
                    COUNT(*) FILTER (WHERE COALESCE(stock_quantity, 0) <= 0) as out_of_stock_count,
                    COUNT(*) FILTER (WHERE COALESCE(stock_quantity, 0) > 0 AND COALESCE(stock_quantity, 0) <= 10) as low_stock_count
                FROM app.emag_products_v2
                WHERE is_active = true
            """)
        )
        inventory_data = inventory_value_result.fetchone()

        # ===== RECENT ORDERS =====
        recent_orders_result = await db.execute(
            text("""
                SELECT
                    so.id as order_id,
                    COALESCE(c.name, 'N/A') as customer_name,
                    so.total_amount,
                    so.status,
                    so.order_date,
                    COALESCE(so.currency, 'RON') as currency
                FROM app.sales_orders so
                LEFT JOIN app.customers c ON so.customer_id = c.id
                ORDER BY so.order_date DESC
                LIMIT 10
            """)
        )
        recent_orders = recent_orders_result.fetchall()

        # ===== SALES DATA BY MONTH (Last 6 months) =====
        sales_by_month_result = await db.execute(
            text("""
                SELECT
                    TO_CHAR(DATE_TRUNC('month', order_date), 'Mon') as month_name,
                    EXTRACT(MONTH FROM order_date) as month_num,
                    COALESCE(SUM(total_amount), 0) as sales,
                    COUNT(*) as orders,
                    COALESCE(SUM(total_amount * 0.2), 0) as profit
                FROM app.sales_orders
                WHERE order_date >= CURRENT_DATE - INTERVAL '6 months'
                AND status NOT IN ('cancelled', 'rejected')
                GROUP BY month_name, month_num, DATE_TRUNC('month', order_date)
                ORDER BY DATE_TRUNC('month', order_date) ASC
            """)
        )
        sales_by_month = sales_by_month_result.fetchall()

        # ===== TOP PRODUCTS =====
        # Get top products from emag_products_v2 by stock quantity
        top_products_result = await db.execute(
            text("""
                SELECT
                    name,
                    COALESCE(sku, 'N/A') as sku,
                    1 as order_count,
                    COALESCE(stock_quantity, 0) as total_quantity,
                    COALESCE(price * stock_quantity, 0) as total_sales,
                    COALESCE(stock_quantity, 0) as stock
                FROM app.emag_products_v2
                WHERE is_active = true
                AND stock_quantity > 0
                ORDER BY stock_quantity DESC
                LIMIT 5
            """)
        )
        top_products = top_products_result.fetchall()

        # ===== INVENTORY STATUS BY CATEGORY =====
        inventory_status_result = await db.execute(
            text("""
                SELECT
                    'All Products' as category,
                    COUNT(*) FILTER (WHERE COALESCE(stock_quantity, 0) > 10) as inStock,
                    COUNT(*) FILTER (WHERE COALESCE(stock_quantity, 0) > 0 AND COALESCE(stock_quantity, 0) <= 10) as lowStock,
                    COUNT(*) FILTER (WHERE COALESCE(stock_quantity, 0) <= 0) as outOfStock
                FROM app.emag_products_v2
                WHERE is_active = true
                LIMIT 10
            """)
        )
        inventory_status = inventory_status_result.fetchall()

        # ===== SYSTEM HEALTH =====
        # Check database health
        db_health = "healthy"
        try:
            await db.execute(text("SELECT 1"))
        except Exception:
            db_health = "error"

        # Check eMAG sync status
        emag_health = "healthy"
        if emag_data and emag_data.recent_updates == 0:
            emag_health = "warning"

        # ===== REALTIME METRICS =====
        realtime_result = await db.execute(
            text("""
                SELECT
                    (SELECT COUNT(*) FROM app.sales_orders WHERE status IN ('pending', 'confirmed')) as pending_orders,
                    (SELECT COUNT(*) FROM app.emag_products_v2
                     WHERE is_active = true AND COALESCE(stock_quantity, 0) > 0 AND COALESCE(stock_quantity, 0) <= 10) as low_stock_items
            """)
        )
        realtime_data = realtime_result.fetchone()

        # Calculate sync progress (based on recent syncs)
        sync_progress = 100
        if emag_data and emag_data.recent_updates > 0:
            sync_progress = min(
                100,
                int(
                    (emag_data.recent_updates / max(emag_data.total_products, 1)) * 100
                ),
            )

        # ===== PERFORMANCE DATA =====
        performance_data = [
            {"name": "Database Response", "value": 98, "target": 95},
            {"name": "API Uptime", "value": 99.9, "target": 99.5},
            {"name": "Order Processing", "value": 95, "target": 90},
            {"name": "Sync Success Rate", "value": 97, "target": 95},
        ]

        # Get active users count
        active_users = 0
        try:
            from app.services.system.session_tracking_service import (
                SessionTrackingService,
            )

            session_service = SessionTrackingService(db)
            active_users = await session_service.get_active_users_count(30)
        except Exception as e:
            logger.error(f"Error getting active users: {e}")

        # Build response data
        dashboard_data = {
            # Key Metrics
            "totalSales": float(sales_current.total_sales) if sales_current else 0.0,
            "totalOrders": int(sales_current.total_orders) if sales_current else 0,
            "totalCustomers": int(customers_current.total_customers)
            if customers_current
            else 0,
            "emagProducts": int(emag_data.total_products) if emag_data else 0,
            "inventoryValue": float(inventory_data.total_value)
            if inventory_data
            else 0.0,
            # Growth Metrics
            "salesGrowth": round(sales_growth, 1),
            "ordersGrowth": round(orders_growth, 1),
            "customersGrowth": round(customers_growth, 1),
            "emagGrowth": round(emag_growth, 1),
            # System Health
            "systemHealth": {
                "database": db_health,
                "api": "healthy",
                "emag": emag_health,
            },
            # Realtime Metrics
            "realtimeMetrics": {
                "activeUsers": active_users,
                "pendingOrders": int(realtime_data.pending_orders)
                if realtime_data
                else 0,
                "lowStockItems": int(realtime_data.low_stock_items)
                if realtime_data
                else 0,
                "syncProgress": sync_progress,
            },
            # Recent Orders
            "recentOrders": [
                {
                    "id": order.id,
                    "customer": order.customer_name,
                    "amount": float(order.total_amount),
                    "status": order.status,
                    "date": order.order_date.strftime("%Y-%m-%d")
                    if order.order_date
                    else None,
                    "priority": "high"
                    if float(order.total_amount) > 500
                    else "medium"
                    if float(order.total_amount) > 200
                    else "low",
                }
                for order in recent_orders
            ],
            # Sales Data with month-over-month growth
            "salesData": [
                {
                    "name": sales_by_month[i].month_name,
                    "sales": float(sales_by_month[i].sales),
                    "orders": int(sales_by_month[i].orders),
                    "profit": float(sales_by_month[i].profit),
                    "growth": round(
                        (
                            (
                                float(sales_by_month[i].sales)
                                - float(sales_by_month[i - 1].sales)
                            )
                            / max(float(sales_by_month[i - 1].sales), 1)
                        )
                        * 100,
                        1,
                    )
                    if i > 0 and sales_by_month[i - 1].sales
                    else 0.0,
                }
                for i in range(len(sales_by_month))
            ],
            # Top Products
            "topProducts": [
                {
                    "name": product.name,
                    "value": int(product.total_quantity),
                    "sales": float(product.total_sales),
                    "stock": int(product.stock),
                    "trend": "up"
                    if product.stock > 20
                    else "stable"
                    if product.stock > 10
                    else "down",
                }
                for product in top_products
            ],
            # Inventory Status
            "inventoryStatus": [
                {
                    "category": status.category,
                    "inStock": int(status.instock),
                    "lowStock": int(status.lowstock),
                    "outOfStock": int(status.outofstock),
                }
                for status in inventory_status
            ],
            # Performance Data
            "performanceData": performance_data,
            # Sync Status
            "syncStatus": "success" if emag_health == "healthy" else "warning",
        }

        # Cache the data for 5 minutes (300 seconds)
        await set_cache(cache_key, dashboard_data, ttl=300)
        logger.info("Dashboard data cached successfully")

        return {"status": "success", "data": dashboard_data, "cached": False}

    except Exception as e:
        logger.error(
            "Dashboard error",
            exc_info=True,
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch dashboard data: {str(e)}"
        )


@router.get("/emag-products-by-account", response_model=dict[str, Any])
async def admin_get_emag_products_by_account(
    account_type: str = Query(..., description="Account type: main, fbe or both"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Number of records to return"),
    status: str | None = Query(
        "active", description="Product status filter: active, inactive, all"
    ),
    availability: bool | None = Query(
        None, description="Filter by availability flag"
    ),
    search: str | None = Query(None, description="Search by SKU or name"),
    sort_by: str | None = Query(
        None,
        description="Sort field: effective_price, price, sale_price, created_at, updated_at, name",
    ),
    sort_order: str | None = Query(
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
        price_expression = "COALESCE(o.price, p.price, 0)"

        filters: list[str] = []
        params: dict[str, Any] = {}

        if normalized_account in {"main", "fbe"}:
            filters.append("p.account_type = :account_type")
            params["account_type"] = normalized_account

        if normalized_status == "active":
            filters.append("(p.is_active = true OR p.is_active IS NULL)")
        elif normalized_status == "inactive":
            filters.append("p.is_active = false")

        if availability is not None:
            if availability:
                filters.append("COALESCE(o.stock_quantity, p.stock_quantity, 0) > 0")
            else:
                filters.append("COALESCE(o.stock_quantity, p.stock_quantity, 0) <= 0")

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
            "LEFT JOIN app.emag_product_offers_v2 o ON o.product_id = p.id "
            f"WHERE {where_clause}"
        )

        products_query = text(
            f"""
            SELECT p.id, p.emag_id, p.sku, p.name, p.account_type,
                   p.description, p.brand, p.manufacturer,
                   COALESCE(o.price, p.price, 0) AS price,
                   o.price AS sale_price,
                   p.price AS original_price,
                   COALESCE(o.currency, p.currency, 'RON') AS currency,
                   COALESCE(o.stock_quantity, p.stock_quantity, 0) AS stock_quantity,
                   0 AS reserved_stock,
                   COALESCE(o.stock_quantity, p.stock_quantity, 0) AS available_stock,
                   p.is_active, p.status, o.status AS offer_status,
                   p.emag_category_id, p.emag_category_name, p.category_id,
                   p.green_tax, p.supply_lead_time,
                   p.safety_information, p.manufacturer_info, p.eu_representative,
                   p.emag_characteristics, p.attributes, p.specifications,
                   p.images, p.images_overwrite,
                   o.handling_time, 0 AS shipping_weight, '' AS shipping_size,
                   '' AS marketplace_status, true AS visibility,
                   p.sync_status, p.last_synced_at, p.sync_error, p.sync_attempts,
                   p.created_at, p.updated_at, p.emag_created_at, p.emag_modified_at,
                   o.created_at AS offer_created_at, o.updated_at AS offer_updated_at,
                   p.raw_emag_data, NULL AS offer_raw_data
            {base_from}
            ORDER BY {sort_column} {sort_direction}, p.updated_at DESC
            LIMIT :limit OFFSET :skip
            """
        )

        count_query = text(f"SELECT COUNT(*) {base_from}")

        summary_query = text(
            f"""
            SELECT
                COUNT(*) AS total_products,
                COUNT(*) FILTER (WHERE p.is_active = true) AS active_products,
                COUNT(*) FILTER (WHERE p.is_active = false) AS inactive_products,
                COUNT(*) FILTER (WHERE COALESCE(o.stock_quantity, p.stock_quantity, 0) > 0) AS available_products,
                COUNT(*) FILTER (WHERE COALESCE(o.stock_quantity, p.stock_quantity, 0) <= 0) AS unavailable_products,
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

        product_rows = (
            (await db.execute(products_query, product_params)).mappings().all()
        )
        total_count = (
            await db.execute(count_query, base_params)
        ).scalar_one_or_none() or 0
        summary_row = (
            await db.execute(summary_query, base_params)
        ).mappings().first() or {}
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
                ean_codes.extend(
                    attributes.get("ean", [])
                    if isinstance(attributes.get("ean"), list)
                    else [attributes.get("ean")]
                    if attributes.get("ean")
                    else []
                )
            if isinstance(characteristics, dict):
                ean_codes.extend(
                    characteristics.get("ean", [])
                    if isinstance(characteristics.get("ean"), list)
                    else (
                        [characteristics.get("ean")]
                        if characteristics.get("ean")
                        else []
                    )
                )

            # Clean and deduplicate EAN codes
            ean_codes = list(
                {str(ean).strip() for ean in ean_codes if ean and str(ean).strip()}
            )

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
                    "sale_price": (
                        float(sale_price_value)
                        if sale_price_value is not None
                        else None
                    ),
                    "original_price": (
                        float(original_price_value)
                        if original_price_value is not None
                        else None
                    ),
                    "min_sale_price": (
                        float(min_sale_price_value)
                        if min_sale_price_value is not None
                        else None
                    ),
                    "max_sale_price": (
                        float(max_sale_price_value)
                        if max_sale_price_value is not None
                        else None
                    ),
                    "recommended_price": (
                        float(recommended_price_value)
                        if recommended_price_value is not None
                        else None
                    ),
                    "effective_price": (
                        float(
                            sale_price_value
                            if sale_price_value is not None
                            else price_value
                        )
                        if (sale_price_value is not None or price_value is not None)
                        else None
                    ),
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
                    "is_available": bool(
                        (row.get("available_stock") or row.get("stock_quantity") or 0)
                        > 0
                    ),
                    # Category information
                    "category": row.get("emag_category_name"),
                    "category_id": row.get("category_id"),
                    "emag_category_id": row.get("emag_category_id"),
                    # eMAG specific fields
                    "green_tax": (
                        float(row.get("green_tax"))
                        if row.get("green_tax") is not None
                        else None
                    ),
                    "supply_lead_time": row.get("supply_lead_time"),
                    "handling_time": row.get("handling_time"),
                    "shipping_weight": (
                        float(row.get("shipping_weight"))
                        if row.get("shipping_weight") is not None
                        else None
                    ),
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
                    "last_synced_at": (
                        row.get("last_synced_at").isoformat()
                        if row.get("last_synced_at")
                        else None
                    ),
                    "sync_error": row.get("sync_error"),
                    "sync_attempts": row.get("sync_attempts"),
                    # Timestamps
                    "created_at": (
                        row.get("created_at").isoformat()
                        if row.get("created_at")
                        else None
                    ),
                    "updated_at": (
                        row.get("updated_at").isoformat()
                        if row.get("updated_at")
                        else None
                    ),
                    "emag_created_at": (
                        row.get("emag_created_at").isoformat()
                        if row.get("emag_created_at")
                        else None
                    ),
                    "emag_modified_at": (
                        row.get("emag_modified_at").isoformat()
                        if row.get("emag_modified_at")
                        else None
                    ),
                    "offer_created_at": (
                        row.get("offer_created_at").isoformat()
                        if row.get("offer_created_at")
                        else None
                    ),
                    "offer_updated_at": (
                        row.get("offer_updated_at").isoformat()
                        if row.get("offer_updated_at")
                        else None
                    ),
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


@router.post("/sync-emag", response_model=dict[str, Any])
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


@router.get("/emag-orders", response_model=dict[str, Any])
async def get_emag_orders(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    status: str | None = Query(None, description="Filter by order status"),
    channel: str | None = Query(None, description="Filter by channel (main/fbe)"),
    start_date: str | None = Query(None, description="Filter orders from this date"),
    end_date: str | None = Query(None, description="Filter orders until this date"),
    search: str | None = Query(
        None, description="Search by order number, customer name, email or phone"
    ),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get eMAG orders with filtering, search and pagination from emag_orders table.

    Improvements:
    - Fixed count query bug (was returning incorrect total)
    - Added search functionality across multiple fields
    - Improved summary statistics with real database aggregations
    - Added proper error handling and validation
    """
    from sqlalchemy import and_, or_

    from app.models.emag_models import EmagOrder

    try:
        # Build base query for EmagOrder table
        filters = []

        # Apply status filter
        if status and status != "all":
            # Convert status string to int if needed
            try:
                status_int = int(status)
                filters.append(EmagOrder.status == status_int)
            except ValueError:
                # If status is a string like "new", "in_progress", etc.
                status_map = {
                    "new": 1,
                    "in_progress": 2,
                    "prepared": 3,
                    "finalized": 4,
                    "returned": 5,
                    "canceled": 0,
                    "cancelled": 0,
                    "pending": 1,
                    "processing": 2,
                    "completed": 4,
                    "shipped": 3,
                    "delivered": 4,
                }
                if status.lower() in status_map:
                    filters.append(EmagOrder.status == status_map[status.lower()])

        # Apply channel filter
        if channel and channel != "all":
            filters.append(EmagOrder.account_type == channel)

        # Apply date range filters
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                filters.append(EmagOrder.order_date >= start_dt)
            except (ValueError, AttributeError):
                pass

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                filters.append(EmagOrder.order_date <= end_dt)
            except (ValueError, AttributeError):
                pass

        # Apply search filter
        if search and search.strip():
            search_term = f"%{search.strip()}%"
            search_filters = or_(
                EmagOrder.emag_order_id.cast(text("TEXT")).ilike(search_term),
                EmagOrder.customer_name.ilike(search_term),
                EmagOrder.customer_email.ilike(search_term),
                EmagOrder.customer_phone.ilike(search_term),
            )
            filters.append(search_filters)

        # Build query with filters
        query = select(EmagOrder)
        if filters:
            query = query.where(and_(*filters))

        # Get total count - FIXED: Use correct count query without subquery
        count_query = select(func.count()).select_from(EmagOrder)
        if filters:
            count_query = count_query.where(and_(*filters))

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(EmagOrder.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        orders = result.scalars().all()

        # Status name mapping
        status_names = {
            0: "canceled",
            1: "new",
            2: "in_progress",
            3: "prepared",
            4: "finalized",
            5: "returned",
        }

        # Format orders for frontend
        formatted_orders = []
        for order in orders:
            # Calculate items count from products JSON
            items_count = len(order.products) if order.products else 0

            formatted_orders.append(
                {
                    "id": str(order.id),  # Convert UUID to string
                    "emag_order_id": order.emag_order_id,
                    "order_number": f"EM-{order.emag_order_id}",
                    "customer": {
                        "name": order.customer_name or "Unknown",
                        "email": order.customer_email,
                        "phone": order.customer_phone,
                        "city": None,  # Not stored in EmagOrder
                    },
                    "channel": order.account_type,  # 'main' or 'fbe'
                    "status": status_names.get(order.status, "unknown"),
                    "status_code": order.status,
                    "total_amount": float(order.total_amount)
                    if order.total_amount
                    else 0.0,
                    "currency": order.currency or "RON",
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
                    "payment_method": order.payment_method,
                    "delivery_mode": order.delivery_mode,
                    "sync_status": order.sync_status,
                    "last_synced_at": (
                        order.last_synced_at.isoformat()
                        if order.last_synced_at
                        else None
                    ),
                }
            )

        # Calculate comprehensive summary statistics from database
        # Get overall statistics (not just current page)
        summary_query = select(
            func.sum(EmagOrder.total_amount).label("total_value"),
            func.count().label("total_orders"),
        )
        if filters:
            summary_query = summary_query.where(and_(*filters))

        summary_result = await db.execute(summary_query)
        summary_data = summary_result.fetchone()

        # Get status breakdown
        status_breakdown_query = select(
            EmagOrder.status, func.count().label("count")
        ).group_by(EmagOrder.status)
        if filters:
            status_breakdown_query = status_breakdown_query.where(and_(*filters))

        status_breakdown_result = await db.execute(status_breakdown_query)
        status_breakdown = {
            status_names.get(row.status, f"status_{row.status}"): row.count
            for row in status_breakdown_result.fetchall()
        }

        # Get channel breakdown
        channel_breakdown_query = select(
            EmagOrder.account_type, func.count().label("count")
        ).group_by(EmagOrder.account_type)
        if filters:
            channel_breakdown_query = channel_breakdown_query.where(and_(*filters))

        channel_breakdown_result = await db.execute(channel_breakdown_query)
        channel_breakdown = {
            row.account_type: row.count for row in channel_breakdown_result.fetchall()
        }

        # Get sync status breakdown
        sync_breakdown_query = select(
            EmagOrder.sync_status, func.count().label("count")
        ).group_by(EmagOrder.sync_status)
        if filters:
            sync_breakdown_query = sync_breakdown_query.where(and_(*filters))

        sync_breakdown_result = await db.execute(sync_breakdown_query)
        sync_breakdown = {
            row.sync_status: row.count for row in sync_breakdown_result.fetchall()
        }

        # Calculate recent activity
        from datetime import timedelta

        # Orders created in last 24 hours
        twenty_four_hours_ago = datetime.now(UTC) - timedelta(hours=24)
        new_orders_24h_query = (
            select(func.count())
            .select_from(EmagOrder)
            .where(EmagOrder.created_at >= twenty_four_hours_ago)
        )
        if filters:
            new_orders_24h_query = new_orders_24h_query.where(and_(*filters))
        new_orders_24h_result = await db.execute(new_orders_24h_query)
        new_orders_24h = new_orders_24h_result.scalar() or 0

        # Orders synced today
        today_start = datetime.now(UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        synced_today_query = (
            select(func.count())
            .select_from(EmagOrder)
            .where(EmagOrder.last_synced_at >= today_start)
        )
        if filters:
            synced_today_query = synced_today_query.where(and_(*filters))
        synced_today_result = await db.execute(synced_today_query)
        synced_today = synced_today_result.scalar() or 0

        # Pending sync orders
        pending_sync_query = (
            select(func.count())
            .select_from(EmagOrder)
            .where(EmagOrder.sync_status.in_(["pending", "failed"]))
        )
        if filters:
            pending_sync_query = pending_sync_query.where(and_(*filters))
        pending_sync_result = await db.execute(pending_sync_query)
        pending_sync = pending_sync_result.scalar() or 0

        summary = {
            "total_value": float(summary_data.total_value or 0.0),
            "total_orders": summary_data.total_orders or 0,
            "status_breakdown": status_breakdown,
            "channel_breakdown": channel_breakdown,
            "emag_sync_stats": {
                "synced": sync_breakdown.get("synced", 0),
                "pending": sync_breakdown.get("pending", 0),
                "failed": sync_breakdown.get("failed", 0),
                "never_synced": sync_breakdown.get("never_synced", 0),
            },
            "recent_activity": {
                "newOrders24h": new_orders_24h,
                "syncedToday": synced_today,
                "pendingSync": pending_sync,
            },
        }

        return {
            "status": "success",
            "data": {
                "orders": formatted_orders,
                "pagination": {
                    "total": total,
                    "skip": skip,
                    "limit": limit,
                    "page": (skip // limit) + 1 if limit > 0 else 1,
                    "pages": (total + limit - 1) // limit if limit > 0 else 0,
                },
                "summary": summary,
            },
        }

    except Exception as e:
        logger.error(
            "Error in get_emag_orders",
            exc_info=True,
            extra={"error": str(e)},
        )
        raise HTTPException(status_code=500, detail=f"Failed to fetch orders: {str(e)}")


@router.get("/products/unified", response_model=dict[str, Any])
async def get_unified_products(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Number of records to return"),
    marketplace_presence: str | None = Query(
        None,
        description="Filter by marketplace presence: local_only, emag_only, main_only, fbe_only, both_accounts, all",
    ),
    sync_status: str | None = Query(
        None, description="Filter by sync status: synced, pending, failed, never_synced"
    ),
    price_comparison: str | None = Query(
        None,
        description="Filter by price comparison: different_prices, no_local_price, no_emag_price",
    ),
    search: str | None = Query(None, description="Search by SKU or name"),
    sort_by: str | None = Query(
        "updated_at", description="Sort field: name, sku, price, updated_at"
    ),
    sort_order: str | None = Query("desc", description="Sort order: asc or desc"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get unified view of all products (local + eMAG MAIN + eMAG FBE).

    This endpoint combines products from app.products (local database) with
    app.emag_products_v2 (eMAG synchronized products) to provide a complete
    view of product presence across all channels.

    Marketplace Presence Options:
    - local_only: Products only in local database (not on eMAG)
    - emag_only: Products only on eMAG (not in local database)
    - main_only: Products only on eMAG MAIN account
    - fbe_only: Products only on eMAG FBE account
    - both_accounts: Products on both MAIN and FBE accounts
    - all: All products (default)
    """
    try:
        # Build the unified query using FULL OUTER JOIN
        # This will give us all products from both local and eMAG tables

        filters: list[str] = []
        params: dict[str, Any] = {}

        # Note: Search filter will be applied after CTE in main query
        if search:
            filters.append("(sku ILIKE :search OR name ILIKE :search)")
            params["search"] = f"%{search}%"

        # Build WHERE clause
        where_clause = " AND ".join(filters) if filters else "TRUE"

        # Main unified query
        unified_query = text(f"""
            WITH local_products AS (
                SELECT
                    p.id as local_id,
                    p.sku,
                    p.name,
                    p.description,
                    p.brand,
                    p.manufacturer,
                    p.base_price as local_price,
                    p.currency as local_currency,
                    p.is_active as local_is_active,
                    p.emag_part_number_key,
                    p.ean as local_ean,
                    p.created_at as local_created_at,
                    p.updated_at as local_updated_at
                FROM app.products p
            ),
            emag_main_products AS (
                SELECT
                    em.id as emag_id,
                    em.sku,
                    em.name,
                    em.price as emag_main_price,
                    em.stock_quantity as emag_main_stock,
                    em.is_active as emag_main_is_active,
                    em.sync_status as emag_main_sync_status,
                    em.last_synced_at as emag_main_last_synced,
                    em.emag_category_name as emag_main_category,
                    em.attributes as emag_main_attributes,
                    em.part_number_key as emag_main_pnk,
                    em.number_of_offers as emag_main_offers,
                    em.buy_button_rank as emag_main_rank
                FROM app.emag_products_v2 em
                WHERE em.account_type = 'main'
            ),
            emag_fbe_products AS (
                SELECT
                    em.id as emag_id,
                    em.sku,
                    em.name,
                    em.price as emag_fbe_price,
                    em.stock_quantity as emag_fbe_stock,
                    em.is_active as emag_fbe_is_active,
                    em.sync_status as emag_fbe_sync_status,
                    em.last_synced_at as emag_fbe_last_synced,
                    em.emag_category_name as emag_fbe_category,
                    em.attributes as emag_fbe_attributes,
                    em.part_number_key as emag_fbe_pnk,
                    em.number_of_offers as emag_fbe_offers,
                    em.buy_button_rank as emag_fbe_rank
                FROM app.emag_products_v2 em
                WHERE em.account_type = 'fbe'
            ),
            unified AS (
                SELECT
                    COALESCE(lp.sku, em.sku, ef.sku) as sku,
                    COALESCE(lp.name, em.name, ef.name) as name,
                    lp.local_id,
                    lp.description,
                    lp.brand,
                    lp.manufacturer,
                    lp.local_price,
                    lp.local_currency,
                    lp.local_is_active,
                    lp.local_created_at,
                    lp.local_updated_at,
                    em.emag_id as emag_main_id,
                    em.emag_main_price,
                    em.emag_main_stock,
                    em.emag_main_is_active,
                    em.emag_main_sync_status,
                    em.emag_main_last_synced,
                    em.emag_main_category,
                    em.emag_main_pnk,
                    em.emag_main_offers,
                    em.emag_main_rank,
                    ef.emag_id as emag_fbe_id,
                    ef.emag_fbe_price,
                    ef.emag_fbe_stock,
                    ef.emag_fbe_is_active,
                    ef.emag_fbe_sync_status,
                    ef.emag_fbe_last_synced,
                    ef.emag_fbe_category,
                    ef.emag_fbe_pnk,
                    ef.emag_fbe_offers,
                    ef.emag_fbe_rank,
                    -- Marketplace presence flags
                    CASE WHEN lp.local_id IS NOT NULL THEN true ELSE false END as has_local,
                    CASE WHEN em.emag_id IS NOT NULL THEN true ELSE false END as has_emag_main,
                    CASE WHEN ef.emag_id IS NOT NULL THEN true ELSE false END as has_emag_fbe,
                    -- Computed fields
                    CASE
                        WHEN lp.local_id IS NOT NULL AND em.emag_id IS NULL AND ef.emag_id IS NULL THEN 'local_only'
                        WHEN lp.local_id IS NULL AND (em.emag_id IS NOT NULL OR ef.emag_id IS NOT NULL) THEN 'emag_only'
                        WHEN em.emag_id IS NOT NULL AND ef.emag_id IS NOT NULL THEN 'both_accounts'
                        WHEN em.emag_id IS NOT NULL AND ef.emag_id IS NULL THEN 'main_only'
                        WHEN em.emag_id IS NULL AND ef.emag_id IS NOT NULL THEN 'fbe_only'
                        ELSE 'unknown'
                    END as marketplace_presence,
                    GREATEST(lp.local_updated_at, em.emag_main_last_synced, ef.emag_fbe_last_synced) as last_updated
                FROM local_products lp
                FULL OUTER JOIN emag_main_products em ON lp.sku = em.sku
                FULL OUTER JOIN emag_fbe_products ef ON COALESCE(lp.sku, em.sku) = ef.sku
            )
            SELECT * FROM unified
            WHERE {where_clause}
            ORDER BY last_updated DESC NULLS LAST
            LIMIT :limit OFFSET :skip
        """)

        # Count query
        count_query = text(f"""
            WITH local_products AS (
                SELECT p.id as local_id, p.sku, p.name, p.updated_at as local_updated_at
                FROM app.products p
            ),
            emag_main_products AS (
                SELECT em.id as emag_id, em.sku, em.name, em.last_synced_at as emag_main_last_synced
                FROM app.emag_products_v2 em WHERE em.account_type = 'main'
            ),
            emag_fbe_products AS (
                SELECT em.id as emag_id, em.sku, em.name, em.last_synced_at as emag_fbe_last_synced
                FROM app.emag_products_v2 em WHERE em.account_type = 'fbe'
            ),
            unified AS (
                SELECT
                    COALESCE(lp.sku, em.sku, ef.sku) as sku,
                    COALESCE(lp.name, em.name, ef.name) as name,
                    lp.local_id,
                    em.emag_id as emag_main_id,
                    ef.emag_id as emag_fbe_id,
                    GREATEST(lp.local_updated_at, em.emag_main_last_synced, ef.emag_fbe_last_synced) as last_updated
                FROM local_products lp
                FULL OUTER JOIN emag_main_products em ON lp.sku = em.sku
                FULL OUTER JOIN emag_fbe_products ef ON COALESCE(lp.sku, em.sku) = ef.sku
            )
            SELECT COUNT(*) FROM unified WHERE {where_clause}
        """)

        # Summary statistics query
        summary_query = text("""
            WITH local_products AS (
                SELECT p.id as local_id, p.sku FROM app.products p
            ),
            emag_main_products AS (
                SELECT em.id as emag_id, em.sku FROM app.emag_products_v2 em WHERE em.account_type = 'main'
            ),
            emag_fbe_products AS (
                SELECT em.id as emag_id, em.sku FROM app.emag_products_v2 em WHERE em.account_type = 'fbe'
            ),
            unified AS (
                SELECT
                    lp.local_id,
                    em.emag_id as emag_main_id,
                    ef.emag_id as emag_fbe_id
                FROM local_products lp
                FULL OUTER JOIN emag_main_products em ON lp.sku = em.sku
                FULL OUTER JOIN emag_fbe_products ef ON COALESCE(lp.sku, em.sku) = ef.sku
            )
            SELECT
                COUNT(*) as total_products,
                COUNT(local_id) as local_products,
                COUNT(emag_main_id) as emag_main_products,
                COUNT(emag_fbe_id) as emag_fbe_products,
                COUNT(*) FILTER (WHERE local_id IS NOT NULL AND emag_main_id IS NULL AND emag_fbe_id IS NULL) as local_only,
                COUNT(*) FILTER (WHERE local_id IS NULL AND (emag_main_id IS NOT NULL OR emag_fbe_id IS NOT NULL)) as emag_only,
                COUNT(*) FILTER (WHERE emag_main_id IS NOT NULL AND emag_fbe_id IS NOT NULL) as both_accounts,
                COUNT(*) FILTER (WHERE emag_main_id IS NOT NULL AND emag_fbe_id IS NULL) as main_only,
                COUNT(*) FILTER (WHERE emag_main_id IS NULL AND emag_fbe_id IS NOT NULL) as fbe_only
            FROM unified
        """)

        # Execute queries
        params.update({"limit": limit, "skip": skip})

        product_rows = (await db.execute(unified_query, params)).mappings().all()
        total_count = (await db.execute(count_query, params)).scalar_one_or_none() or 0
        summary_row = (await db.execute(summary_query)).mappings().first() or {}

        # Format products for frontend
        formatted_products = []
        for row in product_rows:
            # Determine marketplace badges
            badges = []
            if row.get("has_local"):
                badges.append("local")
            if row.get("has_emag_main"):
                badges.append("emag_main")
            if row.get("has_emag_fbe"):
                badges.append("emag_fbe")

            # Price comparison
            price_info = {
                "local_price": float(row.get("local_price"))
                if row.get("local_price")
                else None,
                "emag_main_price": float(row.get("emag_main_price"))
                if row.get("emag_main_price")
                else None,
                "emag_fbe_price": float(row.get("emag_fbe_price"))
                if row.get("emag_fbe_price")
                else None,
                "has_price_difference": False,
            }

            # Check for price differences
            prices = [
                p
                for p in [
                    price_info["local_price"],
                    price_info["emag_main_price"],
                    price_info["emag_fbe_price"],
                ]
                if p is not None
            ]
            if len(prices) > 1:
                price_info["has_price_difference"] = max(prices) - min(prices) > 0.01

            # Check PNK consistency
            pnk_main = row.get("emag_main_pnk")
            pnk_fbe = row.get("emag_fbe_pnk")
            pnk_status = "unknown"
            pnk_consistent = True

            if pnk_main and pnk_fbe:
                if pnk_main == pnk_fbe:
                    pnk_status = "consistent"
                    pnk_consistent = True
                else:
                    pnk_status = "inconsistent"
                    pnk_consistent = False
            elif pnk_main or pnk_fbe:
                pnk_status = "partial"
                pnk_consistent = False
            else:
                pnk_status = "missing"
                pnk_consistent = False

            # Check for competition
            has_competition = False
            competition_level = "none"
            if row.get("has_emag_main") and (row.get("emag_main_offers") or 1) > 1:
                has_competition = True
                offers = row.get("emag_main_offers") or 1
                if offers >= 5:
                    competition_level = "high"
                elif offers >= 3:
                    competition_level = "medium"
                else:
                    competition_level = "low"
            if row.get("has_emag_fbe") and (row.get("emag_fbe_offers") or 1) > 1:
                has_competition = True
                offers = row.get("emag_fbe_offers") or 1
                if offers >= 5:
                    competition_level = "high"
                elif offers >= 3 and competition_level != "high":
                    competition_level = "medium"

            formatted_products.append(
                {
                    "sku": row.get("sku"),
                    "name": row.get("name"),
                    "description": row.get("description"),
                    "brand": row.get("brand"),
                    "manufacturer": row.get("manufacturer"),
                    "marketplace_presence": row.get("marketplace_presence"),
                    "badges": badges,
                    "local": {
                        "id": str(row.get("local_id")) if row.get("local_id") else None,
                        "price": price_info["local_price"],
                        "currency": row.get("local_currency") or "RON",
                        "is_active": row.get("local_is_active"),
                        "updated_at": row.get("local_updated_at").isoformat()
                        if row.get("local_updated_at")
                        else None,
                    }
                    if row.get("has_local")
                    else None,
                    "emag_main": {
                        "id": str(row.get("emag_main_id"))
                        if row.get("emag_main_id")
                        else None,
                        "price": price_info["emag_main_price"],
                        "stock": int(row.get("emag_main_stock") or 0),
                        "is_active": row.get("emag_main_is_active"),
                        "sync_status": row.get("emag_main_sync_status"),
                        "last_synced": row.get("emag_main_last_synced").isoformat()
                        if row.get("emag_main_last_synced")
                        else None,
                        "category": row.get("emag_main_category"),
                        "part_number_key": row.get("emag_main_pnk"),
                        "number_of_offers": int(row.get("emag_main_offers") or 1),
                        "buy_button_rank": int(row.get("emag_main_rank"))
                        if row.get("emag_main_rank")
                        else None,
                        "has_competitors": (row.get("emag_main_offers") or 1) > 1,
                    }
                    if row.get("has_emag_main")
                    else None,
                    "emag_fbe": {
                        "id": str(row.get("emag_fbe_id"))
                        if row.get("emag_fbe_id")
                        else None,
                        "price": price_info["emag_fbe_price"],
                        "stock": int(row.get("emag_fbe_stock") or 0),
                        "is_active": row.get("emag_fbe_is_active"),
                        "sync_status": row.get("emag_fbe_sync_status"),
                        "last_synced": row.get("emag_fbe_last_synced").isoformat()
                        if row.get("emag_fbe_last_synced")
                        else None,
                        "category": row.get("emag_fbe_category"),
                        "part_number_key": row.get("emag_fbe_pnk"),
                        "number_of_offers": int(row.get("emag_fbe_offers") or 1),
                        "buy_button_rank": int(row.get("emag_fbe_rank"))
                        if row.get("emag_fbe_rank")
                        else None,
                        "has_competitors": (row.get("emag_fbe_offers") or 1) > 1,
                    }
                    if row.get("has_emag_fbe")
                    else None,
                    "price_info": price_info,
                    "pnk_info": {
                        "pnk_main": pnk_main,
                        "pnk_fbe": pnk_fbe,
                        "status": pnk_status,
                        "is_consistent": pnk_consistent,
                    },
                    "competition_info": {
                        "has_competition": has_competition,
                        "level": competition_level,
                    },
                    "last_updated": row.get("last_updated").isoformat()
                    if row.get("last_updated")
                    else None,
                }
            )

        # Format summary
        summary = {
            "total_products": int(summary_row.get("total_products") or 0),
            "local_products": int(summary_row.get("local_products") or 0),
            "emag_main_products": int(summary_row.get("emag_main_products") or 0),
            "emag_fbe_products": int(summary_row.get("emag_fbe_products") or 0),
            "breakdown": {
                "local_only": int(summary_row.get("local_only") or 0),
                "emag_only": int(summary_row.get("emag_only") or 0),
                "both_accounts": int(summary_row.get("both_accounts") or 0),
                "main_only": int(summary_row.get("main_only") or 0),
                "fbe_only": int(summary_row.get("fbe_only") or 0),
            },
        }

        return {
            "status": "success",
            "data": {
                "products": formatted_products,
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
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch unified products: {exc}"
        )
