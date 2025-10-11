"""Add eMAG API v4.4.9 fields

Revision ID: add_emag_v449_fields
Revises: c8e960008812
Create Date: 2025-09-30 14:40:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_emag_v449_fields'
down_revision = 'c8e960008812'  # Links to add_shipping_tax_voucher_split_to_orders
branch_labels = None
depends_on = None


def upgrade():
    """Add eMAG API v4.4.9 new fields to emag_products_v2 table."""
    
    # Check and add columns only if they don't exist (idempotent)
    conn = op.get_bind()
    
    # Add validation status fields (skip if already exist from 8ee48849d280)
    columns_to_add = [
        ('validation_status', 'INTEGER'),
        ('validation_status_description', 'VARCHAR(255)'),
        ('translation_validation_status', 'INTEGER'),
        ('ownership', 'INTEGER'),
        ('number_of_offers', 'INTEGER'),
        ('buy_button_rank', 'INTEGER'),
        ('best_offer_sale_price', 'NUMERIC(10, 4)'),
        ('best_offer_recommended_price', 'NUMERIC(10, 4)'),
        ('general_stock', 'INTEGER'),
        ('estimated_stock', 'INTEGER'),
        ('length_mm', 'NUMERIC(10, 2)'),
        ('width_mm', 'NUMERIC(10, 2)'),
        ('height_mm', 'NUMERIC(10, 2)'),
        ('weight_g', 'NUMERIC(10, 2)'),
    ]
    
    for col_name, col_type in columns_to_add:
        # Check if column exists
        result = conn.execute(sa.text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'app' 
            AND table_name = 'emag_products_v2' 
            AND column_name = '{col_name}'
        """))
        if not result.fetchone():
            conn.execute(sa.text(f"""
                ALTER TABLE app.emag_products_v2 
                ADD COLUMN {col_name} {col_type}
            """))
    
    # Add indexes for performance (with IF NOT EXISTS)
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_emag_products_v2_validation_status 
        ON app.emag_products_v2(validation_status)
    """))
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_emag_products_v2_ownership 
        ON app.emag_products_v2(ownership)
    """))
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_emag_products_v2_buy_button_rank 
        ON app.emag_products_v2(buy_button_rank)
    """))
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_emag_products_v2_number_of_offers 
        ON app.emag_products_v2(number_of_offers)
    """))
    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_emag_products_v2_validation_ownership 
        ON app.emag_products_v2(validation_status, ownership)
    """))


def downgrade():
    """Remove eMAG API v4.4.9 fields."""
    
    # Remove indexes
    op.drop_index('idx_emag_products_v2_validation_ownership', 'emag_products_v2', schema='app')
    op.drop_index('idx_emag_products_v2_number_of_offers', 'emag_products_v2', schema='app')
    op.drop_index('idx_emag_products_v2_buy_button_rank', 'emag_products_v2', schema='app')
    op.drop_index('idx_emag_products_v2_ownership', 'emag_products_v2', schema='app')
    op.drop_index('idx_emag_products_v2_validation_status', 'emag_products_v2', schema='app')
    
    # Remove columns
    op.drop_column('emag_products_v2', 'weight_g', schema='app')
    op.drop_column('emag_products_v2', 'height_mm', schema='app')
    op.drop_column('emag_products_v2', 'width_mm', schema='app')
    op.drop_column('emag_products_v2', 'length_mm', schema='app')
    op.drop_column('emag_products_v2', 'estimated_stock', schema='app')
    op.drop_column('emag_products_v2', 'general_stock', schema='app')
    op.drop_column('emag_products_v2', 'best_offer_recommended_price', schema='app')
    op.drop_column('emag_products_v2', 'best_offer_sale_price', schema='app')
    op.drop_column('emag_products_v2', 'buy_button_rank', schema='app')
    op.drop_column('emag_products_v2', 'number_of_offers', schema='app')
    op.drop_column('emag_products_v2', 'ownership', schema='app')
    op.drop_column('emag_products_v2', 'translation_validation_status', schema='app')
    op.drop_column('emag_products_v2', 'validation_status_description', schema='app')
    op.drop_column('emag_products_v2', 'validation_status', schema='app')
