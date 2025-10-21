"""create_emag_orders_table

Revision ID: 20251014_create_emag_orders
Revises: 20251013_fix_emag_sync_logs_account_type
Create Date: 2025-10-14 20:40:00.000000

This migration creates the emag_orders table for storing eMAG marketplace orders.
This table is CRITICAL for:
- Storing real eMAG order data
- Calculating sold quantities for inventory management
- Order history and analytics
- Reconciliation with eMAG API

The table includes:
- Order identification (emag_order_id, account_type)
- Customer information
- Financial data (total_amount, currency, payment details)
- Shipping information
- Products (JSONB field - CRITICAL for sold quantity calculation)
- Sync tracking
"""

import logging
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '20251014_create_emag_orders'
down_revision: str | Sequence[str] | None = '20251013_fix_account_type'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create emag_orders table."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names(schema='app')

    if 'emag_orders' in existing_tables:
        logger.info("Table emag_orders already exists, skipping creation")
        return

    logger.info("Creating emag_orders table...")

    op.create_table(
        'emag_orders',

        # Primary identification
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('emag_order_id', sa.BigInteger(), nullable=False, index=True,
                  comment='eMAG internal order ID'),
        sa.Column('account_type', sa.String(10), nullable=False, default='main',
                  comment='Account type: main or fbe'),

        # Order status and type
        sa.Column(
            'status',
            sa.Integer(),
            nullable=False,
            comment=(
                'Order status: 0=canceled, 1=new, 2=in_progress, 3=prepared, '
                '4=finalized, 5=returned'
            ),
        ),
        sa.Column('status_name', sa.String(50), nullable=True,
                  comment='Human-readable status name'),
        sa.Column('type', sa.Integer(), nullable=True,
                  comment='Order type: 2=FBE, 3=FBS'),
        sa.Column('is_complete', sa.Boolean(), nullable=False, default=False,
                  comment='Whether order is complete'),

        # Customer information
        sa.Column('customer_id', sa.BigInteger(), nullable=True,
                  comment='eMAG customer ID'),
        sa.Column('customer_name', sa.String(200), nullable=True),
        sa.Column('customer_email', sa.String(200), nullable=True),
        sa.Column('customer_phone', sa.String(50), nullable=True),

        # Financial information
        sa.Column('total_amount', sa.Float(), nullable=False, default=0.0,
                  comment='Total order amount'),
        sa.Column('currency', sa.String(3), nullable=False, default='RON'),

        # Payment information
        sa.Column('payment_method', sa.String(50), nullable=True,
                  comment='Payment method: COD, bank_transfer, online_card'),
        sa.Column('payment_mode_id', sa.Integer(), nullable=True,
                  comment='Payment mode ID: 1=COD, 2=bank_transfer, 3=card_online'),
        sa.Column('detailed_payment_method', sa.String(100), nullable=True),
        sa.Column('payment_status', sa.Integer(), nullable=True,
                  comment='Payment status: 0=not_paid, 1=paid'),
        sa.Column('cashed_co', sa.Float(), nullable=True,
                  comment='Card online amount'),
        sa.Column('cashed_cod', sa.Float(), nullable=True,
                  comment='COD amount'),

        # Shipping information
        sa.Column('delivery_mode', sa.String(50), nullable=True,
                  comment='Delivery mode: courier, pickup'),
        sa.Column('shipping_tax', sa.Float(), nullable=True),
        sa.Column('shipping_tax_voucher_split', postgresql.JSONB(), nullable=True,
                  comment='Voucher split for shipping'),
        sa.Column('shipping_address', postgresql.JSONB(), nullable=True,
                  comment='Shipping address details'),
        sa.Column('billing_address', postgresql.JSONB(), nullable=True,
                  comment='Billing address details'),

        # Delivery details
        sa.Column('locker_id', sa.String(50), nullable=True),
        sa.Column('locker_name', sa.String(200), nullable=True),

        # AWB and tracking
        sa.Column('awb_number', sa.String(100), nullable=True,
                  comment='AWB tracking number'),
        sa.Column('courier_name', sa.String(100), nullable=True),

        # Documents
        sa.Column('invoice_url', sa.Text(), nullable=True),
        sa.Column('invoice_uploaded_at', sa.DateTime(), nullable=True),

        # Order items and vouchers - CRITICAL FOR SOLD QUANTITY CALCULATION
        sa.Column(
            'products',
            postgresql.JSONB(),
            nullable=True,
            comment=(
                'CRITICAL: Order line items with SKU and quantity for '
                'sold quantity calculation'
            ),
        ),
        sa.Column('vouchers', postgresql.JSONB(), nullable=True,
                  comment='Applied vouchers'),
        sa.Column('attachments', postgresql.JSONB(), nullable=True,
                  comment='Invoices, warranties, etc.'),

        # Special flags
        sa.Column('is_storno', sa.Boolean(), nullable=False, default=False,
                  comment='Whether order is storno (reversed)'),

        # Order lifecycle timestamps
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('finalized_at', sa.DateTime(), nullable=True),

        # Sync tracking
        sa.Column('sync_status', sa.String(50), nullable=False, default='pending',
                  comment='Sync status: pending, synced, failed'),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True,
                  comment='Last successful sync timestamp'),
        sa.Column('sync_error', sa.Text(), nullable=True,
                  comment='Last sync error message'),
        sa.Column('sync_attempts', sa.Integer(), nullable=False, default=0,
                  comment='Number of sync attempts'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()'),
                  comment='Record creation timestamp'),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()'),
                  comment='Record last update timestamp'),
        sa.Column('order_date', sa.DateTime(), nullable=True,
                  comment='eMAG order date'),
        sa.Column('emag_created_at', sa.DateTime(), nullable=True,
                  comment='eMAG creation timestamp'),
        sa.Column('emag_modified_at', sa.DateTime(), nullable=True,
                  comment='eMAG modification timestamp'),

        # Raw eMAG data (for debugging and future use)
        sa.Column('raw_emag_data', postgresql.JSONB(), nullable=True,
                  comment='Raw eMAG API response for debugging'),

        schema='app'
    )

    # Create indexes for performance
    logger.info("Creating indexes on emag_orders...")

    op.create_index(
        'idx_emag_orders_emag_id_account',
        'emag_orders',
        ['emag_order_id', 'account_type'],
        unique=False,
        schema='app'
    )

    op.create_index(
        'idx_emag_orders_account',
        'emag_orders',
        ['account_type'],
        unique=False,
        schema='app'
    )

    op.create_index(
        'idx_emag_orders_status',
        'emag_orders',
        ['status'],
        unique=False,
        schema='app'
    )

    op.create_index(
        'idx_emag_orders_sync_status',
        'emag_orders',
        ['sync_status'],
        unique=False,
        schema='app'
    )

    op.create_index(
        'idx_emag_orders_order_date',
        'emag_orders',
        ['order_date'],
        unique=False,
        schema='app'
    )

    op.create_index(
        'idx_emag_orders_customer_email',
        'emag_orders',
        ['customer_email'],
        unique=False,
        schema='app'
    )

    # Create unique constraint
    logger.info("Creating unique constraint on emag_orders...")

    op.create_unique_constraint(
        'uq_emag_orders_id_account',
        'emag_orders',
        ['emag_order_id', 'account_type'],
        schema='app'
    )

    # Create check constraints
    logger.info("Creating check constraints on emag_orders...")

    op.create_check_constraint(
        'ck_emag_orders_account_type',
        'emag_orders',
        "account_type IN ('main', 'fbe')",
        schema='app'
    )

    op.create_check_constraint(
        'ck_emag_orders_status',
        'emag_orders',
        'status IN (0,1,2,3,4,5)',
        schema='app'
    )

    op.create_check_constraint(
        'ck_emag_orders_type',
        'emag_orders',
        'type IN (2,3)',
        schema='app'
    )

    logger.info("✅ Successfully created emag_orders table with all indexes and constraints")
    logger.info("IMPORTANT: This table is now ready to store real eMAG order data")
    logger.info("NEXT STEPS:")
    logger.info("1. Run order sync from frontend: 'Sincronizare eMAG (Rapid)'")
    logger.info("2. Verify data: SELECT COUNT(*) FROM app.emag_orders;")
    logger.info("3. Test sold quantity calculation with real data")


def downgrade() -> None:
    """Drop emag_orders table."""
    logger.info("Dropping emag_orders table...")

    # Drop constraints first
    op.drop_constraint('ck_emag_orders_type', 'emag_orders', schema='app', type_='check')
    op.drop_constraint('ck_emag_orders_status', 'emag_orders', schema='app', type_='check')
    op.drop_constraint('ck_emag_orders_account_type', 'emag_orders', schema='app', type_='check')
    op.drop_constraint('uq_emag_orders_id_account', 'emag_orders', schema='app', type_='unique')

    # Drop indexes
    op.drop_index('idx_emag_orders_customer_email', table_name='emag_orders', schema='app')
    op.drop_index('idx_emag_orders_order_date', table_name='emag_orders', schema='app')
    op.drop_index('idx_emag_orders_sync_status', table_name='emag_orders', schema='app')
    op.drop_index('idx_emag_orders_status', table_name='emag_orders', schema='app')
    op.drop_index('idx_emag_orders_account', table_name='emag_orders', schema='app')
    op.drop_index('idx_emag_orders_emag_id_account', table_name='emag_orders', schema='app')

    # Drop table
    op.drop_table('emag_orders', schema='app')

    logger.info("✅ Successfully dropped emag_orders table")
