"""Add Section 8 fields to eMAG models

Revision ID: add_section8_fields
Revises: 069bd2ae6d01
Create Date: 2025-09-30 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_section8_fields'
down_revision = '069bd2ae6d01'
branch_labels = None
depends_on = None


def upgrade():
    """Add missing fields from eMAG API Section 8 to products and offers."""
    
    # Add new fields to emag_products_v2
    # Genius Program fields
    op.add_column('emag_products_v2', sa.Column('genius_eligibility', sa.Integer(), nullable=True))
    op.add_column('emag_products_v2', sa.Column('genius_eligibility_type', sa.Integer(), nullable=True))
    op.add_column('emag_products_v2', sa.Column('genius_computed', sa.Integer(), nullable=True))
    
    # Product Family fields
    op.add_column('emag_products_v2', sa.Column('family_id', sa.Integer(), nullable=True))
    op.add_column('emag_products_v2', sa.Column('family_name', sa.String(255), nullable=True))
    op.add_column('emag_products_v2', sa.Column('family_type_id', sa.Integer(), nullable=True))
    
    # Part Number Key (for attaching to existing products)
    op.add_column('emag_products_v2', sa.Column('part_number_key', sa.String(50), nullable=True))
    op.create_index('idx_emag_products_v2_part_number_key', 'emag_products_v2', ['part_number_key'])
    
    # Additional Product Fields from Section 8
    op.add_column('emag_products_v2', sa.Column('url', sa.String(1024), nullable=True))
    op.add_column('emag_products_v2', sa.Column('source_language', sa.String(10), nullable=True))
    op.add_column('emag_products_v2', sa.Column('warranty', sa.Integer(), nullable=True))
    op.add_column('emag_products_v2', sa.Column('vat_id', sa.Integer(), nullable=True))
    op.add_column('emag_products_v2', sa.Column('currency_type', sa.String(3), nullable=True))
    op.add_column('emag_products_v2', sa.Column('force_images_download', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('emag_products_v2', sa.Column('attachments', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('emag_products_v2', sa.Column('offer_validation_status', sa.Integer(), nullable=True))
    op.add_column('emag_products_v2', sa.Column('offer_validation_status_description', sa.String(255), nullable=True))
    op.add_column('emag_products_v2', sa.Column('doc_errors', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('emag_products_v2', sa.Column('vendor_category_id', sa.String(50), nullable=True))
    
    # Add new fields to emag_product_offers_v2
    op.add_column('emag_product_offers_v2', sa.Column('offer_validation_status', sa.Integer(), nullable=True))
    op.add_column('emag_product_offers_v2', sa.Column('offer_validation_status_description', sa.String(255), nullable=True))
    op.add_column('emag_product_offers_v2', sa.Column('vat_id', sa.Integer(), nullable=True))
    op.add_column('emag_product_offers_v2', sa.Column('warranty', sa.Integer(), nullable=True))
    
    # Create new tables for categories, VAT rates, and handling times
    op.create_table(
        'emag_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('is_allowed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('is_ean_mandatory', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_warranty_mandatory', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('characteristics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('family_types', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('language', sa.String(5), nullable=False, server_default='ro'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_emag_categories_parent', 'emag_categories', ['parent_id'])
    op.create_index('idx_emag_categories_allowed', 'emag_categories', ['is_allowed'])
    op.create_index('idx_emag_categories_name', 'emag_categories', ['name'])
    
    op.create_table(
        'emag_vat_rates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('rate', sa.Float(), nullable=False),
        sa.Column('country', sa.String(2), nullable=False, server_default='RO'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_emag_vat_country', 'emag_vat_rates', ['country'])
    op.create_index('idx_emag_vat_active', 'emag_vat_rates', ['is_active'])
    
    op.create_table(
        'emag_handling_times',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('value', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_emag_handling_time_value', 'emag_handling_times', ['value'])
    op.create_index('idx_emag_handling_time_active', 'emag_handling_times', ['is_active'])


def downgrade():
    """Remove Section 8 fields from eMAG models."""
    
    # Drop new tables
    op.drop_index('idx_emag_handling_time_active', 'emag_handling_times')
    op.drop_index('idx_emag_handling_time_value', 'emag_handling_times')
    op.drop_table('emag_handling_times')
    
    op.drop_index('idx_emag_vat_active', 'emag_vat_rates')
    op.drop_index('idx_emag_vat_country', 'emag_vat_rates')
    op.drop_table('emag_vat_rates')
    
    op.drop_index('idx_emag_categories_name', 'emag_categories')
    op.drop_index('idx_emag_categories_allowed', 'emag_categories')
    op.drop_index('idx_emag_categories_parent', 'emag_categories')
    op.drop_table('emag_categories')
    
    # Remove fields from emag_product_offers_v2
    op.drop_column('emag_product_offers_v2', 'warranty')
    op.drop_column('emag_product_offers_v2', 'vat_id')
    op.drop_column('emag_product_offers_v2', 'offer_validation_status_description')
    op.drop_column('emag_product_offers_v2', 'offer_validation_status')
    
    # Remove fields from emag_products_v2
    op.drop_column('emag_products_v2', 'vendor_category_id')
    op.drop_column('emag_products_v2', 'doc_errors')
    op.drop_column('emag_products_v2', 'offer_validation_status_description')
    op.drop_column('emag_products_v2', 'offer_validation_status')
    op.drop_column('emag_products_v2', 'attachments')
    op.drop_column('emag_products_v2', 'force_images_download')
    op.drop_column('emag_products_v2', 'currency_type')
    op.drop_column('emag_products_v2', 'vat_id')
    op.drop_column('emag_products_v2', 'warranty')
    op.drop_column('emag_products_v2', 'source_language')
    op.drop_column('emag_products_v2', 'url')
    
    # Remove Part Number Key
    op.drop_index('idx_emag_products_v2_part_number_key', 'emag_products_v2')
    op.drop_column('emag_products_v2', 'part_number_key')
    
    # Remove Product Family fields
    op.drop_column('emag_products_v2', 'family_type_id')
    op.drop_column('emag_products_v2', 'family_name')
    op.drop_column('emag_products_v2', 'family_id')
    
    # Remove Genius Program fields
    op.drop_column('emag_products_v2', 'genius_computed')
    op.drop_column('emag_products_v2', 'genius_eligibility_type')
    op.drop_column('emag_products_v2', 'genius_eligibility')
