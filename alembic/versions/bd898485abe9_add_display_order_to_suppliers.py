"""Add display_order to suppliers

Revision ID: bd898485abe9
Revises: 7e1f429f9a5b
Create Date: 2025-10-05 14:08:42.559319

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bd898485abe9'
down_revision: Union[str, Sequence[str], None] = '7e1f429f9a5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add display_order column to suppliers table
    op.add_column(
        'suppliers',
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='999'),
        schema='app'
    )
    # Create index on display_order for better query performance
    op.create_index(
        'ix_app_suppliers_display_order',
        'suppliers',
        ['display_order'],
        schema='app'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index
    op.drop_index('ix_app_suppliers_display_order', table_name='suppliers', schema='app')
    # Drop column
    op.drop_column('suppliers', 'display_order', schema='app')
