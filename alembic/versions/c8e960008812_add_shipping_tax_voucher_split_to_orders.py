"""add_shipping_tax_voucher_split_to_orders

Revision ID: c8e960008812
Revises: 9fd22e656f5c
Create Date: 2025-09-29 22:00:35.550370

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c8e960008812'
down_revision: str | Sequence[str] | None = '9fd22e656f5c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add shipping_tax_voucher_split column to emag_orders table
    op.add_column(
        'emag_orders',
        sa.Column('shipping_tax_voucher_split', sa.dialects.postgresql.JSONB(), nullable=True),
        schema='app'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove shipping_tax_voucher_split column from emag_orders table
    op.drop_column('emag_orders', 'shipping_tax_voucher_split', schema='app')
