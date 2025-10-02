"""add chinese_name to products

Revision ID: 20251001_034500
Revises: 069bd2ae6d01
Create Date: 2025-10-01 03:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251001_034500'
down_revision = '069bd2ae6d01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add chinese_name column to products table for supplier matching."""
    # Add chinese_name column
    op.add_column(
        'products',
        sa.Column(
            'chinese_name',
            sa.String(length=500),
            nullable=True,
            comment='Chinese product name for supplier matching (1688.com integration)'
        ),
        schema='app'
    )
    
    # Add index for better search performance
    op.create_index(
        'ix_app_products_chinese_name',
        'products',
        ['chinese_name'],
        unique=False,
        schema='app'
    )


def downgrade() -> None:
    """Remove chinese_name column from products table."""
    # Drop index first
    op.drop_index('ix_app_products_chinese_name', table_name='products', schema='app')
    
    # Drop column
    op.drop_column('products', 'chinese_name', schema='app')
