-- Test Script for Sold Quantity Feature
-- Run this in your PostgreSQL client to verify data

-- ============================================================================
-- 1. Check if there are eMAG orders in the last 6 months
-- ============================================================================
SELECT 
    COUNT(*) as total_orders,
    COUNT(DISTINCT emag_order_id) as unique_orders,
    MIN(order_date) as earliest_order,
    MAX(order_date) as latest_order,
    account_type
FROM app.emag_orders
WHERE order_date >= NOW() - INTERVAL '6 months'
  AND status IN (3, 4)  -- prepared, finalized
  AND products IS NOT NULL
GROUP BY account_type;

-- ============================================================================
-- 2. Find products with eMAG sales (sample 10)
-- ============================================================================
WITH emag_products AS (
    SELECT DISTINCT
        jsonb_array_elements(products)->>'part_number_key' as sku,
        jsonb_array_elements(products)->>'sku' as sku_alt,
        COUNT(*) as order_count
    FROM app.emag_orders
    WHERE order_date >= NOW() - INTERVAL '6 months'
      AND status IN (3, 4)
      AND products IS NOT NULL
    GROUP BY 1, 2
)
SELECT 
    COALESCE(sku, sku_alt) as product_sku,
    order_count
FROM emag_products
WHERE COALESCE(sku, sku_alt) IS NOT NULL
ORDER BY order_count DESC
LIMIT 10;

-- ============================================================================
-- 3. Check sales orders in last 6 months
-- ============================================================================
SELECT 
    COUNT(*) as total_lines,
    COUNT(DISTINCT sales_order_id) as unique_orders,
    SUM(quantity) as total_quantity
FROM app.sales_order_lines sol
JOIN app.sales_orders so ON sol.sales_order_id = so.id
WHERE so.order_date >= NOW() - INTERVAL '6 months'
  AND so.status IN ('confirmed', 'processing', 'shipped', 'delivered');

-- ============================================================================
-- 4. Check generic orders in last 6 months
-- ============================================================================
SELECT 
    COUNT(*) as total_lines,
    COUNT(DISTINCT order_id) as unique_orders,
    SUM(quantity) as total_quantity
FROM app.order_lines ol
JOIN app.orders o ON ol.order_id = o.id
WHERE o.order_date >= NOW() - INTERVAL '6 months'
  AND o.status IN ('confirmed', 'processing', 'shipped', 'delivered', 'completed');

-- ============================================================================
-- 5. Detailed analysis for a specific SKU (REPLACE 'YOUR_SKU_HERE')
-- ============================================================================
-- Replace 'YOUR_SKU_HERE' with actual SKU
DO $$
DECLARE
    test_sku TEXT := 'YOUR_SKU_HERE';  -- CHANGE THIS
    product_id_var INT;
    emag_qty INT := 0;
    sales_qty INT := 0;
    orders_qty INT := 0;
    total_qty INT := 0;
    avg_monthly NUMERIC;
BEGIN
    -- Get product ID
    SELECT id INTO product_id_var
    FROM app.products
    WHERE sku = test_sku;
    
    IF product_id_var IS NULL THEN
        RAISE NOTICE 'Product with SKU % not found', test_sku;
        RETURN;
    END IF;
    
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Testing SKU: %', test_sku;
    RAISE NOTICE 'Product ID: %', product_id_var;
    RAISE NOTICE '========================================';
    
    -- Count eMAG sales
    SELECT COUNT(*) INTO emag_qty
    FROM app.emag_orders
    WHERE order_date >= NOW() - INTERVAL '6 months'
      AND status IN (3, 4)
      AND products::text LIKE '%' || test_sku || '%';
    
    RAISE NOTICE 'eMAG Orders: % orders', emag_qty;
    
    -- Count sales orders
    SELECT COALESCE(SUM(sol.quantity), 0) INTO sales_qty
    FROM app.sales_order_lines sol
    JOIN app.sales_orders so ON sol.sales_order_id = so.id
    WHERE sol.product_id = product_id_var
      AND so.order_date >= NOW() - INTERVAL '6 months'
      AND so.status IN ('confirmed', 'processing', 'shipped', 'delivered');
    
    RAISE NOTICE 'Sales Orders: % units', sales_qty;
    
    -- Count generic orders
    SELECT COALESCE(SUM(ol.quantity), 0) INTO orders_qty
    FROM app.order_lines ol
    JOIN app.orders o ON ol.order_id = o.id
    WHERE ol.product_id = product_id_var
      AND o.order_date >= NOW() - INTERVAL '6 months'
      AND o.status IN ('confirmed', 'processing', 'shipped', 'delivered', 'completed');
    
    RAISE NOTICE 'Generic Orders: % units', orders_qty;
    
    -- Calculate totals
    total_qty := emag_qty + sales_qty + orders_qty;
    avg_monthly := ROUND(total_qty / 6.0, 2);
    
    RAISE NOTICE '========================================';
    RAISE NOTICE 'TOTAL SOLD: % units', total_qty;
    RAISE NOTICE 'AVG/MONTH: % units', avg_monthly;
    RAISE NOTICE '========================================';
    
    -- Velocity classification
    IF avg_monthly >= 10 THEN
        RAISE NOTICE 'Velocity: HIGH DEMAND (>= 10/month)';
    ELSIF avg_monthly >= 5 THEN
        RAISE NOTICE 'Velocity: MEDIUM DEMAND (5-9/month)';
    ELSIF avg_monthly >= 1 THEN
        RAISE NOTICE 'Velocity: LOW DEMAND (1-4/month)';
    ELSE
        RAISE NOTICE 'Velocity: VERY LOW DEMAND (< 1/month)';
    END IF;
END $$;

-- ============================================================================
-- 6. Get sample SKUs with actual sales
-- ============================================================================
SELECT 
    p.sku,
    p.name,
    p.chinese_name,
    -- Count from different sources
    (SELECT COUNT(*) 
     FROM app.emag_orders eo
     WHERE eo.order_date >= NOW() - INTERVAL '6 months'
       AND eo.status IN (3, 4)
       AND eo.products::text LIKE '%' || p.sku || '%') as emag_orders,
    
    (SELECT COALESCE(SUM(sol.quantity), 0)
     FROM app.sales_order_lines sol
     JOIN app.sales_orders so ON sol.sales_order_id = so.id
     WHERE sol.product_id = p.id
       AND so.order_date >= NOW() - INTERVAL '6 months'
       AND so.status IN ('confirmed', 'processing', 'shipped', 'delivered')) as sales_qty,
    
    (SELECT COALESCE(SUM(ol.quantity), 0)
     FROM app.order_lines ol
     JOIN app.orders o ON ol.order_id = o.id
     WHERE ol.product_id = p.id
       AND o.order_date >= NOW() - INTERVAL '6 months'
       AND o.status IN ('confirmed', 'processing', 'shipped', 'delivered', 'completed')) as orders_qty
FROM app.products p
WHERE p.is_active = true
LIMIT 20;

-- ============================================================================
-- 7. Test query performance
-- ============================================================================
EXPLAIN ANALYZE
SELECT 
    p.id,
    p.sku,
    p.name,
    -- This simulates what the backend function does
    (SELECT COUNT(*) 
     FROM app.emag_orders eo
     WHERE eo.order_date >= NOW() - INTERVAL '6 months'
       AND eo.status IN (3, 4)
       AND eo.products::text LIKE '%' || p.sku || '%') as emag_count
FROM app.products p
WHERE p.is_active = true
LIMIT 10;
