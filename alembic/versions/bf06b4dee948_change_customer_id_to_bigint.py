"""change_customer_id_to_bigint

Revision ID: bf06b4dee948
Revises: 32b7be1a5113
Create Date: 2025-10-13 20:14:18.065113
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'bf06b4dee948'
down_revision: str | Sequence[str] | None = '32b7be1a5113'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Change customer_id from INTEGER to BIGINT
    op.alter_column(
        'emag_orders',
        'customer_id',
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
        schema='app'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Revert customer_id from BIGINT to INTEGER
    op.alter_column(
        'emag_orders',
        'customer_id',
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
        schema='app'
    )
