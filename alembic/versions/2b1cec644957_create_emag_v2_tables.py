"""create_emag_v2_tables

Revision ID: 2b1cec644957
Revises: 0eae9be5122f
Create Date: 2025-09-29 17:08:35.417206

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "2b1cec644957"
down_revision: str | Sequence[str] | None = "0eae9be5122f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
