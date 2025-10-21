"""change_emag_order_id_to_bigint

Revision ID: 32b7be1a5113
Revises: 20251013_fix_account_type
Create Date: 2025-10-13 20:13:30.161237

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '32b7be1a5113'
down_revision: Union[str, Sequence[str], None] = '20251014_create_emag_orders'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Change emag_order_id from INTEGER to BIGINT
    op.alter_column(
        'emag_orders',
        'emag_order_id',
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
        schema='app'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Revert emag_order_id from BIGINT to INTEGER
    op.alter_column(
        'emag_orders',
        'emag_order_id',
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
        schema='app'
    )
