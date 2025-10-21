-- ============================================================================
-- TESTARE COMPLETĂ - SKU: EMG258
-- Data: 2025-10-14
-- ============================================================================

\echo '========================================================================'
\echo 'TESTARE SOLD QUANTITY PENTRU SKU: EMG258'
\echo '========================================================================'

-- ============================================================================
-- 1. Verificare Produs
-- ============================================================================
\echo ''
\echo '1️⃣  VERIFICARE PRODUS'
\echo '------------------------------------------------------------------------'

SELECT 
    id as product_id,
    sku,
    name,
    chinese_name,
    base_price,
    currency,
    is_active,
    is_discontinued,
    created_at
FROM app.products
WHERE sku = 'EMG258';

-- ============================================================================
-- 2. Verificare Inventory Items
-- ============================================================================
\echo ''
\echo '2️⃣  VERIFICARE INVENTORY ITEMS'
\echo '------------------------------------------------------------------------'

SELECT 
    ii.id as inventory_item_id,
    ii.product_id,
    w.name as warehouse_name,
    w.code as warehouse_code,
    ii.quantity,
    ii.reserved_quantity,
    (ii.quantity - ii.reserved_quantity) as available_quantity,
    ii.minimum_stock,
    ii.reorder_point,
    ii.maximum_stock,
    ii.manual_reorder_quantity
FROM app.inventory_items ii
JOIN app.warehouses w ON ii.warehouse_id = w.id
JOIN app.products p ON ii.product_id = p.id
WHERE p.sku = 'EMG258'
  AND ii.is_active = true;

-- ============================================================================
-- 3. Verificare eMAG Orders (Ultimele 6 Luni)
-- ============================================================================
\echo ''
\echo '3️⃣  VERIFICARE eMAG ORDERS (Ultimele 6 Luni)'
\echo '------------------------------------------------------------------------'

WITH emag_sales AS (
    SELECT 
        eo.emag_order_id,
        eo.order_date,
        eo.status,
        eo.account_type,
        eo.total_amount,
        eo.currency,
        jsonb_array_elements(eo.products) as product_item
    FROM app.emag_orders eo
    WHERE eo.order_date >= NOW() - INTERVAL '6 months'
      AND eo.status IN (3, 4)  -- 3=prepared, 4=finalized
      AND eo.products IS NOT NULL
)
SELECT 
    emag_order_id,
    order_date,
    CASE status
        WHEN 3 THEN 'prepared'
        WHEN 4 THEN 'finalized'
    END as status_name,
    account_type,
    product_item->>'part_number_key' as sku,
    (product_item->>'quantity')::int as quantity,
    product_item->>'name' as product_name,
    total_amount,
    currency
FROM emag_sales
WHERE product_item->>'part_number_key' = 'EMG258'
   OR product_item->>'sku' = 'EMG258'
ORDER BY order_date DESC;

-- Summary eMAG
\echo ''
\echo '📊 SUMAR eMAG:'
SELECT 
    COUNT(*) as total_orders,
    SUM((product_item->>'quantity')::int) as total_quantity,
    MIN(order_date) as first_order,
    MAX(order_date) as last_order,
    ROUND(SUM((product_item->>'quantity')::int) / 6.0, 2) as avg_per_month
FROM (
    SELECT 
        eo.order_date,
        jsonb_array_elements(eo.products) as product_item
    FROM app.emag_orders eo
    WHERE eo.order_date >= NOW() - INTERVAL '6 months'
      AND eo.status IN (3, 4)
      AND eo.products IS NOT NULL
) sub
WHERE product_item->>'part_number_key' = 'EMG258'
   OR product_item->>'sku' = 'EMG258';

-- ============================================================================
-- 4. Verificare Sales Orders (Ultimele 6 Luni)
-- ============================================================================
\echo ''
\echo '4️⃣  VERIFICARE SALES ORDERS (Ultimele 6 Luni)'
\echo '------------------------------------------------------------------------'

SELECT 
    so.order_number,
    so.order_date,
    so.status,
    sol.quantity,
    sol.unit_price,
    sol.line_total,
    c.name as customer_name
FROM app.sales_order_lines sol
JOIN app.sales_orders so ON sol.sales_order_id = so.id
LEFT JOIN app.customers c ON so.customer_id = c.id
JOIN app.products p ON sol.product_id = p.id
WHERE p.sku = 'EMG258'
  AND so.order_date >= NOW() - INTERVAL '6 months'
  AND so.status IN ('confirmed', 'processing', 'shipped', 'delivered')
ORDER BY so.order_date DESC;

-- Summary Sales Orders
\echo ''
\echo '📊 SUMAR SALES ORDERS:'
SELECT 
    COUNT(*) as total_orders,
    COALESCE(SUM(sol.quantity), 0) as total_quantity,
    MIN(so.order_date) as first_order,
    MAX(so.order_date) as last_order,
    ROUND(COALESCE(SUM(sol.quantity), 0) / 6.0, 2) as avg_per_month
