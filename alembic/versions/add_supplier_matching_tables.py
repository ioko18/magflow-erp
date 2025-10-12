"""Add supplier matching tables for 1688.com product comparison

Revision ID: supplier_matching_001
Revises: c8e960008812
Create Date: 2025-10-01 00:56:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = 'supplier_matching_001'
down_revision = 'c8e960008812'  # Links to add_shipping_tax_voucher_split_to_orders
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create supplier matching tables."""

    # Create product_matching_groups table FIRST (to avoid FK constraint issues)
    op.create_table(
        'product_matching_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_name', sa.String(length=500), nullable=False),
        sa.Column('group_name_en', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('representative_image_url', sa.String(length=2000), nullable=True),
        sa.Column('representative_image_hash', sa.String(length=64), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('matching_method', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='auto_matched'),
        sa.Column('verified_by', sa.Integer(), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('min_price_cny', sa.Float(), nullable=True),
        sa.Column('max_price_cny', sa.Float(), nullable=True),
        sa.Column('avg_price_cny', sa.Float(), nullable=True),
        sa.Column('best_supplier_id', sa.Integer(), nullable=True),
        sa.Column('product_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('local_product_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['local_product_id'], ['app.products.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='app'
    )

    # Create indexes for product_matching_groups
    op.create_index('idx_group_status', 'product_matching_groups', ['status'], schema='app')
    op.create_index('idx_group_confidence', 'product_matching_groups', ['confidence_score'], schema='app')
    op.create_index('idx_group_active', 'product_matching_groups', ['is_active'], schema='app')

    # Create supplier_raw_products table (after product_matching_groups)
    op.create_table(
        'supplier_raw_products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=False),
        sa.Column('chinese_name', sa.String(length=1000), nullable=False),
        sa.Column('price_cny', sa.Float(), nullable=False),
        sa.Column('product_url', sa.String(length=2000), nullable=False),
        sa.Column('image_url', sa.String(length=2000), nullable=False),
        sa.Column('english_name', sa.String(length=1000), nullable=True),
        sa.Column('normalized_name', sa.String(length=1000), nullable=True),
        sa.Column('image_hash', sa.String(length=64), nullable=True),
        sa.Column('image_features', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('image_downloaded', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('image_local_path', sa.String(length=500), nullable=True),
        sa.Column('matching_status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('product_group_id', sa.Integer(), nullable=True),
        sa.Column('import_batch_id', sa.String(length=50), nullable=True),
        sa.Column('import_date', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_price_check', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('specifications', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('supplier_sku', sa.String(length=100), nullable=True),
        sa.Column('moq', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['supplier_id'], ['app.suppliers.id'], ),
        sa.ForeignKeyConstraint(['product_group_id'], ['app.product_matching_groups.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='app'
    )

    # Create indexes for supplier_raw_products
    op.create_index('idx_supplier_raw_name', 'supplier_raw_products', ['chinese_name'], schema='app')
    op.create_index('idx_supplier_raw_supplier', 'supplier_raw_products', ['supplier_id'], schema='app')
    op.create_index('idx_supplier_raw_status', 'supplier_raw_products', ['matching_status'], schema='app')
    op.create_index('idx_supplier_raw_active', 'supplier_raw_products', ['is_active'], schema='app')
    op.create_index('idx_supplier_raw_batch', 'supplier_raw_products', ['import_batch_id'], schema='app')
    op.create_index('idx_supplier_raw_group', 'supplier_raw_products', ['product_group_id'], schema='app')

    # Create product_matching_scores table
    op.create_table(
        'product_matching_scores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_a_id', sa.Integer(), nullable=False),
        sa.Column('product_b_id', sa.Integer(), nullable=False),
        sa.Column('text_similarity', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('image_similarity', sa.Float(), nullable=True),
        sa.Column('price_similarity', sa.Float(), nullable=True),
        sa.Column('total_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('matching_algorithm', sa.String(length=50), nullable=False),
        sa.Column('matching_features', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_match', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('threshold_used', sa.Float(), nullable=False, server_default='0.7'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['product_a_id'], ['app.supplier_raw_products.id'], ),
        sa.ForeignKeyConstraint(['product_b_id'], ['app.supplier_raw_products.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_a_id', 'product_b_id', name='uq_product_pair'),
        schema='app'
    )

    # Create indexes for product_matching_scores
    op.create_index('idx_matching_products', 'product_matching_scores', ['product_a_id', 'product_b_id'], schema='app')
    op.create_index('idx_matching_score', 'product_matching_scores', ['total_score'], schema='app')

    # Create supplier_price_history table
    op.create_table(
        'supplier_price_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('raw_product_id', sa.Integer(), nullable=False),
        sa.Column('price_cny', sa.Float(), nullable=False),
        sa.Column('price_change', sa.Float(), nullable=True),
        sa.Column('price_change_percent', sa.Float(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='scraping'),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['raw_product_id'], ['app.supplier_raw_products.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='app'
    )

    # Create indexes for supplier_price_history
    op.create_index('idx_price_history_product', 'supplier_price_history', ['raw_product_id'], schema='app')
    op.create_index('idx_price_history_date', 'supplier_price_history', ['recorded_at'], schema='app')


def downgrade() -> None:
    """Drop supplier matching tables."""

    # Drop tables in reverse order
    op.drop_table('supplier_price_history', schema='app')
    op.drop_table('product_matching_scores', schema='app')
    op.drop_table('product_matching_groups', schema='app')
    op.drop_table('supplier_raw_products', schema='app')
