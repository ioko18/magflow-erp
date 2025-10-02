"""add emag reference data tables

Revision ID: add_emag_reference_data
Revises: add_section8_fields_to_emag_models
Create Date: 2025-09-30 22:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_emag_reference_data'
down_revision = '3880b6b52d31'  # merge_emag_v449_heads
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create eMAG reference data tables for caching categories, VAT rates, and handling times."""
    
    # Create emag_categories table
    op.create_table(
        'emag_categories',
        sa.Column('id', sa.Integer(), nullable=False, comment='eMAG category ID'),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('is_allowed', sa.Integer(), nullable=False, server_default='0', comment='1 if seller can post in this category'),
        sa.Column('parent_id', sa.Integer(), nullable=True, comment='Parent category ID'),
        sa.Column('is_ean_mandatory', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_warranty_mandatory', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('characteristics', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Category characteristics with mandatory flags'),
        sa.Column('family_types', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Family types for product variants'),
        sa.Column('language', sa.String(length=5), nullable=False, server_default='ro', comment='Language code: en, ro, hu, bg, pl, gr, de'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True, comment='Last time synced from eMAG API'),
        sa.PrimaryKeyConstraint('id'),
        schema='app'
    )
    
    # Create indexes for emag_categories
    op.create_index('idx_emag_categories_is_allowed', 'emag_categories', ['is_allowed'], schema='app')
    op.create_index('idx_emag_categories_parent_id', 'emag_categories', ['parent_id'], schema='app')
    op.create_index('idx_emag_categories_language', 'emag_categories', ['language'], schema='app')
    
    # Create emag_vat_rates table
    op.create_table(
        'emag_vat_rates',
        sa.Column('id', sa.Integer(), nullable=False, comment='eMAG VAT rate ID'),
        sa.Column('name', sa.String(length=100), nullable=False, comment="VAT rate name (e.g., 'Standard Rate 19%')"),
        sa.Column('rate', sa.Float(), nullable=False, comment='VAT rate as decimal (e.g., 0.19 for 19%)'),
        sa.Column('country', sa.String(length=2), nullable=False, server_default='RO', comment='Country code'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True, comment='Last time synced from eMAG API'),
        sa.PrimaryKeyConstraint('id'),
        schema='app'
    )
    
    # Create indexes for emag_vat_rates
    op.create_index('idx_emag_vat_rates_is_active', 'emag_vat_rates', ['is_active'], schema='app')
    op.create_index('idx_emag_vat_rates_country', 'emag_vat_rates', ['country'], schema='app')
    
    # Create emag_handling_times table
    op.create_table(
        'emag_handling_times',
        sa.Column('id', sa.Integer(), nullable=False, comment='eMAG handling time ID'),
        sa.Column('value', sa.Integer(), nullable=False, comment='Number of days from order to dispatch'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='Handling time name'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True, comment='Last time synced from eMAG API'),
        sa.PrimaryKeyConstraint('id'),
        schema='app'
    )
    
    # Create indexes for emag_handling_times
    op.create_index('idx_emag_handling_times_value', 'emag_handling_times', ['value'], schema='app')
    op.create_index('idx_emag_handling_times_is_active', 'emag_handling_times', ['is_active'], schema='app')


def downgrade() -> None:
    """Drop eMAG reference data tables."""
    
    # Drop indexes and tables for emag_handling_times
    op.drop_index('idx_emag_handling_times_is_active', table_name='emag_handling_times', schema='app')
    op.drop_index('idx_emag_handling_times_value', table_name='emag_handling_times', schema='app')
    op.drop_table('emag_handling_times', schema='app')
    
    # Drop indexes and tables for emag_vat_rates
    op.drop_index('idx_emag_vat_rates_country', table_name='emag_vat_rates', schema='app')
    op.drop_index('idx_emag_vat_rates_is_active', table_name='emag_vat_rates', schema='app')
    op.drop_table('emag_vat_rates', schema='app')
    
    # Drop indexes and tables for emag_categories
    op.drop_index('idx_emag_categories_language', table_name='emag_categories', schema='app')
    op.drop_index('idx_emag_categories_parent_id', table_name='emag_categories', schema='app')
    op.drop_index('idx_emag_categories_is_allowed', table_name='emag_categories', schema='app')
    op.drop_table('emag_categories', schema='app')
