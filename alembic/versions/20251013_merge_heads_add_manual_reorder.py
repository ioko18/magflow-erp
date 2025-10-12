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
    """Merge multiple heads and add manual_reorder_quantity column.

    This migration consolidates:
    1. All 11 separate heads into one unified head
    2. Adds manual_reorder_quantity column (new feature)
    3. Adds unique constraint from 20251001_add_unique_constraint_sync_progress
    """

    # Get connection and inspector
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # ========================================================================
    # 1. Add manual_reorder_quantity column (NEW FEATURE)
    # ========================================================================
    existing_columns = [
        col['name']
        for col in inspector.get_columns('inventory_items', schema='app')
    ]

    if 'manual_reorder_quantity' not in existing_columns:
        op.add_column(
            'inventory_items',
            sa.Column('manual_reorder_quantity', sa.Integer(), nullable=True),
            schema='app',
        )

        op.execute("""
            COMMENT ON COLUMN app.inventory_items.manual_reorder_quantity IS
            'Manual override for reorder quantity. If set, this value takes precedence over automatic calculation.'
        """)
        print("✅ Added manual_reorder_quantity column")
    else:
        print("ℹ️  Column manual_reorder_quantity already exists, skipping")

    # ========================================================================
    # 2. Add unique constraint (from 20251001_add_unique_constraint_sync_progress)
    # ========================================================================
    # Check if constraint already exists
    existing_constraints = [
        c['name']
        for c in inspector.get_unique_constraints('emag_sync_progress', schema='app')
    ]

    if 'uq_emag_sync_progress_sync_log_id' not in existing_constraints:
        try:
            op.create_unique_constraint(
                "uq_emag_sync_progress_sync_log_id",
                "emag_sync_progress",
                ["sync_log_id"],
                schema='app'
            )
            print("✅ Added unique constraint on emag_sync_progress.sync_log_id")
        except Exception as e:
            print(f"ℹ️  Constraint might already exist or table not found: {e}")
    else:
        print("ℹ️  Unique constraint already exists, skipping")


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # ========================================================================
    # 1. Remove unique constraint
    # ========================================================================
    existing_constraints = [
        c['name']
        for c in inspector.get_unique_constraints('emag_sync_progress', schema='app')
    ]

    if 'uq_emag_sync_progress_sync_log_id' in existing_constraints:
        try:
            op.drop_constraint(
                "uq_emag_sync_progress_sync_log_id",
                "emag_sync_progress",
                type_="unique",
                schema='app'
            )
            print("✅ Removed unique constraint")
        except Exception as e:
            print(f"ℹ️  Could not remove constraint: {e}")

    # ========================================================================
    # 2. Remove manual_reorder_quantity column
    # ========================================================================
    existing_columns = [
        col['name']
        for col in inspector.get_columns('inventory_items', schema='app')
    ]

    if 'manual_reorder_quantity' in existing_columns:
        op.drop_column('inventory_items', 'manual_reorder_quantity', schema='app')
        print("✅ Removed manual_reorder_quantity column")
    else:
        print("ℹ️  Column manual_reorder_quantity doesn't exist, skipping")
