"""add_created_at_updated_at_to_emag_sync_logs

Revision ID: 9fd22e656f5c
Revises: 2b1cec644957
Create Date: 2025-09-29 19:12:41.351081

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9fd22e656f5c'
down_revision: Union[str, Sequence[str], None] = '2b1cec644957'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add created_at and updated_at columns to emag_sync_logs table."""
    # Add created_at column with default value
    op.add_column('emag_sync_logs', 
                  sa.Column('created_at', sa.DateTime(), nullable=False, 
                           server_default=sa.text('CURRENT_TIMESTAMP')))
    
    # Add updated_at column with default value
    op.add_column('emag_sync_logs', 
                  sa.Column('updated_at', sa.DateTime(), nullable=False, 
                           server_default=sa.text('CURRENT_TIMESTAMP')))


def downgrade() -> None:
    """Remove created_at and updated_at columns from emag_sync_logs table."""
    op.drop_column('emag_sync_logs', 'updated_at')
    op.drop_column('emag_sync_logs', 'created_at')
