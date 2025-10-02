"""Add product history tracking tables

Revision ID: 10a0b733b02b
Revises: 9986388d397d
Create Date: 2025-10-01 15:19:55.804410

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '10a0b733b02b'
down_revision: Union[str, Sequence[str], None] = '9986388d397d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
