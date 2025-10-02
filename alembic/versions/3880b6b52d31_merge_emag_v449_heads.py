"""merge_emag_v449_heads

Revision ID: 3880b6b52d31
Revises: 8ee48849d280, add_emag_v449_fields, c8e960008812
Create Date: 2025-09-30 20:02:00.304329

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3880b6b52d31'
down_revision: Union[str, Sequence[str], None] = ('8ee48849d280', 'add_emag_v449_fields', 'c8e960008812')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
