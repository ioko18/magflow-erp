-- 03-views.sql
-- This script creates views for common queries

-- View for inventory summary
CREATE OR REPLACE VIEW inventory_summary AS
SELECT
    p.id as product_id,
    p.sku,
    p.name as product_name,
    p.price,
    p.cost_price,
    p.status as product_status,
    c.name as category_name,
    COALESCE(SUM(ii.quantity), 0) as total_quantity,
    COALESCE(SUM(ii.available_quantity), 0) as available_quantity,
    COALESCE(SUM(ii.quantity * p.cost_price), 0) as total_cost_value,
    COALESCE(SUM(ii.available_quantity * p.price), 0) as total_retail_value,
    ARRAY_AGG(DISTINCT w.name) as warehouse_names
FROM products p
LEFT JOIN categories c ON p.category_id = c.id
LEFT JOIN inventory_items ii ON p.id = ii.product_id
LEFT JOIN warehouses w ON ii.warehouse_id = w.id
WHERE p.deleted_at IS NULL
  AND (w.id IS NULL OR w.is_active = true)
GROUP BY p.id, p.sku, p.name, p.price, p.cost_price, p.status, c.name;

-- View for user activity
CREATE OR REPLACE VIEW user_activity AS
SELECT
    u.id as user_id,
    u.email,
    u.first_name,
    u.last_name,
    u.role,
    u.last_login_at,
    COUNT(DISTINCT al.id) as total_actions,
    MAX(al.created_at) as last_action_at,
    COUNT(DISTINCT DATE(al.created_at)) as active_days
FROM users u
LEFT JOIN audit_logs al ON u.id = al.user_id
WHERE u.deleted_at IS NULL
GROUP BY u.id, u.email, u.first_name, u.last_name, u.role, u.last_login_at;

-- View for product performance
CREATE OR REPLACE VIEW product_performance AS
SELECT
    p.id as product_id,
    p.sku,
    p.name as product_name,
    p.price,
    p.cost_price,
    c.name as category_name,
    COALESCE(SUM(oi.quantity), 0) as total_quantity_sold,
    COALESCE(SUM(oi.quantity * oi.unit_price), 0) as total_revenue,
    COALESCE(SUM(oi.quantity * p.cost_price), 0) as total_cost,
    COALESCE(SUM(oi.quantity * oi.unit_price) - SUM(oi.quantity * p.cost_price), 0) as total_profit
FROM products p
LEFT JOIN categories c ON p.category_id = c.id
LEFT JOIN order_items oi ON p.id = oi.product_id
LEFT JOIN orders o ON oi.order_id = o.id
WHERE p.deleted_at IS NULL
  AND o.status = 'completed'
GROUP BY p.id, p.sku, p.name, p.price, p.cost_price, c.name;
