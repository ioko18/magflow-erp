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
    # Create index with IF NOT EXISTS to avoid conflicts
    conn = op.get_bind()
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_emag_products_v2_part_number_key 
        ON emag_products_v2(part_number_key)
    """))
    
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
    
    # Add new fields to emag_product_offers (note: warranty already exists)
    # Check if columns exist before adding them
    conn = op.get_bind()
    
    # Check and add offer_validation_status
    result = conn.execute(sa.text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_schema = 'app' AND table_name = 'emag_product_offers' 
        AND column_name = 'offer_validation_status'
    """))
    if not result.fetchone():
        op.add_column('emag_product_offers', sa.Column('offer_validation_status', sa.Integer(), nullable=True))
    
    # Check and add offer_validation_status_description
    result = conn.execute(sa.text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_schema = 'app' AND table_name = 'emag_product_offers' 
        AND column_name = 'offer_validation_status_description'
    """))
    if not result.fetchone():
        op.add_column('emag_product_offers', sa.Column('offer_validation_status_description', sa.String(255), nullable=True))
    
    # Check and add vat_id
    result = conn.execute(sa.text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_schema = 'app' AND table_name = 'emag_product_offers' 
        AND column_name = 'vat_id'
    """))
    if not result.fetchone():
        op.add_column('emag_product_offers', sa.Column('vat_id', sa.Integer(), nullable=True))
    
    # Note: warranty column already exists in emag_product_offers, skip adding it
    
    # Create new tables for categories, VAT rates, and handling times (idempotent)
    # These tables are also created in add_emag_reference_data_tables.py
    # Using raw SQL with IF NOT EXISTS to avoid conflicts
    conn = op.get_bind()
    
    # Create emag_categories table if not exists
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS app.emag_categories (
            id INTEGER PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            is_allowed INTEGER NOT NULL DEFAULT 0,
            parent_id INTEGER,
            is_ean_mandatory INTEGER NOT NULL DEFAULT 0,
            is_warranty_mandatory INTEGER NOT NULL DEFAULT 0,
            characteristics JSONB,
            family_types JSONB,
            language VARCHAR(5) NOT NULL DEFAULT 'ro',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_synced_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_emag_categories_parent ON app.emag_categories(parent_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_emag_categories_allowed ON app.emag_categories(is_allowed)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_emag_categories_name ON app.emag_categories(name)"))
    
    # Create emag_vat_rates table if not exists
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS app.emag_vat_rates (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            rate FLOAT NOT NULL,
            country VARCHAR(2) NOT NULL DEFAULT 'RO',
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_synced_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_emag_vat_country ON app.emag_vat_rates(country)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_emag_vat_active ON app.emag_vat_rates(is_active)"))
    
    # Create emag_handling_times table if not exists
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS app.emag_handling_times (
            id INTEGER PRIMARY KEY,
            value INTEGER NOT NULL,
            name VARCHAR(100) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_synced_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_emag_handling_time_value ON app.emag_handling_times(value)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_emag_handling_time_active ON app.emag_handling_times(is_active)"))


def downgrade():
    """Remove Section 8 fields from eMAG models."""
    
    # Drop new tables (idempotent)
    conn = op.get_bind()
    conn.execute(sa.text('DROP INDEX IF EXISTS app.idx_emag_handling_time_active'))
    conn.execute(sa.text('DROP INDEX IF EXISTS app.idx_emag_handling_time_value'))
    conn.execute(sa.text('DROP TABLE IF EXISTS app.emag_handling_times'))
    
    conn.execute(sa.text('DROP INDEX IF EXISTS app.idx_emag_vat_active'))
    conn.execute(sa.text('DROP INDEX IF EXISTS app.idx_emag_vat_country'))
    conn.execute(sa.text('DROP TABLE IF EXISTS app.emag_vat_rates'))
    
    conn.execute(sa.text('DROP INDEX IF EXISTS app.idx_emag_categories_name'))
    conn.execute(sa.text('DROP INDEX IF EXISTS app.idx_emag_categories_allowed'))
    conn.execute(sa.text('DROP INDEX IF EXISTS app.idx_emag_categories_parent'))
    conn.execute(sa.text('DROP TABLE IF EXISTS app.emag_categories'))
    
    # Remove fields from emag_product_offers (skip warranty as it existed before)
    conn = op.get_bind()
    
    # Drop columns if they exist
    result = conn.execute(sa.text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_schema = 'app' AND table_name = 'emag_product_offers' 
        AND column_name = 'vat_id'
    """))
    if result.fetchone():
        op.drop_column('emag_product_offers', 'vat_id')
    
    result = conn.execute(sa.text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_schema = 'app' AND table_name = 'emag_product_offers' 
        AND column_name = 'offer_validation_status_description'
    """))
    if result.fetchone():
        op.drop_column('emag_product_offers', 'offer_validation_status_description')
    
    result = conn.execute(sa.text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_schema = 'app' AND table_name = 'emag_product_offers' 
        AND column_name = 'offer_validation_status'
    """))
    if result.fetchone():
        op.drop_column('emag_product_offers', 'offer_validation_status')
    
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
