"""merge_heads_for_emag_v2

Revision ID: 0eae9be5122f
Revises: 20250928_add_fulfillment_channel, 20250929_add_enhanced_emag_models, f5a8d2c7d4ab
Create Date: 2025-09-29 17:08:21.921291

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "0eae9be5122f"
down_revision: str | Sequence[str] | None = (
    "20250928_add_fulfillment_channel",
    "20250929_add_enhanced_emag_models",
    "f5a8d2c7d4ab",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
