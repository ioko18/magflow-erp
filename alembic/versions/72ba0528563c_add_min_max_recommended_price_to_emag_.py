"""add_min_max_recommended_price_to_emag_product_offers_v2

Revision ID: 72ba0528563c
Revises: f6bd35df0c64
Create Date: 2025-10-18 15:17:50.277884

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '72ba0528563c'
down_revision: Union[str, Sequence[str], None] = 'f6bd35df0c64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add min_sale_price, max_sale_price, and recommended_price columns to emag_product_offers_v2
    op.add_column(
        'emag_product_offers_v2',
        sa.Column('min_sale_price', sa.Float(), nullable=True, comment='Minimum sale price (ex-VAT)'),
        schema='app'
    )
    op.add_column(
        'emag_product_offers_v2',
        sa.Column('max_sale_price', sa.Float(), nullable=True, comment='Maximum sale price (ex-VAT)'),
        schema='app'
    )
    op.add_column(
        'emag_product_offers_v2',
        sa.Column('recommended_price', sa.Float(), nullable=True, comment='Recommended retail price (ex-VAT)'),
        schema='app'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove the added columns
    op.drop_column('emag_product_offers_v2', 'recommended_price', schema='app')
    op.drop_column('emag_product_offers_v2', 'max_sale_price', schema='app')
    op.drop_column('emag_product_offers_v2', 'min_sale_price', schema='app')
