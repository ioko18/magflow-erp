"""add_validation_columns_to_emag_products

Revision ID: 8ee48849d280
Revises: add_emag_orders_v2
Create Date: 2025-09-30 15:37:39.462224

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8ee48849d280'
down_revision: Union[str, Sequence[str], None] = 'add_emag_orders_v2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('emag_products_v2', sa.Column('validation_status', sa.String(50), nullable=True))
    op.add_column('emag_products_v2', sa.Column('validation_status_description', sa.Text(), nullable=True))
    op.add_column('emag_products_v2', sa.Column('translation_validation_status', sa.String(50), nullable=True))
    op.add_column('emag_products_v2', sa.Column('ownership', sa.String(50), nullable=True))
    op.add_column('emag_products_v2', sa.Column('number_of_offers', sa.Integer(), nullable=True))
    op.add_column('emag_products_v2', sa.Column('buy_button_rank', sa.Integer(), nullable=True))
    op.add_column('emag_products_v2', sa.Column('best_offer_sale_price', sa.Numeric(10, 2), nullable=True))
    op.add_column('emag_products_v2', sa.Column('best_offer_recommended_price', sa.Numeric(10, 2), nullable=True))
    op.add_column('emag_products_v2', sa.Column('general_stock', sa.Boolean(), nullable=True))
    op.add_column('emag_products_v2', sa.Column('estimated_stock', sa.Boolean(), nullable=True))
    op.add_column('emag_products_v2', sa.Column('length_mm', sa.Integer(), nullable=True))
    op.add_column('emag_products_v2', sa.Column('width_mm', sa.Integer(), nullable=True))
    op.add_column('emag_products_v2', sa.Column('height_mm', sa.Integer(), nullable=True))
    op.add_column('emag_products_v2', sa.Column('weight_g', sa.Integer(), nullable=True))

    # Adăugare indecși pentru noile câmpuri dacă este necesar
    op.create_index('idx_emag_products_v2_validation_status', 'emag_products_v2', ['validation_status'])
    op.create_index('idx_emag_products_v2_ownership', 'emag_products_v2', ['ownership'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_emag_products_v2_ownership', table_name='emag_products_v2')
    op.drop_index('idx_emag_products_v2_validation_status', table_name='emag_products_v2')
    
    op.drop_column('emag_products_v2', 'weight_g')
    op.drop_column('emag_products_v2', 'height_mm')
    op.drop_column('emag_products_v2', 'width_mm')
    op.drop_column('emag_products_v2', 'length_mm')
    op.drop_column('emag_products_v2', 'estimated_stock')
    op.drop_column('emag_products_v2', 'general_stock')
    op.drop_column('emag_products_v2', 'best_offer_recommended_price')
    op.drop_column('emag_products_v2', 'best_offer_sale_price')
    op.drop_column('emag_products_v2', 'buy_button_rank')
    op.drop_column('emag_products_v2', 'number_of_offers')
    op.drop_column('emag_products_v2', 'ownership')
    op.drop_column('emag_products_v2', 'translation_validation_status')
    op.drop_column('emag_products_v2', 'validation_status_description')
    op.drop_column('emag_products_v2', 'validation_status')
