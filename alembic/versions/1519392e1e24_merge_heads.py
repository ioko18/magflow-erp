"""merge heads

Revision ID: 1519392e1e24
Revises: 86f7456767fd
Create Date: 2025-09-24 09:08:58.357004

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '1519392e1e24'
down_revision: str | Sequence[str] | None = '86f7456767fd'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
