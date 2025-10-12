"""add_display_order_to_products

Revision ID: 1bf2989cb727
Revises: 940c1544dd7b
Create Date: 2025-10-02 23:24:23.963098

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1bf2989cb727'
down_revision: str | Sequence[str] | None = '940c1544dd7b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add display_order column to products table
    op.add_column(
        'products',
        sa.Column('display_order', sa.Integer(), nullable=True, comment='Custom display order for product listing (lower numbers appear first)'),
        schema='app'
    )

    # Create index on display_order for better query performance
    op.create_index(
        'ix_app_products_display_order',
        'products',
        ['display_order'],
        schema='app'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index first
    op.drop_index('ix_app_products_display_order', table_name='products', schema='app')

    # Drop display_order column
    op.drop_column('products', 'display_order', schema='app')
