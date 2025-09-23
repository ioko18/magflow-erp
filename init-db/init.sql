-- Initialize MagFlow ERP Database

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create custom functions for audit logging
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create custom function for soft delete
CREATE OR REPLACE FUNCTION soft_delete_trigger()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL THEN
        NEW.updated_at = CURRENT_TIMESTAMP;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create indexes for performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_created_at ON users(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_name ON products(name);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_category_id ON products(category_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_items_warehouse ON inventory_items(warehouse_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_items_product ON inventory_items(product_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sales_orders_customer ON sales_orders(customer_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sales_orders_status ON sales_orders(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_purchase_orders_supplier ON purchase_orders(supplier_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_purchase_orders_status ON purchase_orders(status);

-- Create views for common queries
CREATE OR REPLACE VIEW inventory_summary AS
SELECT
    w.id as warehouse_id,
    w.name as warehouse_name,
    COUNT(i.id) as total_items,
    SUM(i.quantity * COALESCE(i.unit_cost, 0)) as total_value,
    COUNT(CASE WHEN i.available_quantity <= i.minimum_stock THEN 1 END) as low_stock_items,
    COUNT(CASE WHEN i.available_quantity <= 0 THEN 1 END) as out_of_stock_items
FROM warehouses w
LEFT JOIN inventory_items i ON w.id = i.warehouse_id AND i.is_active = true
WHERE w.is_active = true
GROUP BY w.id, w.name;

CREATE OR REPLACE VIEW sales_summary AS
SELECT
    c.id as customer_id,
    c.name as customer_name,
    COUNT(so.id) as total_orders,
    SUM(so.total_amount) as total_revenue,
    AVG(so.total_amount) as average_order_value,
    MAX(so.created_at) as last_order_date
FROM customers c
LEFT JOIN sales_orders so ON c.id = so.customer_id
WHERE c.is_active = true
GROUP BY c.id, c.name;

CREATE OR REPLACE VIEW purchase_summary AS
SELECT
    s.id as supplier_id,
    s.name as supplier_name,
    COUNT(po.id) as total_orders,
    SUM(po.total_amount) as total_spent,
    AVG(po.total_amount) as average_order_value,
    COUNT(CASE WHEN po.status = 'confirmed' THEN 1 END) as confirmed_orders
FROM suppliers s
LEFT JOIN purchase_orders po ON s.id = po.supplier_id
WHERE s.is_active = true
GROUP BY s.id, s.name;

-- Insert default data
INSERT INTO roles (name, description, is_active, created_at, updated_at)
VALUES
    ('admin', 'System administrator with full access', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('manager', 'Manager with access to most features', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('user', 'Regular user with basic access', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('viewer', 'Read-only user', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (name) DO NOTHING;

-- Insert default permissions
INSERT INTO permissions (name, description, created_at, updated_at)
VALUES
    ('user:read', 'Read user data', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('user:create', 'Create users', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('user:update', 'Update user data', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('user:delete', 'Delete users', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('product:read', 'Read product data', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('product:create', 'Create products', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('product:update', 'Update product data', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('product:delete', 'Delete products', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('inventory:read', 'Read inventory data', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('inventory:update', 'Update inventory data', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('inventory:manage', 'Manage inventory operations', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('sales:read', 'Read sales data', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('sales:create', 'Create sales orders', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('sales:update', 'Update sales data', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('sales:manage', 'Manage sales operations', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('purchase:read', 'Read purchase data', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('purchase:create', 'Create purchase orders', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('purchase:update', 'Update purchase data', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('purchase:manage', 'Manage purchase operations', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('system:read', 'Read system data', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('system:update', 'Update system configuration', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('system:manage', 'Manage system operations', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (name) DO NOTHING;

-- Assign permissions to roles
INSERT INTO role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'admin'
ON CONFLICT DO NOTHING;

INSERT INTO role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name = 'manager'
  AND p.name IN (
      'user:read', 'user:create', 'user:update',
      'product:read', 'product:create', 'product:update', 'product:delete',
      'inventory:read', 'inventory:update', 'inventory:manage',
      'sales:read', 'sales:create', 'sales:update', 'sales:manage',
      'purchase:read', 'purchase:create', 'purchase:update', 'purchase:manage',
      'system:read'
  )
ON CONFLICT DO NOTHING;

INSERT INTO role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name = 'user'
  AND p.name IN (
      'product:read',
      'inventory:read',
      'sales:read',
      'purchase:read'
  )
ON CONFLICT DO NOTHING;

INSERT INTO role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name = 'viewer'
  AND p.name IN (
      'product:read',
      'inventory:read'
  )
ON CONFLICT DO NOTHING;

-- Insert default warehouses
INSERT INTO warehouses (name, code, is_active, created_at, updated_at)
VALUES
    ('Main Warehouse', 'WH001', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('Secondary Warehouse', 'WH002', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (code) DO NOTHING;

-- Insert sample data for testing
INSERT INTO categories (name, description, is_active, created_at, updated_at)
VALUES
    ('Electronics', 'Electronic products', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('Clothing', 'Clothing and apparel', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (name) DO NOTHING;

-- Insert sample products
INSERT INTO products (name, description, category_id, price, is_active, created_at, updated_at)
SELECT
    'Sample Product ' || generate_series,
    'Sample product for testing ' || generate_series,
    CASE WHEN generate_series % 2 = 1 THEN 1 ELSE 2 END,
    (random() * 100 + 10)::numeric(10,2),
    true,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
FROM generate_series(1, 10)
ON CONFLICT DO NOTHING;

COMMIT;