FROM app.sales_order_lines sol
JOIN app.sales_orders so ON sol.sales_order_id = so.id
JOIN app.products p ON sol.product_id = p.id
WHERE p.sku = 'EMG258'
  AND so.order_date >= NOW() - INTERVAL '6 months'
  AND so.status IN ('confirmed', 'processing', 'shipped', 'delivered');

-- ============================================================================
-- 5. Verificare Generic Orders (Ultimele 6 Luni)
-- ============================================================================
\echo ''
\echo '5️⃣  VERIFICARE GENERIC ORDERS (Ultimele 6 Luni)'
\echo '------------------------------------------------------------------------'

SELECT 
    o.id as order_id,
    o.order_date,
    o.status,
    ol.quantity,
    ol.unit_price,
    u.email as customer_email
FROM app.order_lines ol
JOIN app.orders o ON ol.order_id = o.id
LEFT JOIN app.users u ON o.customer_id = u.id
JOIN app.products p ON ol.product_id = p.id
WHERE p.sku = 'EMG258'
  AND o.order_date >= NOW() - INTERVAL '6 months'
  AND o.status IN ('confirmed', 'processing', 'shipped', 'delivered', 'completed')
ORDER BY o.order_date DESC;

-- Summary Generic Orders
\echo ''
\echo '📊 SUMAR GENERIC ORDERS:'
SELECT 
    COUNT(*) as total_orders,
    COALESCE(SUM(ol.quantity), 0) as total_quantity,
    MIN(o.order_date) as first_order,
    MAX(o.order_date) as last_order,
    ROUND(COALESCE(SUM(ol.quantity), 0) / 6.0, 2) as avg_per_month
FROM app.order_lines ol
JOIN app.orders o ON ol.order_id = o.id
JOIN app.products p ON ol.product_id = p.id
WHERE p.sku = 'EMG258'
  AND o.order_date >= NOW() - INTERVAL '6 months'
  AND o.status IN ('confirmed', 'processing', 'shipped', 'delivered', 'completed');

-- ============================================================================
-- 6. CALCUL FINAL - TOTAL SOLD LAST 6 MONTHS
-- ============================================================================
\echo ''
\echo '6️⃣  CALCUL FINAL - TOTAL SOLD LAST 6 MONTHS'
\echo '========================================================================'

WITH product_info AS (
    SELECT id, sku, name FROM app.products WHERE sku = 'EMG258'
),
emag_qty AS (
    SELECT 
        COALESCE(SUM((product_item->>'quantity')::int), 0) as qty
    FROM (
        SELECT jsonb_array_elements(eo.products) as product_item
        FROM app.emag_orders eo
        WHERE eo.order_date >= NOW() - INTERVAL '6 months'
          AND eo.status IN (3, 4)
          AND eo.products IS NOT NULL
    ) sub
    WHERE product_item->>'part_number_key' = 'EMG258'
       OR product_item->>'sku' = 'EMG258'
),
sales_qty AS (
    SELECT COALESCE(SUM(sol.quantity), 0) as qty
    FROM app.sales_order_lines sol
    JOIN app.sales_orders so ON sol.sales_order_id = so.id
    JOIN app.products p ON sol.product_id = p.id
    WHERE p.sku = 'EMG258'
      AND so.order_date >= NOW() - INTERVAL '6 months'
      AND so.status IN ('confirmed', 'processing', 'shipped', 'delivered')
),
orders_qty AS (
    SELECT COALESCE(SUM(ol.quantity), 0) as qty
    FROM app.order_lines ol
    JOIN app.orders o ON ol.order_id = o.id
    JOIN app.products p ON ol.product_id = p.id
    WHERE p.sku = 'EMG258'
      AND o.order_date >= NOW() - INTERVAL '6 months'
      AND o.status IN ('confirmed', 'processing', 'shipped', 'delivered', 'completed')
)
SELECT 
    pi.sku,
    pi.name,
    eq.qty as emag_quantity,
    sq.qty as sales_orders_quantity,
    oq.qty as generic_orders_quantity,
    '────────────────────────────────' as separator,
    (eq.qty + sq.qty + oq.qty) as TOTAL_SOLD_6_MONTHS,
    ROUND((eq.qty + sq.qty + oq.qty) / 6.0, 2) as AVG_MONTHLY_SALES,
    '────────────────────────────────' as separator2,
    CASE 
        WHEN ROUND((eq.qty + sq.qty + oq.qty) / 6.0, 2) >= 10 THEN '🔥 HIGH DEMAND (≥10/month) - RED'
        WHEN ROUND((eq.qty + sq.qty + oq.qty) / 6.0, 2) >= 5 THEN '📈 MEDIUM DEMAND (5-9/month) - ORANGE'
        WHEN ROUND((eq.qty + sq.qty + oq.qty) / 6.0, 2) >= 1 THEN '📊 LOW DEMAND (1-4/month) - BLUE'
        ELSE '📉 VERY LOW DEMAND (<1/month) - GRAY'
    END as SALES_VELOCITY
