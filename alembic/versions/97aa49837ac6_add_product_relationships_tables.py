"""add_product_relationships_tables

Revision ID: 97aa49837ac6
Revises: 14b0e514876f
Create Date: 2025-10-10 20:23:53.439853

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '97aa49837ac6'
down_revision: str | Sequence[str] | None = '14b0e514876f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    # Create product_variants table
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

    # Create product_genealogy table
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


def downgrade() -> None:
    """Downgrade schema."""

    # Drop product_genealogy table
    op.drop_index('idx_genealogy_root', table_name='product_genealogy', schema='app')
    op.drop_index('idx_genealogy_stage', table_name='product_genealogy', schema='app')
    op.drop_index('idx_genealogy_sku', table_name='product_genealogy', schema='app')
    op.drop_index('idx_genealogy_family', table_name='product_genealogy', schema='app')
    op.drop_table('product_genealogy', schema='app')

    # Drop product_variants table
    op.drop_index('idx_product_variants_type', table_name='product_variants', schema='app')
    op.drop_index('idx_product_variants_active', table_name='product_variants', schema='app')
    op.drop_index('idx_product_variants_pnk', table_name='product_variants', schema='app')
    op.drop_index('idx_product_variants_sku', table_name='product_variants', schema='app')
    op.drop_index('idx_product_variants_group', table_name='product_variants', schema='app')
    op.drop_table('product_variants', schema='app')
