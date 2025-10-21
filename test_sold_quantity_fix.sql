-- Test pentru verificare fix sold quantity
-- Acest script simulează exact ce face funcția calculate_sold_quantity_last_6_months

\echo '========================================================================='
\echo 'TEST SOLD QUANTITY FIX - Verificare Mapare SKU'
\echo '========================================================================='
\echo ''

-- 1. Găsește produsul EMG463 (care are part_number_key DVX0FSYBM în eMAG)
\echo '1️⃣  PRODUS LOCAL (din tabela products):'
\echo '─────────────────────────────────────────────────────────────────────────'
SELECT 
    id as product_id,
    sku as local_sku,
    name
FROM app.products
WHERE sku = 'EMG463'
LIMIT 1;

\echo ''
\echo '2️⃣  MAPARE eMAG (din tabela emag_products_v2):'
\echo '─────────────────────────────────────────────────────────────────────────'
SELECT 
    sku as local_sku,
    part_number_key as emag_part_number,
    name,
    account_type
FROM app.emag_products_v2
WHERE sku = 'EMG463';

\echo ''
\echo '3️⃣  VÂNZĂRI eMAG (din tabela emag_orders):'
\echo '─────────────────────────────────────────────────────────────────────────'
-- Calculează vânzări pentru DVX0FSYBM (part_number_key)
WITH emag_sales AS (
    SELECT 
        product_item->>'part_number_key' as part_number_key,
        (product_item->>'quantity')::int as quantity,
        eo.order_date,
        eo.emag_order_id,
        eo.account_type
    FROM app.emag_orders eo,
    LATERAL jsonb_array_elements(eo.products) as product_item
    WHERE eo.order_date >= NOW() - INTERVAL '6 months'
      AND eo.status IN (3, 4)
      AND eo.products IS NOT NULL
      AND product_item->>'part_number_key' = 'DVX0FSYBM'
)
SELECT 
    part_number_key,
    SUM(quantity) as total_sold_6m,
    ROUND(SUM(quantity) / 6.0, 2) as avg_monthly,
    COUNT(DISTINCT emag_order_id) as order_count,
    string_agg(DISTINCT account_type, ', ') as accounts
FROM emag_sales
GROUP BY part_number_key;

\echo ''
\echo '4️⃣  VERIFICARE COMPLETĂ - Mapare SKU Local -> eMAG -> Vânzări:'
\echo '─────────────────────────────────────────────────────────────────────────'
WITH product_mapping AS (
    -- Mapare produs local -> eMAG part_number_key
    SELECT 
        p.id as product_id,
        p.sku as local_sku,
        p.name as product_name,
        ep.part_number_key as emag_part_number,
        ep.account_type
    FROM app.products p
    JOIN app.emag_products_v2 ep ON p.sku = ep.sku
    WHERE p.sku = 'EMG463'
),
emag_sales AS (
    -- Vânzări din eMAG pentru part_number_key
    SELECT 
        product_item->>'part_number_key' as part_number_key,
        SUM((product_item->>'quantity')::int) as total_quantity,
        COUNT(DISTINCT eo.emag_order_id) as order_count
    FROM app.emag_orders eo,
    LATERAL jsonb_array_elements(eo.products) as product_item
    WHERE eo.order_date >= NOW() - INTERVAL '6 months'
      AND eo.status IN (3, 4)
      AND eo.products IS NOT NULL
      AND product_item->>'part_number_key' IN (
          SELECT part_number_key FROM product_mapping
      )
    GROUP BY product_item->>'part_number_key'
)
SELECT 
    pm.product_id,
    pm.local_sku,
    pm.product_name,
    pm.emag_part_number,
    COALESCE(es.total_quantity, 0) as sold_last_6_months,
    ROUND(COALESCE(es.total_quantity, 0) / 6.0, 2) as avg_monthly_sales,
    COALESCE(es.order_count, 0) as order_count,
    CASE 
        WHEN ROUND(COALESCE(es.total_quantity, 0) / 6.0, 2) >= 10 THEN '🔥 HIGH DEMAND'
        WHEN ROUND(COALESCE(es.total_quantity, 0) / 6.0, 2) >= 5 THEN '📈 MEDIUM DEMAND'
        WHEN ROUND(COALESCE(es.total_quantity, 0) / 6.0, 2) >= 1 THEN '📊 LOW DEMAND'
        ELSE '📉 VERY LOW'
    END as velocity_classification
FROM product_mapping pm
LEFT JOIN emag_sales es ON pm.emag_part_number = es.part_number_key;

\echo ''
\echo '5️⃣  TEST PENTRU TOP 5 PRODUSE CU VÂNZĂRI:'
\echo '─────────────────────────────────────────────────────────────────────────'
WITH product_mapping AS (
    SELECT 
        p.id as product_id,
        p.sku as local_sku,
        p.name as product_name,
        ep.part_number_key as emag_part_number
    FROM app.products p
    JOIN app.emag_products_v2 ep ON p.sku = ep.sku
    WHERE ep.part_number_key IS NOT NULL
),
emag_sales AS (
    SELECT 
        product_item->>'part_number_key' as part_number_key,
        SUM((product_item->>'quantity')::int) as total_quantity
    FROM app.emag_orders eo,
    LATERAL jsonb_array_elements(eo.products) as product_item
    WHERE eo.order_date >= NOW() - INTERVAL '6 months'
      AND eo.status IN (3, 4)
      AND eo.products IS NOT NULL
    GROUP BY product_item->>'part_number_key'
)
SELECT 
    pm.product_id,
    pm.local_sku,
    LEFT(pm.product_name, 40) as product_name,
    pm.emag_part_number,
    COALESCE(es.total_quantity, 0) as sold_6m,
    ROUND(COALESCE(es.total_quantity, 0) / 6.0, 2) as avg_monthly
FROM product_mapping pm
LEFT JOIN emag_sales es ON pm.emag_part_number = es.part_number_key
WHERE es.total_quantity > 0
ORDER BY es.total_quantity DESC
LIMIT 5;

\echo ''
\echo '========================================================================='
\echo '✅ TEST COMPLET'
\echo '========================================================================='
\echo ''
\echo 'CONCLUZIE:'
\echo '  - Dacă vezi sold_last_6_months = 34 pentru EMG463, fix-ul funcționează!'
\echo '  - Dacă vezi 0, există încă o problemă de mapare'
\echo ''
