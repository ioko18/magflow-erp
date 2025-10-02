-- ============================================
-- CLEANUP SCRIPT: Reset Matching Groups
-- ============================================
-- Folosește acest script când ai șters produse și vrei să resetezi grupurile

-- 1. Verifică câte grupuri active există
SELECT 
    COUNT(*) as total_groups,
    COUNT(CASE WHEN is_active = true THEN 1 END) as active_groups,
    COUNT(CASE WHEN is_active = false THEN 1 END) as inactive_groups
FROM app.product_matching_groups;

-- 2. Verifică câte produse active există
SELECT 
    COUNT(*) as total_products,
    COUNT(CASE WHEN is_active = true THEN 1 END) as active_products,
    COUNT(CASE WHEN is_active = false THEN 1 END) as inactive_products
FROM app.supplier_raw_products;

-- 3. OPȚIUNE A: Soft delete pentru grupuri fără produse active
-- (Recomandată - păstrează istoricul)
UPDATE app.product_matching_groups
SET is_active = false
WHERE id IN (
    SELECT pmg.id
    FROM app.product_matching_groups pmg
    LEFT JOIN app.supplier_raw_products srp 
        ON srp.product_group_id = pmg.id 
        AND srp.is_active = true
    WHERE pmg.is_active = true
    GROUP BY pmg.id
    HAVING COUNT(srp.id) = 0
);

-- 4. OPȚIUNE B: Hard delete - ATENȚIE! Șterge permanent!
-- (Folosește doar dacă vrei să resetezi complet)
-- UNCOMMENT DOAR DACĂ EȘTI SIGUR:

-- DELETE FROM app.product_matching_groups
-- WHERE id IN (
--     SELECT pmg.id
--     FROM app.product_matching_groups pmg
--     LEFT JOIN app.supplier_raw_products srp 
--         ON srp.product_group_id = pmg.id 
--         AND srp.is_active = true
--     GROUP BY pmg.id
--     HAVING COUNT(srp.id) = 0
-- );

-- 5. OPȚIUNE C: Reset complet - ATENȚIE! Șterge TOT!
-- (Folosește doar pentru development/testing)
-- UNCOMMENT DOAR DACĂ VREI SĂ RESETEZI COMPLET:

-- -- Șterge toate grupurile
-- DELETE FROM app.product_matching_groups;
-- 
-- -- Resetează product_group_id pentru toate produsele
-- UPDATE app.supplier_raw_products 
-- SET product_group_id = NULL, 
--     matching_status = 'pending';
-- 
-- -- Resetează sequence-urile (pentru ID-uri clean)
-- ALTER SEQUENCE app.product_matching_groups_id_seq RESTART WITH 1;

-- 6. Verificare finală
SELECT 
    'Groups' as table_name,
    COUNT(*) as total,
    COUNT(CASE WHEN is_active = true THEN 1 END) as active
FROM app.product_matching_groups
UNION ALL
SELECT 
    'Products' as table_name,
    COUNT(*) as total,
    COUNT(CASE WHEN is_active = true THEN 1 END) as active
FROM app.supplier_raw_products;

-- 7. Verifică grupuri cu număr de produse
SELECT 
    pmg.id,
    pmg.group_name,
    pmg.product_count as recorded_count,
    COUNT(srp.id) as actual_active_count,
    pmg.is_active as group_active
FROM app.product_matching_groups pmg
LEFT JOIN app.supplier_raw_products srp 
    ON srp.product_group_id = pmg.id 
    AND srp.is_active = true
WHERE pmg.is_active = true
GROUP BY pmg.id, pmg.group_name, pmg.product_count, pmg.is_active
ORDER BY pmg.id
LIMIT 20;