FROM product_info pi
CROSS JOIN emag_qty eq
CROSS JOIN sales_qty sq
CROSS JOIN orders_qty oq;

-- ============================================================================
-- 7. VERIFICARE SUPPLIERS
-- ============================================================================
\echo ''
\echo '7️⃣  VERIFICARE SUPPLIERS'
\echo '------------------------------------------------------------------------'

-- Suppliers from Google Sheets
SELECT 
    'Google Sheets' as source,
    pss.supplier_name,
    pss.price_cny as price,
    'CNY' as currency,
    pss.calculated_price_ron as price_ron,
    pss.is_preferred,
    pss.is_verified,
    pss.supplier_url
FROM app.product_supplier_sheets pss
WHERE pss.sku = 'EMG258'
  AND pss.is_active = true

UNION ALL

-- Suppliers from 1688
SELECT 
    '1688.com' as source,
    s.name as supplier_name,
    sp.supplier_price as price,
    sp.supplier_currency as currency,
    NULL as price_ron,
    sp.is_preferred,
    sp.manual_confirmed as is_verified,
    sp.supplier_product_url as supplier_url
FROM app.supplier_products sp
JOIN app.suppliers s ON sp.supplier_id = s.id
JOIN app.products p ON sp.local_product_id = p.id
WHERE p.sku = 'EMG258'
  AND sp.is_active = true;

-- ============================================================================
-- 8. RECOMANDARE REORDER QUANTITY
-- ============================================================================
\echo ''
\echo '8️⃣  RECOMANDARE REORDER QUANTITY'
\echo '------------------------------------------------------------------------'

WITH sold_data AS (
    SELECT 
        ROUND((
            COALESCE((
                SELECT SUM((product_item->>'quantity')::int)
                FROM (
                    SELECT jsonb_array_elements(eo.products) as product_item
                    FROM app.emag_orders eo
                    WHERE eo.order_date >= NOW() - INTERVAL '6 months'
                      AND eo.status IN (3, 4)
                ) sub
                WHERE product_item->>'part_number_key' = 'EMG258'
            ), 0) +
            COALESCE((
                SELECT SUM(sol.quantity)
                FROM app.sales_order_lines sol
                JOIN app.sales_orders so ON sol.sales_order_id = so.id
                JOIN app.products p ON sol.product_id = p.id
                WHERE p.sku = 'EMG258'
                  AND so.order_date >= NOW() - INTERVAL '6 months'
                  AND so.status IN ('confirmed', 'processing', 'shipped', 'delivered')
            ), 0) +
            COALESCE((
                SELECT SUM(ol.quantity)
                FROM app.order_lines ol
                JOIN app.orders o ON ol.order_id = o.id
                JOIN app.products p ON ol.product_id = p.id
                WHERE p.sku = 'EMG258'
                  AND o.order_date >= NOW() - INTERVAL '6 months'
                  AND o.status IN ('confirmed', 'processing', 'shipped', 'delivered', 'completed')
            ), 0)
        ) / 6.0, 2) as avg_monthly
)
SELECT 
    ii.quantity as current_stock,
    ii.reserved_quantity,
    (ii.quantity - ii.reserved_quantity) as available_stock,
    ii.minimum_stock,
    ii.reorder_point,
    ii.maximum_stock,
    ii.manual_reorder_quantity,
    sd.avg_monthly as avg_monthly_sales,
    '────────────────────────────────' as separator,
    -- Calculare reorder quantity recomandat
    CASE 
        WHEN ii.manual_reorder_quantity IS NOT NULL THEN ii.manual_reorder_quantity
        WHEN ii.maximum_stock IS NOT NULL THEN GREATEST(0, ii.maximum_stock - (ii.quantity - ii.reserved_quantity))
        WHEN ii.reorder_point > 0 THEN GREATEST(0, (ii.reorder_point * 2) - (ii.quantity - ii.reserved_quantity))
        ELSE GREATEST(0, (ii.minimum_stock * 3) - (ii.quantity - ii.reserved_quantity))
    END as calculated_reorder_qty,
    '────────────────────────────────' as separator2,
    -- Recomandare bazată pe vânzări
    CASE 
        WHEN sd.avg_monthly > 0 THEN 
            GREATEST(0, 
                ROUND(sd.avg_monthly * 2)::int +  -- 2 luni de stoc
                ROUND(sd.avg_monthly * 1.5)::int - -- Safety stock
                (ii.quantity - ii.reserved_quantity)
            )
        ELSE NULL
    END as smart_reorder_recommendation
FROM app.inventory_items ii
JOIN app.products p ON ii.product_id = p.id
CROSS JOIN sold_data sd
WHERE p.sku = 'EMG258'
  AND ii.is_active = true;

\echo ''
\echo '========================================================================'
\echo '✅ TESTARE COMPLETĂ FINALIZATĂ'
\echo '========================================================================'
