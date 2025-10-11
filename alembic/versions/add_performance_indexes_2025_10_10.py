"""Add performance indexes for dashboard and common queries

Revision ID: perf_idx_20251010
Revises: bd898485abe9
Create Date: 2025-10-10 05:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'perf_idx_20251010'
down_revision = 'bd898485abe9'  # Latest migration
branch_labels = None
depends_on = None


def upgrade():
    """Add performance indexes for frequently queried fields."""
    
    # Sales Orders indexes for dashboard queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_sales_orders_order_date 
        ON app.sales_orders(order_date DESC);
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_sales_orders_customer_id 
        ON app.sales_orders(customer_id) 
        WHERE customer_id IS NOT NULL;
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_sales_orders_status 
        ON app.sales_orders(status);
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_sales_orders_date_status 
        ON app.sales_orders(order_date DESC, status);
    """)
    
    # eMAG Products indexes
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_emag_products_v2_updated_at 
        ON app.emag_products_v2(updated_at DESC);
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_emag_products_v2_active 
        ON app.emag_products_v2(is_active) 
        WHERE is_active = true;
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_emag_products_v2_account 
        ON app.emag_products_v2(account_type);
    """)
    
    # Products indexes
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_sku 
        ON app.products(sku);
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_name 
        ON app.products(name);
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_products_created_at 
        ON app.products(created_at DESC);
    """)
    
    # Inventory indexes
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_inventory_product_id 
        ON app.inventory(product_id);
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_inventory_quantity 
        ON app.inventory(quantity);
    """)
    
    # Customers indexes (if table exists)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_customers_email 
        ON app.customers(email) 
        WHERE email IS NOT NULL;
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_customers_created_at 
        ON app.customers(created_at DESC);
    """)
    
    # Composite index for common dashboard query
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_sales_orders_dashboard 
        ON app.sales_orders(order_date DESC, status, total_amount) 
        WHERE status NOT IN ('cancelled', 'rejected');
    """)
    
    print("✅ Performance indexes created successfully!")


def downgrade():
    """Remove performance indexes."""
    
    # Sales Orders indexes
    op.execute("DROP INDEX IF EXISTS app.idx_sales_orders_order_date;")
    op.execute("DROP INDEX IF EXISTS app.idx_sales_orders_customer_id;")
    op.execute("DROP INDEX IF EXISTS app.idx_sales_orders_status;")
    op.execute("DROP INDEX IF EXISTS app.idx_sales_orders_date_status;")
    op.execute("DROP INDEX IF EXISTS app.idx_sales_orders_dashboard;")
    
    # eMAG Products indexes
    op.execute("DROP INDEX IF EXISTS app.idx_emag_products_v2_updated_at;")
    op.execute("DROP INDEX IF EXISTS app.idx_emag_products_v2_active;")
    op.execute("DROP INDEX IF EXISTS app.idx_emag_products_v2_account;")
    
    # Products indexes
    op.execute("DROP INDEX IF EXISTS app.idx_products_sku;")
    op.execute("DROP INDEX IF EXISTS app.idx_products_name;")
    op.execute("DROP INDEX IF EXISTS app.idx_products_created_at;")
    
    # Inventory indexes
    op.execute("DROP INDEX IF EXISTS app.idx_inventory_product_id;")
    op.execute("DROP INDEX IF EXISTS app.idx_inventory_quantity;")
    
    # Customers indexes
    op.execute("DROP INDEX IF EXISTS app.idx_customers_email;")
    op.execute("DROP INDEX IF EXISTS app.idx_customers_created_at;")
    
    print("✅ Performance indexes removed successfully!")
