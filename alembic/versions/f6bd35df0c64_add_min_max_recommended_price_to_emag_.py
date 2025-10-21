"""add_min_max_recommended_price_to_emag_product_offers

Revision ID: f6bd35df0c64
Revises: bf06b4dee948
Create Date: 2025-10-18 15:07:39.793588

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6bd35df0c64'
down_revision: Union[str, Sequence[str], None] = 'bf06b4dee948'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add min_sale_price, max_sale_price, and recommended_price columns to emag_product_offers
    op.add_column(
        'emag_product_offers',
        sa.Column('min_sale_price', sa.Float(), nullable=True, comment='Minimum sale price (ex-VAT)'),
        schema='app'
    )
    op.add_column(
        'emag_product_offers',
        sa.Column('max_sale_price', sa.Float(), nullable=True, comment='Maximum sale price (ex-VAT)'),
        schema='app'
    )
    op.add_column(
        'emag_product_offers',
        sa.Column('recommended_price', sa.Float(), nullable=True, comment='Recommended retail price (ex-VAT)'),
        schema='app'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove the added columns
    op.drop_column('emag_product_offers', 'recommended_price', schema='app')
    op.drop_column('emag_product_offers', 'max_sale_price', schema='app')
    op.drop_column('emag_product_offers', 'min_sale_price', schema='app')
