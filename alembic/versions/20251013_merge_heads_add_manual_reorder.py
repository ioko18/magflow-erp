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
    7. Shipping tax voucher split (from c8e960008812_add_shipping_tax_voucher_split_to_orders)
    8. Missing supplier columns (from 14b0e514876f_add_missing_supplier_columns)
    9. Part number key for emag_products (from 069bd2ae6d01_add_part_number_key_to_emag_products)
    10. Display order for products (from 1bf2989cb727_add_display_order_to_products)
    11. Chinese name for products (from 20251001_034500_add_chinese_name_to_products)
    12. Part number key for emag_product_offers (from 9a5e6b199c94_add_part_number_key_to_emag_product_)
    13. Created/updated timestamps for emag_sync_logs (from 9fd22e656f5c_add_created_at_updated_at_to_emag_sync_)
    14. External ID for orders (from 20250928_add_external_id_to_orders)
    15. Missing columns for emag_products_v2 (from fix_emag_products_v2_missing_columns)
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

    # ========================================================================
    # 6. Add shipping_tax_voucher_split to emag_orders (from c8e960008812)
    # ========================================================================
    try:
        if 'emag_orders' in inspector.get_table_names(schema='app'):
            emag_orders_columns = [
                col['name']
                for col in inspector.get_columns('emag_orders', schema='app')
            ]

            if 'shipping_tax_voucher_split' not in emag_orders_columns:
                op.add_column(
                    'emag_orders',
                    sa.Column('shipping_tax_voucher_split', sa.dialects.postgresql.JSONB(), nullable=True),
                    schema='app'
                )
                print("✅ Added shipping_tax_voucher_split column to emag_orders")
            else:
                print("ℹ️  Column shipping_tax_voucher_split already exists, skipping")
        else:
            print("ℹ️  Table emag_orders not found, skipping")
    except Exception as e:
        print(f"ℹ️  Shipping tax voucher split operation skipped: {e}")

    # ========================================================================
    # 7. Add missing supplier columns (from 14b0e514876f)
    # ========================================================================
    try:
        suppliers_columns = [
            col['name']
            for col in inspector.get_columns('suppliers', schema='app')
        ]

        columns_to_add = {
            'code': sa.Column('code', sa.String(length=20), nullable=True),
            'address': sa.Column('address', sa.Text(), nullable=True),
            'city': sa.Column('city', sa.String(length=50), nullable=True),
            'tax_id': sa.Column('tax_id', sa.String(length=50), nullable=True)
        }

        for col_name, col_def in columns_to_add.items():
            if col_name not in suppliers_columns:
                op.add_column('suppliers', col_def, schema='app')
                print(f"✅ Added {col_name} column to suppliers")
            else:
                print(f"ℹ️  Column {col_name} already exists in suppliers, skipping")

        # Create unique index on code if it doesn't exist
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('suppliers', schema='app')]
        if 'ix_app_suppliers_code' not in existing_indexes:
            op.create_index(op.f('ix_app_suppliers_code'), 'suppliers', ['code'], unique=True, schema='app')
            print("✅ Created unique index on suppliers.code")
        else:
            print("ℹ️  Index ix_app_suppliers_code already exists, skipping")
    except Exception as e:
        print(f"ℹ️  Supplier columns operation skipped: {e}")

    # ========================================================================
    # 8. Add part_number_key to emag_products (from 069bd2ae6d01)
    # ========================================================================
    try:
        if 'emag_products' in inspector.get_table_names(schema='app'):
            emag_products_columns = [
                col['name']
                for col in inspector.get_columns('emag_products', schema='app')
            ]

            if 'part_number_key' not in emag_products_columns:
                op.add_column(
                    'emag_products',
                    sa.Column('part_number_key', sa.String(length=50), nullable=True),
                    schema='app'
                )
                print("✅ Added part_number_key column to emag_products")

                # Create index
                op.create_index('ix_emag_products_part_number_key', 'emag_products', ['part_number_key'], schema='app')
                print("✅ Created index on emag_products.part_number_key")
            else:
                print("ℹ️  Column part_number_key already exists in emag_products, skipping")
        else:
            print("ℹ️  Table emag_products not found, skipping")
    except Exception as e:
        print(f"ℹ️  Part number key operation skipped: {e}")

    # ========================================================================
    # 9. Add display_order to products (from 1bf2989cb727)
    # ========================================================================
    try:
        products_columns = [
            col['name']
            for col in inspector.get_columns('products', schema='app')
        ]

        if 'display_order' not in products_columns:
            op.add_column(
                'products',
                sa.Column('display_order', sa.Integer(), nullable=True, 
                         comment='Custom display order for product listing (lower numbers appear first)'),
                schema='app'
            )
            print("✅ Added display_order column to products")

            # Create index
            op.create_index('ix_app_products_display_order', 'products', ['display_order'], schema='app')
            print("✅ Created index on products.display_order")
        else:
            print("ℹ️  Column display_order already exists in products, skipping")
    except Exception as e:
        print(f"ℹ️  Products display order operation skipped: {e}")

    # ========================================================================
    # 10. Add chinese_name to products (from 20251001_034500)
    # ========================================================================
    try:
        products_columns = [
            col['name']
            for col in inspector.get_columns('products', schema='app')
        ]

        if 'chinese_name' not in products_columns:
            op.add_column(
                'products',
                sa.Column('chinese_name', sa.String(length=500), nullable=True,
                         comment='Chinese product name for supplier matching (1688.com integration)'),
                schema='app'
            )
            print("✅ Added chinese_name column to products")

            # Create index
            op.create_index('ix_app_products_chinese_name', 'products', ['chinese_name'], unique=False, schema='app')
            print("✅ Created index on products.chinese_name")
        else:
            print("ℹ️  Column chinese_name already exists in products, skipping")
    except Exception as e:
        print(f"ℹ️  Chinese name operation skipped: {e}")

    # ========================================================================
    # 11. Add part_number_key to emag_product_offers (from 9a5e6b199c94)
    # ========================================================================
    try:
        if 'emag_product_offers' in inspector.get_table_names(schema='app'):
            offers_columns = [
                col['name']
                for col in inspector.get_columns('emag_product_offers', schema='app')
            ]

            if 'part_number_key' not in offers_columns:
                op.add_column(
                    'emag_product_offers',
                    sa.Column('part_number_key', sa.String(length=50), nullable=True),
                    schema='app'
                )
                print("✅ Added part_number_key column to emag_product_offers")

                # Create index
                op.create_index('ix_emag_product_offers_part_number_key', 'emag_product_offers', ['part_number_key'], schema='app')
                print("✅ Created index on emag_product_offers.part_number_key")
            else:
                print("ℹ️  Column part_number_key already exists in emag_product_offers, skipping")
        else:
            print("ℹ️  Table emag_product_offers not found, skipping")
    except Exception as e:
        print(f"ℹ️  Emag product offers part number key operation skipped: {e}")

    # ========================================================================
    # 12. Add timestamps to emag_sync_logs (from 9fd22e656f5c)
    # ========================================================================
    try:
        if 'emag_sync_logs' in inspector.get_table_names(schema='app'):
            sync_logs_columns = [col['name'] for col in inspector.get_columns('emag_sync_logs', schema='app')]
            
            if 'created_at' not in sync_logs_columns:
                op.add_column('emag_sync_logs', sa.Column('created_at', sa.DateTime(), nullable=False, 
                             server_default=sa.text('CURRENT_TIMESTAMP')), schema='app')
                print("✅ Added created_at to emag_sync_logs")
            
            if 'updated_at' not in sync_logs_columns:
                op.add_column('emag_sync_logs', sa.Column('updated_at', sa.DateTime(), nullable=False,
                             server_default=sa.text('CURRENT_TIMESTAMP')), schema='app')
                print("✅ Added updated_at to emag_sync_logs")
    except Exception as e:
        print(f"ℹ️  Emag sync logs timestamps operation skipped: {e}")

    # ========================================================================
    # 13. Add external_id to orders (from 20250928_add_external_id)
    # ========================================================================
    try:
        if 'orders' in inspector.get_table_names(schema='app'):
            orders_columns = [col['name'] for col in inspector.get_columns('orders', schema='app')]
            
            if 'external_id' not in orders_columns:
                op.add_column('orders', sa.Column('external_id', sa.String(length=100), nullable=True), schema='app')
                op.add_column('orders', sa.Column('external_source', sa.String(length=50), nullable=True), schema='app')
                op.create_index('ix_orders_external_id', 'orders', ['external_id'], unique=False, schema='app')
                op.create_unique_constraint('uq_orders_external_source', 'orders', ['external_id', 'external_source'], schema='app')
                print("✅ Added external_id and external_source to orders")
    except Exception as e:
        print(f"ℹ️  Orders external ID operation skipped: {e}")

    # ========================================================================
    # 14. Fix missing columns in emag_products_v2 (from fix_emag_v2_cols)
    # ========================================================================
    try:
        if 'emag_products_v2' in inspector.get_table_names(schema='app'):
            v2_columns = [col['name'] for col in inspector.get_columns('emag_products_v2', schema='app')]
            
            if 'emag_id' not in v2_columns:
                op.add_column('emag_products_v2', sa.Column('emag_id', sa.String(50), nullable=True), schema='app')
                op.create_index('idx_emag_products_v2_emag_id', 'emag_products_v2', ['emag_id'], schema='app')
                print("✅ Added emag_id to emag_products_v2")
    except Exception as e:
        print(f"ℹ️  Emag products v2 fix operation skipped: {e}")


