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
    """Merge multiple heads and consolidate small migrations.

    This migration consolidates:
    1. All 11 separate heads into one unified head
    2. manual_reorder_quantity column (NEW FEATURE)
    3. Unique constraint (from 20251001_add_unique_constraint_sync_progress)
    4. Invoice name columns (from add_invoice_names_to_products)
    5. EAN column and index (from ee01e67b1bcc_add_ean_column_to_emag_products_v2)
    6. Display order for suppliers (from bd898485abe9_add_display_order_to_suppliers)
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
    try:
        existing_constraints = [
            c['name']
            for c in inspector.get_unique_constraints('emag_sync_progress', schema='app')
        ]

        if 'uq_emag_sync_progress_sync_log_id' not in existing_constraints:
            op.create_unique_constraint(
                "uq_emag_sync_progress_sync_log_id",
                "emag_sync_progress",
                ["sync_log_id"],
                schema='app'
            )
            print("✅ Added unique constraint on emag_sync_progress.sync_log_id")
        else:
            print("ℹ️  Unique constraint already exists, skipping")
    except Exception as e:
        print(f"ℹ️  Constraint operation skipped: {e}")

    # ========================================================================
    # 3. Add invoice name columns (from add_invoice_names_to_products)
    # ========================================================================
    try:
        products_columns = [
            col['name']
            for col in inspector.get_columns('products', schema='app')
        ]

        if 'invoice_name_ro' not in products_columns:
            op.add_column(
                'products',
                sa.Column('invoice_name_ro', sa.String(200), nullable=True,
                         comment='Product name for Romanian invoices (shorter, customs-friendly)'),
                schema='app'
            )
            print("✅ Added invoice_name_ro column")
        else:
            print("ℹ️  Column invoice_name_ro already exists, skipping")

        if 'invoice_name_en' not in products_columns:
            op.add_column(
                'products',
                sa.Column('invoice_name_en', sa.String(200), nullable=True,
                         comment='Product name for English invoices (customs declarations, VAT)'),
                schema='app'
            )
            print("✅ Added invoice_name_en column")
        else:
            print("ℹ️  Column invoice_name_en already exists, skipping")
    except Exception as e:
        print(f"ℹ️  Invoice columns operation skipped: {e}")

    # ========================================================================
    # 4. Add EAN column and index (from ee01e67b1bcc_add_ean_column_to_emag_products_v2)
    # ========================================================================
    try:
        # Check if emag_products_v2 table exists
        if 'emag_products_v2' in inspector.get_table_names(schema='app'):
            emag_columns = [
                col['name']
                for col in inspector.get_columns('emag_products_v2', schema='app')
            ]

            if 'ean' not in emag_columns:
                op.execute("""
                    ALTER TABLE app.emag_products_v2
                    ADD COLUMN IF NOT EXISTS ean JSONB
                """)
                print("✅ Added ean column to emag_products_v2")
            else:
                print("ℹ️  Column ean already exists in emag_products_v2, skipping")

            # Create index if it doesn't exist
            op.execute("""
                CREATE INDEX IF NOT EXISTS idx_emag_products_ean
                ON app.emag_products_v2 USING gin (ean)
            """)
            print("✅ Created index on ean column")
        else:
            print("ℹ️  Table emag_products_v2 not found, skipping EAN column")
    except Exception as e:
        print(f"ℹ️  EAN column operation skipped: {e}")

    # ========================================================================
    # 5. Add display_order to suppliers (from bd898485abe9_add_display_order_to_suppliers)
    # ========================================================================
    try:
        suppliers_columns = [
            col['name']
            for col in inspector.get_columns('suppliers', schema='app')
        ]

        if 'display_order' not in suppliers_columns:
            op.add_column(
                'suppliers',
                sa.Column('display_order', sa.Integer(), nullable=False, server_default='999'),
                schema='app'
            )
            print("✅ Added display_order column to suppliers")

            # Create index
            op.create_index(
                'ix_app_suppliers_display_order',
                'suppliers',
                ['display_order'],
                schema='app'
            )
            print("✅ Created index on suppliers.display_order")
        else:
            print("ℹ️  Column display_order already exists in suppliers, skipping")
    except Exception as e:
        print(f"ℹ️  Display order operation skipped: {e}")


def downgrade() -> None:
    """Downgrade schema - reverse all operations."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # ========================================================================
    # 5. Remove display_order from suppliers
    # ========================================================================
    try:
        suppliers_columns = [
            col['name']
            for col in inspector.get_columns('suppliers', schema='app')
        ]

        if 'display_order' in suppliers_columns:
            # Drop index first
            try:
                op.drop_index('ix_app_suppliers_display_order', table_name='suppliers', schema='app')
                print("✅ Removed index on suppliers.display_order")
            except Exception:
                pass

            # Drop column
            op.drop_column('suppliers', 'display_order', schema='app')
            print("✅ Removed display_order column from suppliers")
    except Exception as e:
        print(f"ℹ️  Display order removal skipped: {e}")

    # ========================================================================
    # 4. Remove EAN column and index
    # ========================================================================
    try:
        if 'emag_products_v2' in inspector.get_table_names(schema='app'):
            # Drop index
            op.execute("DROP INDEX IF EXISTS app.idx_emag_products_ean")
            print("✅ Removed index on ean column")

            # Drop column
            op.execute("ALTER TABLE app.emag_products_v2 DROP COLUMN IF EXISTS ean")
            print("✅ Removed ean column from emag_products_v2")
    except Exception as e:
        print(f"ℹ️  EAN removal skipped: {e}")

    # ========================================================================
    # 3. Remove invoice name columns
    # ========================================================================
    try:
        products_columns = [
            col['name']
            for col in inspector.get_columns('products', schema='app')
        ]

        if 'invoice_name_en' in products_columns:
            op.drop_column('products', 'invoice_name_en', schema='app')
            print("✅ Removed invoice_name_en column")

        if 'invoice_name_ro' in products_columns:
            op.drop_column('products', 'invoice_name_ro', schema='app')
            print("✅ Removed invoice_name_ro column")
    except Exception as e:
        print(f"ℹ️  Invoice columns removal skipped: {e}")

    # ========================================================================
    # 2. Remove unique constraint
    # ========================================================================
    try:
        existing_constraints = [
            c['name']
            for c in inspector.get_unique_constraints('emag_sync_progress', schema='app')
        ]

        if 'uq_emag_sync_progress_sync_log_id' in existing_constraints:
            op.drop_constraint(
                "uq_emag_sync_progress_sync_log_id",
                "emag_sync_progress",
                type_="unique",
                schema='app'
            )
            print("✅ Removed unique constraint")
    except Exception as e:
        print(f"ℹ️  Constraint removal skipped: {e}")

    # ========================================================================
    # 1. Remove manual_reorder_quantity column
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
