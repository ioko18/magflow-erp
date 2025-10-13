"""add_auxiliary_tables

Revision ID: 20251010_add_auxiliary
Revises: 6d303f2068d4
Create Date: 2025-09-25 16:05:27.860298

This migration consolidates the creation of auxiliary tables:
- audit_logs: For tracking user actions and system events
- product_variants: For managing product variations and republishing
- product_genealogy: For tracking product lifecycle and supersession

Consolidated from:
- 4242d9721c62_add_missing_tables.py (audit_logs)
- 97aa49837ac6_add_product_relationships_tables.py (product_variants, product_genealogy)
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20251010_add_auxiliary'
down_revision: str | Sequence[str] | None = '6d303f2068d4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema by creating auxiliary tables."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names(schema='app')

    # ========================================
    # 1. CREATE AUDIT_LOGS TABLE
    # ========================================
    if 'audit_logs' not in existing_tables:
        op.create_table(
            'audit_logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('action', sa.String(length=100), nullable=False),
            sa.Column('resource', sa.String(length=100), nullable=False),
            sa.Column('resource_id', sa.String(length=100), nullable=True),
            sa.Column('details', sa.Text(), nullable=True),
            sa.Column('ip_address', sa.String(length=45), nullable=True),
            sa.Column('user_agent', sa.String(length=500), nullable=True),
            sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
            sa.Column('success', sa.Boolean(), nullable=False),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['app.users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
            schema='app'
        )
        op.create_index(op.f('ix_app_audit_logs_id'), 'audit_logs', ['id'], unique=False, schema='app')
        print("✅ Created audit_logs table")
    else:
        print("⏭️  Skipped audit_logs table (already exists)")

    # ========================================
    # 2. CREATE PRODUCT_VARIANTS TABLE
    # ========================================
    # Check if required tables exist
    required_tables = ['products', 'emag_products_v2']
    missing_tables = [t for t in required_tables if t not in existing_tables]

    if missing_tables:
        print(f"⚠️  Skipping product_variants migration - missing required tables: {missing_tables}")
        print("ℹ️  These tables will be created by Base.metadata.create_all() or another migration")
    elif 'product_variants' not in existing_tables:
        op.create_table(
            'product_variants',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('variant_group_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column('local_product_id', sa.Integer(), sa.ForeignKey('app.products.id'), nullable=True),
            sa.Column('emag_product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('app.emag_products_v2.id'), nullable=True),
            sa.Column('sku', sa.String(100), nullable=False, index=True),
            sa.Column('ean', postgresql.JSONB(), nullable=True),
            sa.Column('part_number_key', sa.String(50), nullable=True, index=True),
            sa.Column('variant_type', sa.String(50), nullable=False),
            sa.Column('variant_reason', sa.Text(), nullable=True),
            sa.Column('is_primary', sa.Boolean(), nullable=False, default=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
            sa.Column('account_type', sa.String(10), nullable=True),
            sa.Column('parent_variant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('app.product_variants.id'), nullable=True),
            sa.Column('has_competitors', sa.Boolean(), nullable=False, default=False),
            sa.Column('competitor_count', sa.Integer(), nullable=True),
            sa.Column('last_competitor_check', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('deactivated_at', sa.DateTime(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('extra_data', postgresql.JSONB(), nullable=True),
            sa.CheckConstraint(
                "variant_type IN ('original', 'republished', 'competitor_hijacked', 'variation', 'test')",
                name='ck_product_variants_type'
            ),
            sa.CheckConstraint(
                "account_type IN ('main', 'fbe', 'local', 'both') OR account_type IS NULL",
                name='ck_product_variants_account'
            ),
            schema='app'
        )

        # Create indexes for product_variants
        op.create_index('idx_product_variants_group', 'product_variants', ['variant_group_id'], schema='app')
        op.create_index('idx_product_variants_sku', 'product_variants', ['sku'], schema='app')
        op.create_index('idx_product_variants_pnk', 'product_variants', ['part_number_key'], schema='app')
        op.create_index('idx_product_variants_active', 'product_variants', ['is_active'], schema='app')
        op.create_index('idx_product_variants_type', 'product_variants', ['variant_type'], schema='app')
        print("✅ Created product_variants table")
    else:
        print("⏭️  Skipped product_variants table (already exists)")

    # ========================================
    # 3. CREATE PRODUCT_GENEALOGY TABLE
    # ========================================
    if not missing_tables and 'product_genealogy' not in existing_tables:
        op.create_table(
            'product_genealogy',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('family_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column('family_name', sa.String(255), nullable=True),
            sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('product_type', sa.String(20), nullable=False),
            sa.Column('sku', sa.String(100), nullable=False, index=True),
            sa.Column('generation', sa.Integer(), nullable=False, default=1),
            sa.Column('parent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('app.product_genealogy.id'), nullable=True),
            sa.Column('is_root', sa.Boolean(), nullable=False, default=False),
            sa.Column('lifecycle_stage', sa.String(50), nullable=False),
            sa.Column('superseded_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('app.product_genealogy.id'), nullable=True),
            sa.Column('superseded_at', sa.DateTime(), nullable=True),
            sa.Column('supersede_reason', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('extra_data', postgresql.JSONB(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.CheckConstraint(
                "product_type IN ('local', 'emag_main', 'emag_fbe')",
                name='ck_genealogy_product_type'
            ),
            sa.CheckConstraint(
                "lifecycle_stage IN ('active', 'superseded', 'retired', 'archived', 'draft')",
                name='ck_genealogy_lifecycle'
            ),
            sa.CheckConstraint(
                "generation >= 1",
                name='ck_genealogy_generation'
            ),
            schema='app'
        )

        # Create indexes for product_genealogy
        op.create_index('idx_genealogy_family', 'product_genealogy', ['family_id'], schema='app')
        op.create_index('idx_genealogy_sku', 'product_genealogy', ['sku'], schema='app')
        op.create_index('idx_genealogy_stage', 'product_genealogy', ['lifecycle_stage'], schema='app')
        op.create_index('idx_genealogy_root', 'product_genealogy', ['is_root'], schema='app')
        print("✅ Created product_genealogy table")
    else:
        print("⏭️  Skipped product_genealogy table (already exists or missing dependencies)")


def downgrade() -> None:
    """Downgrade schema by dropping auxiliary tables."""
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names(schema='app')

    # Drop product_genealogy table
    if 'product_genealogy' in existing_tables:
        try:
            op.drop_index('idx_genealogy_root', table_name='product_genealogy', schema='app', if_exists=True)
            op.drop_index('idx_genealogy_stage', table_name='product_genealogy', schema='app', if_exists=True)
            op.drop_index('idx_genealogy_sku', table_name='product_genealogy', schema='app', if_exists=True)
            op.drop_index('idx_genealogy_family', table_name='product_genealogy', schema='app', if_exists=True)
            op.drop_table('product_genealogy', schema='app')
            print("✅ Dropped product_genealogy table")
        except Exception as e:
            print(f"⚠️  Error dropping product_genealogy: {e}")

    # Drop product_variants table
    if 'product_variants' in existing_tables:
        try:
            op.drop_index('idx_product_variants_type', table_name='product_variants', schema='app', if_exists=True)
            op.drop_index('idx_product_variants_active', table_name='product_variants', schema='app', if_exists=True)
            op.drop_index('idx_product_variants_pnk', table_name='product_variants', schema='app', if_exists=True)
            op.drop_index('idx_product_variants_sku', table_name='product_variants', schema='app', if_exists=True)
            op.drop_index('idx_product_variants_group', table_name='product_variants', schema='app', if_exists=True)
            op.drop_table('product_variants', schema='app')
            print("✅ Dropped product_variants table")
        except Exception as e:
            print(f"⚠️  Error dropping product_variants: {e}")

    # Drop audit_logs table
    if 'audit_logs' in existing_tables:
        try:
            op.drop_index(op.f('ix_app_audit_logs_id'), table_name='audit_logs', schema='app', if_exists=True)
            op.drop_table('audit_logs', schema='app')
            print("✅ Dropped audit_logs table")
        except Exception as e:
            print(f"⚠️  Error dropping audit_logs: {e}")