def downgrade() -> None:
    """Downgrade schema - reverse all operations."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # ========================================================================
    # 11. Remove part_number_key from emag_product_offers
    # ========================================================================
    try:
        if 'emag_product_offers' in inspector.get_table_names(schema='app'):
            # Drop index first
            try:
                op.drop_index('ix_emag_product_offers_part_number_key', table_name='emag_product_offers', schema='app')
                print("✅ Removed index on emag_product_offers.part_number_key")
            except Exception:
                pass

            # Drop column
            op.drop_column('emag_product_offers', 'part_number_key', schema='app')
            print("✅ Removed part_number_key column from emag_product_offers")
    except Exception as e:
        print(f"ℹ️  Emag product offers part number key removal skipped: {e}")

    # ========================================================================
    # 10. Remove chinese_name from products
    # ========================================================================
    try:
        # Drop index first
        try:
            op.drop_index('ix_app_products_chinese_name', table_name='products', schema='app')
            print("✅ Removed index on products.chinese_name")
        except Exception:
            pass

        # Drop column
        op.drop_column('products', 'chinese_name', schema='app')
        print("✅ Removed chinese_name column from products")
    except Exception as e:
        print(f"ℹ️  Chinese name removal skipped: {e}")

    # ========================================================================
    # 9. Remove display_order from products
    # ========================================================================
    try:
        # Drop index first
        try:
            op.drop_index('ix_app_products_display_order', table_name='products', schema='app')
            print("✅ Removed index on products.display_order")
        except Exception:
            pass

        # Drop column
        op.drop_column('products', 'display_order', schema='app')
        print("✅ Removed display_order column from products")
    except Exception as e:
        print(f"ℹ️  Products display order removal skipped: {e}")

    # ========================================================================
    # 8. Remove part_number_key from emag_products
    # ========================================================================
    try:
        if 'emag_products' in inspector.get_table_names(schema='app'):
            # Drop index first
            try:
                op.drop_index('ix_emag_products_part_number_key', table_name='emag_products', schema='app')
                print("✅ Removed index on emag_products.part_number_key")
            except Exception:
                pass

            # Drop column
            op.drop_column('emag_products', 'part_number_key', schema='app')
            print("✅ Removed part_number_key column from emag_products")
    except Exception as e:
        print(f"ℹ️  Part number key removal skipped: {e}")

    # ========================================================================
    # 7. Remove missing supplier columns
    # ========================================================================
    try:
        # Drop index first
        try:
            op.drop_index(op.f('ix_app_suppliers_code'), table_name='suppliers', schema='app')
            print("✅ Removed index on suppliers.code")
        except Exception:
            pass

        # Drop columns
        for col_name in ['tax_id', 'city', 'address', 'code']:
            try:
                op.drop_column('suppliers', col_name, schema='app')
                print(f"✅ Removed {col_name} column from suppliers")
            except Exception:
                pass
    except Exception as e:
        print(f"ℹ️  Supplier columns removal skipped: {e}")

    # ========================================================================
    # 6. Remove shipping_tax_voucher_split from emag_orders
    # ========================================================================
    try:
        if 'emag_orders' in inspector.get_table_names(schema='app'):
            op.drop_column('emag_orders', 'shipping_tax_voucher_split', schema='app')
            print("✅ Removed shipping_tax_voucher_split column from emag_orders")
    except Exception as e:
        print(f"ℹ️  Shipping tax voucher split removal skipped: {e}")

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
