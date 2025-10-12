"""Merge multiple heads and add manual_reorder_quantity column

Revision ID: 20251013_merge_heads
Revises: 20251001_add_unique_constraint_sync_progress, 20251011_enhanced_po_adapted, add_emag_orders_v2, add_emag_reference_data, add_emag_v449_fields, add_invoice_names, create_product_mapping, create_supplier_sheets, perf_idx_20251010, recreate_emag_v2, supplier_matching_001
Create Date: 2025-10-13 01:25:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20251013_merge_heads'
down_revision: str | Sequence[str] | None = (
    '20251001_add_unique_constraint_sync_progress',
    '20251011_enhanced_po_adapted',
    'add_emag_orders_v2',
    'add_emag_reference_data',
    'add_emag_v449_fields',
    'add_invoice_names',
    'create_product_mapping',
    'create_supplier_sheets',
    'perf_idx_20251010',
    'recreate_emag_v2',
    'supplier_matching_001',
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge multiple heads and add manual_reorder_quantity column."""

    # Get connection and inspector
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Check if column already exists
    existing_columns = [
        col['name']
        for col in inspector.get_columns('inventory_items', schema='app')
    ]

    if 'manual_reorder_quantity' not in existing_columns:
        # Add manual_reorder_quantity column to inventory_items table
        op.add_column(
            'inventory_items',
            sa.Column('manual_reorder_quantity', sa.Integer(), nullable=True),
            schema='app',
        )

        # Add comment to explain the column
        op.execute("""
            COMMENT ON COLUMN app.inventory_items.manual_reorder_quantity IS
            'Manual override for reorder quantity. If set, this value takes precedence over automatic calculation.'
        """)
        print("✅ Added manual_reorder_quantity column")
    else:
        print("ℹ️  Column manual_reorder_quantity already exists, skipping")


def downgrade() -> None:
    """Downgrade schema."""
    # Check if column exists before dropping
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    existing_columns = [
        col['name']
        for col in inspector.get_columns('inventory_items', schema='app')
    ]

    if 'manual_reorder_quantity' in existing_columns:
        # Remove manual_reorder_quantity column
        op.drop_column('inventory_items', 'manual_reorder_quantity', schema='app')
        print("✅ Removed manual_reorder_quantity column")
    else:
        print("ℹ️  Column manual_reorder_quantity doesn't exist, skipping")
