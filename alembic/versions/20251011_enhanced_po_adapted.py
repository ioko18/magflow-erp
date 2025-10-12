"""Add enhanced purchase order fields adapted to existing schema

Revision ID: 20251011_enhanced_po_adapted
Revises: 9c505c31bcc1
Create Date: 2025-10-11 21:45:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = '20251011_enhanced_po_adapted'
down_revision = '97aa49837ac6'  # Current head in database
branch_labels = None
depends_on = None


def upgrade():
    """Add only NEW columns and tables to existing purchase orders schema."""

    # Add NEW columns to existing purchase_orders table (only if they don't exist)
    # Note: actual_delivery_date already exists in the table
    conn = op.get_bind()

    # Check and add columns only if they don't exist
    inspector = sa.inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('purchase_orders', schema='app')]

    if 'delivery_address' not in existing_columns:
        op.add_column('purchase_orders',
            sa.Column('delivery_address', sa.Text(), nullable=True),
            schema='app'
        )

    if 'tracking_number' not in existing_columns:
        op.add_column('purchase_orders',
            sa.Column('tracking_number', sa.String(100), nullable=True),
            schema='app'
        )

    if 'cancelled_at' not in existing_columns:
        op.add_column('purchase_orders',
            sa.Column('cancelled_at', sa.DateTime(), nullable=True),
            schema='app'
        )

    if 'cancelled_by' not in existing_columns:
        op.add_column('purchase_orders',
            sa.Column('cancelled_by', sa.Integer(), nullable=True),
            schema='app'
        )

    if 'cancellation_reason' not in existing_columns:
        op.add_column('purchase_orders',
            sa.Column('cancellation_reason', sa.Text(), nullable=True),
            schema='app'
        )

    # Create NEW table: purchase_order_unreceived_items
    op.create_table(
        'purchase_order_unreceived_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('purchase_order_id', sa.Integer(), nullable=False),
        sa.Column('purchase_order_item_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('ordered_quantity', sa.Integer(), nullable=False),
        sa.Column('received_quantity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('unreceived_quantity', sa.Integer(), nullable=False),
        sa.Column('expected_date', sa.DateTime(), nullable=True),
        sa.Column('follow_up_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['purchase_order_id'], ['app.purchase_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['purchase_order_item_id'], ['app.purchase_order_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['app.products.id'], ondelete='CASCADE'),
        schema='app'
    )

    # Create indexes for unreceived_items
    op.create_index(
        'ix_purchase_order_unreceived_items_po_id',
        'purchase_order_unreceived_items',
        ['purchase_order_id'],
        schema='app'
    )
    op.create_index(
        'ix_purchase_order_unreceived_items_product_id',
        'purchase_order_unreceived_items',
        ['product_id'],
        schema='app'
    )
    op.create_index(
        'ix_purchase_order_unreceived_items_status',
        'purchase_order_unreceived_items',
        ['status'],
        schema='app'
    )

    # Create NEW table: purchase_order_history
    op.create_table(
        'purchase_order_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('purchase_order_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('old_status', sa.String(20), nullable=True),
        sa.Column('new_status', sa.String(20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('changed_by', sa.Integer(), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('extra_data', postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['purchase_order_id'], ['app.purchase_orders.id'], ondelete='CASCADE'),
        schema='app'
    )

    # Create indexes for history
    op.create_index(
        'ix_purchase_order_history_po_id',
        'purchase_order_history',
        ['purchase_order_id'],
        schema='app'
    )
    op.create_index(
        'ix_purchase_order_history_action',
        'purchase_order_history',
        ['action'],
        schema='app'
    )


def downgrade():
    """Remove enhanced purchase order features."""

    # Drop indexes
    op.drop_index('ix_purchase_order_history_action', table_name='purchase_order_history', schema='app')
    op.drop_index('ix_purchase_order_history_po_id', table_name='purchase_order_history', schema='app')
    op.drop_index('ix_purchase_order_unreceived_items_status', table_name='purchase_order_unreceived_items', schema='app')
    op.drop_index('ix_purchase_order_unreceived_items_product_id', table_name='purchase_order_unreceived_items', schema='app')
    op.drop_index('ix_purchase_order_unreceived_items_po_id', table_name='purchase_order_unreceived_items', schema='app')

    # Drop tables
    op.drop_table('purchase_order_history', schema='app')
    op.drop_table('purchase_order_unreceived_items', schema='app')

    # Drop columns (only if they were added)
    op.drop_column('purchase_orders', 'cancellation_reason', schema='app')
    op.drop_column('purchase_orders', 'cancelled_by', schema='app')
    op.drop_column('purchase_orders', 'cancelled_at', schema='app')
    op.drop_column('purchase_orders', 'tracking_number', schema='app')
    op.drop_column('purchase_orders', 'delivery_address', schema='app')
