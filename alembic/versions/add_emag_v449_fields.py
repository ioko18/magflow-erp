"""Add eMAG API v4.4.9 fields

Revision ID: add_emag_v449_fields
Revises: 
Create Date: 2025-09-30 14:40:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_emag_v449_fields'
down_revision = None  # Update this to your latest revision
branch_labels = None
depends_on = None


def upgrade():
    """Add eMAG API v4.4.9 new fields to emag_products_v2 table."""
    
    # Add validation status fields
    op.add_column('emag_products_v2', 
        sa.Column('validation_status', sa.Integer(), nullable=True),
        schema='app')
    op.add_column('emag_products_v2', 
        sa.Column('validation_status_description', sa.String(255), nullable=True),
        schema='app')
    op.add_column('emag_products_v2', 
        sa.Column('translation_validation_status', sa.Integer(), nullable=True),
        schema='app')
    
    # Add ownership field (1 = can modify documentation, 2 = cannot modify)
    op.add_column('emag_products_v2', 
        sa.Column('ownership', sa.Integer(), nullable=True),
        schema='app')
    
    # Add competition metrics
    op.add_column('emag_products_v2', 
        sa.Column('number_of_offers', sa.Integer(), nullable=True),
        schema='app')
    op.add_column('emag_products_v2', 
        sa.Column('buy_button_rank', sa.Integer(), nullable=True),
        schema='app')
    op.add_column('emag_products_v2', 
        sa.Column('best_offer_sale_price', sa.Numeric(10, 4), nullable=True),
        schema='app')
    op.add_column('emag_products_v2', 
        sa.Column('best_offer_recommended_price', sa.Numeric(10, 4), nullable=True),
        schema='app')
    
    # Add advanced stock fields
    op.add_column('emag_products_v2', 
        sa.Column('general_stock', sa.Integer(), nullable=True),
        schema='app')
    op.add_column('emag_products_v2', 
        sa.Column('estimated_stock', sa.Integer(), nullable=True),
        schema='app')
    
    # Add measurements fields (in mm and g as per eMAG API spec)
    op.add_column('emag_products_v2', 
        sa.Column('length_mm', sa.Numeric(10, 2), nullable=True),
        schema='app')
    op.add_column('emag_products_v2', 
        sa.Column('width_mm', sa.Numeric(10, 2), nullable=True),
        schema='app')
    op.add_column('emag_products_v2', 
        sa.Column('height_mm', sa.Numeric(10, 2), nullable=True),
        schema='app')
    op.add_column('emag_products_v2', 
        sa.Column('weight_g', sa.Numeric(10, 2), nullable=True),
        schema='app')
    
    # Add indexes for performance
    op.create_index('idx_emag_products_v2_validation_status', 'emag_products_v2', 
                    ['validation_status'], schema='app')
    op.create_index('idx_emag_products_v2_ownership', 'emag_products_v2', 
                    ['ownership'], schema='app')
    op.create_index('idx_emag_products_v2_buy_button_rank', 'emag_products_v2', 
                    ['buy_button_rank'], schema='app')
    op.create_index('idx_emag_products_v2_number_of_offers', 'emag_products_v2', 
                    ['number_of_offers'], schema='app')
    
    # Add composite index for filtering by validation and ownership
    op.create_index('idx_emag_products_v2_validation_ownership', 'emag_products_v2', 
                    ['validation_status', 'ownership'], schema='app')


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
