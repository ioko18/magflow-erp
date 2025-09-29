"""Add enhanced eMAG integration models

Revision ID: 20250929_add_enhanced_emag_models
Revises: 20250928_add_external_id_to_orders
Create Date: 2025-09-29 16:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250929_add_enhanced_emag_models'
down_revision = '20250928_add_external_id'
branch_labels = None
depends_on = None


def upgrade():
    """Create enhanced eMAG integration tables."""
    
    # Create emag_products table
    op.create_table('emag_products',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('emag_id', sa.String(length=50), nullable=True),
        sa.Column('sku', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('account_type', sa.String(length=10), nullable=False),
        sa.Column('source_account', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('brand', sa.String(length=200), nullable=True),
        sa.Column('manufacturer', sa.String(length=200), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('stock_quantity', sa.Integer(), nullable=True),
        sa.Column('category_id', sa.String(length=50), nullable=True),
        sa.Column('emag_category_id', sa.String(length=50), nullable=True),
        sa.Column('emag_category_name', sa.String(length=200), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('images', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('images_overwrite', sa.Boolean(), nullable=False),
        sa.Column('green_tax', sa.Float(), nullable=True),
        sa.Column('supply_lead_time', sa.Integer(), nullable=True),
        sa.Column('safety_information', sa.Text(), nullable=True),
        sa.Column('manufacturer_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('eu_representative', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('emag_characteristics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('specifications', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('sync_status', sa.String(length=50), nullable=False),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('sync_error', sa.Text(), nullable=True),
        sa.Column('sync_attempts', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('emag_created_at', sa.DateTime(), nullable=True),
        sa.Column('emag_modified_at', sa.DateTime(), nullable=True),
        sa.Column('raw_emag_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint("account_type IN ('main', 'fbe')", name='ck_emag_products_account_type'),
        sa.CheckConstraint("currency IN ('RON', 'EUR', 'USD')", name='ck_emag_products_currency'),
        sa.CheckConstraint('supply_lead_time IN (2,3,5,7,14,30,60,90,120)', name='ck_emag_products_lead_time'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sku', 'account_type', name='uq_emag_products_sku_account')
    )
    
    # Create indexes for emag_products
    op.create_index('idx_emag_products_sku_account', 'emag_products', ['sku', 'account_type'])
    op.create_index('idx_emag_products_emag_id', 'emag_products', ['emag_id'])
    op.create_index('idx_emag_products_sync_status', 'emag_products', ['sync_status'])
    op.create_index('idx_emag_products_last_synced', 'emag_products', ['last_synced_at'])
    op.create_index('idx_emag_products_category', 'emag_products', ['emag_category_id'])
    
    # Create emag_product_offers table
    op.create_table('emag_product_offers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('emag_offer_id', sa.String(length=50), nullable=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=False),
        sa.Column('account_type', sa.String(length=10), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('original_price', sa.Float(), nullable=True),
        sa.Column('sale_price', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('stock', sa.Integer(), nullable=False),
        sa.Column('reserved_stock', sa.Integer(), nullable=False),
        sa.Column('available_stock', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('is_available', sa.Boolean(), nullable=False),
        sa.Column('handling_time', sa.Integer(), nullable=True),
        sa.Column('shipping_weight', sa.Float(), nullable=True),
        sa.Column('shipping_size', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('marketplace_status', sa.String(length=50), nullable=True),
        sa.Column('visibility', sa.String(length=50), nullable=False),
        sa.Column('sync_status', sa.String(length=50), nullable=False),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('sync_error', sa.Text(), nullable=True),
        sa.Column('sync_attempts', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('emag_created_at', sa.DateTime(), nullable=True),
        sa.Column('emag_modified_at', sa.DateTime(), nullable=True),
        sa.Column('raw_emag_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint("account_type IN ('main', 'fbe')", name='ck_emag_offers_account_type'),
        sa.CheckConstraint("currency IN ('RON', 'EUR', 'USD')", name='ck_emag_offers_currency'),
        sa.CheckConstraint('stock >= 0', name='ck_emag_offers_stock_positive'),
        sa.ForeignKeyConstraint(['product_id'], ['emag_products.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sku', 'account_type', name='uq_emag_offers_sku_account')
    )
    
    # Create indexes for emag_product_offers
    op.create_index('idx_emag_offers_sku_account', 'emag_product_offers', ['sku', 'account_type'])
    op.create_index('idx_emag_offers_emag_id', 'emag_product_offers', ['emag_offer_id'])
    op.create_index('idx_emag_offers_sync_status', 'emag_product_offers', ['sync_status'])
    op.create_index('idx_emag_offers_status', 'emag_product_offers', ['status'])
    op.create_index('idx_emag_offers_last_synced', 'emag_product_offers', ['last_synced_at'])
    
    # Create emag_orders table
    op.create_table('emag_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('emag_order_id', sa.String(length=50), nullable=False),
        sa.Column('account_type', sa.String(length=10), nullable=False),
        sa.Column('status', sa.Integer(), nullable=False),
        sa.Column('type', sa.Integer(), nullable=True),
        sa.Column('is_complete', sa.Boolean(), nullable=False),
        sa.Column('customer_name', sa.String(length=200), nullable=True),
        sa.Column('customer_email', sa.String(length=200), nullable=True),
        sa.Column('customer_phone', sa.String(length=50), nullable=True),
        sa.Column('total_amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('payment_mode_id', sa.Integer(), nullable=False),
        sa.Column('detailed_payment_method', sa.String(length=100), nullable=True),
        sa.Column('payment_status', sa.Integer(), nullable=True),
        sa.Column('cashed_co', sa.Float(), nullable=True),
        sa.Column('cashed_cod', sa.Float(), nullable=True),
        sa.Column('delivery_mode', sa.String(length=50), nullable=True),
        sa.Column('shipping_tax', sa.Float(), nullable=True),
        sa.Column('shipping_address', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('billing_address', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('locker_id', sa.String(length=50), nullable=True),
        sa.Column('locker_name', sa.String(length=200), nullable=True),
        sa.Column('products', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('vouchers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('attachments', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_storno', sa.Boolean(), nullable=False),
        sa.Column('sync_status', sa.String(length=50), nullable=False),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('sync_error', sa.Text(), nullable=True),
        sa.Column('sync_attempts', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('order_date', sa.DateTime(), nullable=True),
        sa.Column('emag_created_at', sa.DateTime(), nullable=True),
        sa.Column('emag_modified_at', sa.DateTime(), nullable=True),
        sa.Column('raw_emag_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint("account_type IN ('main', 'fbe')", name='ck_emag_orders_account_type'),
        sa.CheckConstraint('status IN (0,1,2,3,4,5)', name='ck_emag_orders_status'),
        sa.CheckConstraint('type IN (2,3)', name='ck_emag_orders_type'),
        sa.CheckConstraint('payment_mode_id IN (1,2,3)', name='ck_emag_orders_payment_mode'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('emag_order_id', name='emag_orders_emag_order_id_key')
    )
    
    # Create indexes for emag_orders
    op.create_index('idx_emag_orders_emag_id', 'emag_orders', ['emag_order_id'])
    op.create_index('idx_emag_orders_account', 'emag_orders', ['account_type'])
    op.create_index('idx_emag_orders_status', 'emag_orders', ['status'])
    op.create_index('idx_emag_orders_sync_status', 'emag_orders', ['sync_status'])
    op.create_index('idx_emag_orders_order_date', 'emag_orders', ['order_date'])
    op.create_index('idx_emag_orders_customer_email', 'emag_orders', ['customer_email'])
    
    # Create emag_sync_logs table
    op.create_table('emag_sync_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sync_type', sa.String(length=50), nullable=False),
        sa.Column('account_type', sa.String(length=10), nullable=False),
        sa.Column('operation', sa.String(length=50), nullable=False),
        sa.Column('sync_params', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('total_items', sa.Integer(), nullable=False),
        sa.Column('processed_items', sa.Integer(), nullable=False),
        sa.Column('created_items', sa.Integer(), nullable=False),
        sa.Column('updated_items', sa.Integer(), nullable=False),
        sa.Column('failed_items', sa.Integer(), nullable=False),
        sa.Column('errors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('warnings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('pages_processed', sa.Integer(), nullable=False),
        sa.Column('api_requests_made', sa.Integer(), nullable=False),
        sa.Column('rate_limit_hits', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('triggered_by', sa.String(length=100), nullable=True),
        sa.Column('sync_version', sa.String(length=20), nullable=True),
        sa.CheckConstraint("account_type IN ('main', 'fbe')", name='ck_emag_sync_logs_account_type'),
        sa.CheckConstraint("sync_type IN ('products', 'offers', 'orders')", name='ck_emag_sync_logs_sync_type'),
        sa.CheckConstraint("status IN ('running', 'completed', 'failed', 'partial')", name='ck_emag_sync_logs_status'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for emag_sync_logs
    op.create_index('idx_emag_sync_logs_type_account', 'emag_sync_logs', ['sync_type', 'account_type'])
    op.create_index('idx_emag_sync_logs_status', 'emag_sync_logs', ['status'])
    op.create_index('idx_emag_sync_logs_started_at', 'emag_sync_logs', ['started_at'])
    
    # Create emag_sync_progress table
    op.create_table('emag_sync_progress',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sync_log_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('current_page', sa.Integer(), nullable=False),
        sa.Column('total_pages', sa.Integer(), nullable=True),
        sa.Column('current_item', sa.Integer(), nullable=False),
        sa.Column('total_items', sa.Integer(), nullable=True),
        sa.Column('percentage_complete', sa.Float(), nullable=False),
        sa.Column('current_operation', sa.String(length=200), nullable=True),
        sa.Column('current_sku', sa.String(length=100), nullable=True),
        sa.Column('items_per_second', sa.Float(), nullable=True),
        sa.Column('estimated_completion', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('percentage_complete >= 0 AND percentage_complete <= 100', name='ck_emag_sync_progress_percentage'),
        sa.ForeignKeyConstraint(['sync_log_id'], ['emag_sync_logs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for emag_sync_progress
    op.create_index('idx_emag_sync_progress_log_id', 'emag_sync_progress', ['sync_log_id'])
    op.create_index('idx_emag_sync_progress_active', 'emag_sync_progress', ['is_active'])
    
    # Set default values for existing columns
    op.execute("UPDATE emag_products SET account_type = 'main' WHERE account_type IS NULL")
    op.execute("UPDATE emag_products SET currency = 'RON' WHERE currency IS NULL")
    op.execute("UPDATE emag_products SET is_active = true WHERE is_active IS NULL")
    op.execute("UPDATE emag_products SET images_overwrite = false WHERE images_overwrite IS NULL")
    op.execute("UPDATE emag_products SET sync_status = 'pending' WHERE sync_status IS NULL")
    op.execute("UPDATE emag_products SET sync_attempts = 0 WHERE sync_attempts IS NULL")


def downgrade():
    """Drop enhanced eMAG integration tables."""
    
    # Drop tables in reverse order due to foreign key constraints
    op.drop_table('emag_sync_progress')
    op.drop_table('emag_sync_logs')
    op.drop_table('emag_orders')
    op.drop_table('emag_product_offers')
    op.drop_table('emag_products')
