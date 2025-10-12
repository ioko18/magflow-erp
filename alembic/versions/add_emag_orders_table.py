"""Add eMAG orders table

Revision ID: add_emag_orders_v2
Revises: 069bd2ae6d01
Create Date: 2025-09-30 11:40:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = 'add_emag_orders_v2'
down_revision = '4242d9721c62'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create emag_orders table in app schema."""

    # Check if table already exists (idempotent - handles parallel branch merge)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'emag_orders' in inspector.get_table_names(schema='app'):
        print("⚠️  Table emag_orders already exists, skipping creation")
        return

    # Create emag_orders table
    op.create_table(
        'emag_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('emag_order_id', sa.Integer(), nullable=False),
        sa.Column('account_type', sa.String(length=10), nullable=False),
        sa.Column('status', sa.Integer(), nullable=False),
        sa.Column('status_name', sa.String(length=50), nullable=True),
        sa.Column('type', sa.Integer(), nullable=True),
        sa.Column('is_complete', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('customer_name', sa.String(length=200), nullable=True),
        sa.Column('customer_email', sa.String(length=200), nullable=True),
        sa.Column('customer_phone', sa.String(length=50), nullable=True),
        sa.Column('total_amount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='RON'),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('payment_mode_id', sa.Integer(), nullable=True),
        sa.Column('detailed_payment_method', sa.String(length=100), nullable=True),
        sa.Column('payment_status', sa.Integer(), nullable=True),
        sa.Column('cashed_co', sa.Float(), nullable=True),
        sa.Column('cashed_cod', sa.Float(), nullable=True),
        sa.Column('delivery_mode', sa.String(length=50), nullable=True),
        sa.Column('shipping_tax', sa.Float(), nullable=True),
        sa.Column('shipping_tax_voucher_split', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('shipping_address', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('billing_address', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('locker_id', sa.String(length=50), nullable=True),
        sa.Column('locker_name', sa.String(length=200), nullable=True),
        sa.Column('awb_number', sa.String(length=100), nullable=True),
        sa.Column('courier_name', sa.String(length=100), nullable=True),
        sa.Column('invoice_url', sa.Text(), nullable=True),
        sa.Column('invoice_uploaded_at', sa.DateTime(), nullable=True),
        sa.Column('products', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('vouchers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('attachments', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_storno', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('finalized_at', sa.DateTime(), nullable=True),
        sa.Column('sync_status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('sync_error', sa.Text(), nullable=True),
        sa.Column('sync_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('order_date', sa.DateTime(), nullable=True),
        sa.Column('emag_created_at', sa.DateTime(), nullable=True),
        sa.Column('emag_modified_at', sa.DateTime(), nullable=True),
        sa.Column('raw_emag_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("account_type IN ('main', 'fbe')", name='ck_emag_orders_account_type'),
        sa.CheckConstraint('status IN (0,1,2,3,4,5)', name='ck_emag_orders_status'),
        sa.CheckConstraint('type IN (2,3)', name='ck_emag_orders_type'),
        sa.UniqueConstraint('emag_order_id', 'account_type', name='uq_emag_orders_id_account'),
        schema='app'
    )

    # Create indexes
    op.create_index(
        'idx_emag_orders_emag_id_account',
        'emag_orders',
        ['emag_order_id', 'account_type'],
        schema='app'
    )
    op.create_index(
        'idx_emag_orders_account',
        'emag_orders',
        ['account_type'],
        schema='app'
    )
    op.create_index(
        'idx_emag_orders_status',
        'emag_orders',
        ['status'],
        schema='app'
    )
    op.create_index(
        'idx_emag_orders_sync_status',
        'emag_orders',
        ['sync_status'],
        schema='app'
    )
    op.create_index(
        'idx_emag_orders_order_date',
        'emag_orders',
        ['order_date'],
        schema='app'
    )
    op.create_index(
        'idx_emag_orders_customer_email',
        'emag_orders',
        ['customer_email'],
        schema='app'
    )


def downgrade() -> None:
    """Drop emag_orders table."""
    # Idempotent downgrade
    conn = op.get_bind()
    conn.execute(sa.text('DROP INDEX IF EXISTS app.idx_emag_orders_customer_email'))
    conn.execute(sa.text('DROP INDEX IF EXISTS app.idx_emag_orders_order_date'))
    conn.execute(sa.text('DROP INDEX IF EXISTS app.idx_emag_orders_sync_status'))
    conn.execute(sa.text('DROP INDEX IF EXISTS app.idx_emag_orders_status'))
    conn.execute(sa.text('DROP INDEX IF EXISTS app.idx_emag_orders_account'))
    conn.execute(sa.text('DROP INDEX IF EXISTS app.idx_emag_orders_emag_id_account'))
    conn.execute(sa.text('DROP TABLE IF EXISTS app.emag_orders CASCADE'))
