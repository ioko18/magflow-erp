"""Add product history tracking tables

Revision ID: 10a0b733b02b
Revises: 9986388d397d
Create Date: 2025-10-01 15:19:55.804410

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '10a0b733b02b'
down_revision: str | Sequence[str] | None = '9986388d397d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
