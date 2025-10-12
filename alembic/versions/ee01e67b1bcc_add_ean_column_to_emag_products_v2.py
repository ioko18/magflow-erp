"""add_ean_column_to_emag_products_v2

Revision ID: ee01e67b1bcc
Revises: 10a0b733b02b
Create Date: 2025-10-01 16:43:20.405979

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ee01e67b1bcc'
down_revision: str | Sequence[str] | None = '10a0b733b02b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add ean column to emag_products_v2 table
    op.execute("""
        ALTER TABLE emag_products_v2
        ADD COLUMN IF NOT EXISTS ean JSONB
    """)

    # Create index on ean column for fast lookups
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_emag_products_ean
        ON emag_products_v2 USING gin (ean)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove index
    op.execute("DROP INDEX IF EXISTS idx_emag_products_ean")

    # Remove column
    op.execute("ALTER TABLE emag_products_v2 DROP COLUMN IF EXISTS ean")
