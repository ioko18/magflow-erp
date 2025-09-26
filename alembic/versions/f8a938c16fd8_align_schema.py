"""align schema

Revision ID: f8a938c16fd8
Revises: b1234f5d6c78
Create Date: 2025-09-25 15:45:55.619370

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8a938c16fd8'
down_revision: Union[str, Sequence[str], None] = 'b1234f5d6c78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
