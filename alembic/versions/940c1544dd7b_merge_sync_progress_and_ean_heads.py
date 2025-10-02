"""merge_sync_progress_and_ean_heads

Revision ID: 940c1544dd7b
Revises: 20251001_add_unique_constraint_sync_progress, ee01e67b1bcc
Create Date: 2025-10-01 19:58:13.103163

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '940c1544dd7b'
down_revision: Union[str, Sequence[str], None] = ('20251001_add_unique_constraint_sync_progress', 'ee01e67b1bcc')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
