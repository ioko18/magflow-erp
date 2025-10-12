"""add_part_number_key_to_emag_products

Revision ID: 069bd2ae6d01
Revises: 4242d9721c62
Create Date: 2025-09-25 23:43:27.241512

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '069bd2ae6d01'
down_revision: str | Sequence[str] | None = '4242d9721c62'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema by adding part_number_key column to emag_products table."""
    op.execute("SET search_path TO app, public")

    # Add part_number_key column to emag_products table
    op.add_column(
        "emag_products",
        sa.Column("part_number_key", sa.String(length=50), nullable=True),
        schema="app"
    )

    # Create index for the new column
    op.create_index("ix_emag_products_part_number_key", "emag_products", ["part_number_key"], schema="app")


def downgrade() -> None:
    """Downgrade schema by removing part_number_key column from emag_products table."""
    op.execute("SET search_path TO app, public")

    # Drop index first
    op.drop_index("ix_emag_products_part_number_key", table_name="emag_products", schema="app")

    # Remove the column
    op.drop_column("emag_products", "part_number_key", schema="app")
