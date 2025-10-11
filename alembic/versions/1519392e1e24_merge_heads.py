"""merge heads

Revision ID: 1519392e1e24
Revises: 86f7456767fd
Create Date: 2025-09-24 09:08:58.357004

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = '1519392e1e24'
down_revision: Union[str, Sequence[str], None] = '86f7456767fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
