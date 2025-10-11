"""Recreate emag_products_v2 table with correct schema

Revision ID: recreate_emag_v2
Revises: fix_emag_v2_cols
Create Date: 2025-10-04 19:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = 'recreate_emag_v2'
down_revision = 'fix_emag_v2_cols'
branch_labels = None
depends_on = None


def upgrade():
    """Recreate emag_products_v2 table with complete v4.4.9 schema."""
    
    # Drop the old table (it's empty anyway)
    op.execute("DROP TABLE IF EXISTS app.emag_products_v2 CASCADE")
    
    # Create the new table with complete schema
    op.create_table(
        'emag_products_v2',
        # Primary identification
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('emag_id', sa.String(50), nullable=True, index=True),
        sa.Column('sku', sa.String(100), nullable=False, index=True),
        sa.Column('name', sa.String(500), nullable=False),
        
        # Account and source tracking
        sa.Column('account_type', sa.String(10), nullable=False, default='main'),
        sa.Column('source_account', sa.String(50), nullable=True),
        
        # Basic product information
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('brand', sa.String(200), nullable=True),
        sa.Column('manufacturer', sa.String(200), nullable=True),
        
        # Pricing and inventory
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(3), nullable=False, default='RON'),
        sa.Column('stock_quantity', sa.Integer(), nullable=True, default=0),
        
        # Categories and classification
        sa.Column('category_id', sa.String(50), nullable=True),
        sa.Column('emag_category_id', sa.String(50), nullable=True),
        sa.Column('emag_category_name', sa.String(200), nullable=True),
        
        # Product status and availability
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('status', sa.String(50), nullable=True),
        
        # Images and media
        sa.Column('images', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('images_overwrite', sa.Boolean(), nullable=False, default=False),
        
        # eMAG specific fields
        sa.Column('green_tax', sa.Float(), nullable=True),
        sa.Column('supply_lead_time', sa.Integer(), nullable=True),
        
        # GPSR fields
        sa.Column('safety_information', sa.Text(), nullable=True),
        sa.Column('manufacturer_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('eu_representative', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        
        # Product characteristics and attributes
        sa.Column('emag_characteristics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('specifications', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        
        # Sync and metadata
        sa.Column('sync_status', sa.String(50), nullable=False, default='pending'),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('sync_error', sa.Text(), nullable=True),
        sa.Column('sync_attempts', sa.Integer(), nullable=False, default=0),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('emag_created_at', sa.DateTime(), nullable=True),
        sa.Column('emag_modified_at', sa.DateTime(), nullable=True),
        
        # Raw eMAG data
        sa.Column('raw_emag_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        
        # eMAG API v4.4.9 - Validation and Ownership
        sa.Column('validation_status', sa.Integer(), nullable=True),
        sa.Column('validation_status_description', sa.String(255), nullable=True),
        sa.Column('translation_validation_status', sa.Integer(), nullable=True),
        sa.Column('ownership', sa.Integer(), nullable=True),
        
        # eMAG API v4.4.9 - Marketplace Competition
        sa.Column('number_of_offers', sa.Integer(), nullable=True),
        sa.Column('buy_button_rank', sa.Integer(), nullable=True),
        sa.Column('best_offer_sale_price', sa.Float(), nullable=True),
        sa.Column('best_offer_recommended_price', sa.Float(), nullable=True),
        
        # eMAG API v4.4.9 - Advanced Stock
        sa.Column('general_stock', sa.Integer(), nullable=True),
        sa.Column('estimated_stock', sa.Integer(), nullable=True),
        
        # eMAG API v4.4.9 - Measurements
        sa.Column('length_mm', sa.Float(), nullable=True),
        sa.Column('width_mm', sa.Float(), nullable=True),
        sa.Column('height_mm', sa.Float(), nullable=True),
        sa.Column('weight_g', sa.Float(), nullable=True),
        
        # eMAG API v4.4.9 - Genius Program
        sa.Column('genius_eligibility', sa.Integer(), nullable=True),
        sa.Column('genius_eligibility_type', sa.Integer(), nullable=True),
        sa.Column('genius_computed', sa.Integer(), nullable=True),
        
        # eMAG API v4.4.9 - Product Family
        sa.Column('family_id', sa.Integer(), nullable=True),
        sa.Column('family_name', sa.String(255), nullable=True),
        sa.Column('family_type_id', sa.Integer(), nullable=True),
        
        # eMAG API v4.4.9 - Part Number Key
        sa.Column('part_number_key', sa.String(50), nullable=True, index=True),
        
        # eMAG API v4.4.9 - Additional Product Fields
        sa.Column('url', sa.String(1024), nullable=True),
        sa.Column('source_language', sa.String(10), nullable=True),
        sa.Column('warranty', sa.Integer(), nullable=True),
        sa.Column('vat_id', sa.Integer(), nullable=True),
        sa.Column('currency_type', sa.String(3), nullable=True),
        sa.Column('force_images_download', sa.Boolean(), nullable=False, default=False),
        sa.Column('attachments', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        
        # eMAG API v4.4.9 - Offer Validation Status
        sa.Column('offer_validation_status', sa.Integer(), nullable=True),
        sa.Column('offer_validation_status_description', sa.String(255), nullable=True),
        
        # eMAG API v4.4.9 - Documentation Errors
        sa.Column('doc_errors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        
        # eMAG API v4.4.9 - Vendor Category
        sa.Column('vendor_category_id', sa.String(50), nullable=True),
        
        # eMAG API v4.4.9 - EAN
        sa.Column('ean', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        
        # eMAG API v4.4.9 - GPSR Presence Flags
        sa.Column('has_manufacturer_info', sa.Boolean(), nullable=False, default=False),
        sa.Column('has_eu_representative', sa.Boolean(), nullable=False, default=False),
        
        # eMAG API v4.4.9 - Validation Errors Storage
        sa.Column('validation_errors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('translation_validation_errors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        
        # eMAG API v4.4.9 - Image Validation
        sa.Column('main_image_url', sa.String(1024), nullable=True),
        sa.Column('images_validated', sa.Boolean(), nullable=False, default=False),
        
        # eMAG API v4.4.9 - Characteristic Validation
        sa.Column('characteristics_validated', sa.Boolean(), nullable=False, default=False),
        sa.Column('characteristics_validation_errors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        
        schema='app'
    )
    
    # Create indexes
    op.create_index('idx_emag_products_sku_account', 'emag_products_v2', ['sku', 'account_type'], schema='app')
    op.create_index('idx_emag_products_emag_id', 'emag_products_v2', ['emag_id'], schema='app')
    op.create_index('idx_emag_products_sync_status', 'emag_products_v2', ['sync_status'], schema='app')
    op.create_index('idx_emag_products_last_synced', 'emag_products_v2', ['last_synced_at'], schema='app')
    op.create_index('idx_emag_products_category', 'emag_products_v2', ['emag_category_id'], schema='app')
    op.create_index('idx_emag_products_ean', 'emag_products_v2', ['ean'], schema='app')
    op.create_index('idx_emag_products_part_number_key', 'emag_products_v2', ['part_number_key'], schema='app')
    op.create_index('idx_emag_products_validation', 'emag_products_v2', ['validation_status'], schema='app')
    
    # Create unique constraint
    op.create_unique_constraint('uq_emag_products_sku_account', 'emag_products_v2', ['sku', 'account_type'], schema='app')
    
    # Create check constraints
    op.create_check_constraint('ck_emag_products_account_type', 'emag_products_v2', "account_type IN ('main', 'fbe')", schema='app')
    op.create_check_constraint('ck_emag_products_currency', 'emag_products_v2', "currency IN ('RON', 'EUR', 'USD')", schema='app')
    op.create_check_constraint('ck_emag_products_lead_time', 'emag_products_v2', "supply_lead_time IN (2,3,5,7,14,30,60,90,120)", schema='app')


def downgrade():
    """Drop the new table and restore the old one."""
    # This is a destructive operation, so we'll just drop the table
    op.execute("DROP TABLE IF EXISTS app.emag_products_v2 CASCADE")
