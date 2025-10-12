"""Merge multiple heads

Revision ID: 7e1f429f9a5b
Revises: create_supplier_sheets, recreate_emag_v2
Create Date: 2025-10-05 14:08:28.320162

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '7e1f429f9a5b'
down_revision: str | Sequence[str] | None = ('create_supplier_sheets', 'recreate_emag_v2')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
