"""add_part_number_key_to_emag_product_offers

Revision ID: 9a5e6b199c94
Revises: 069bd2ae6d01
Create Date: 2025-09-25 23:45:26.136664

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a5e6b199c94'
down_revision: Union[str, Sequence[str], None] = '069bd2ae6d01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema by adding part_number_key column to emag_product_offers table."""
    op.execute("SET search_path TO app, public")

    # Add part_number_key column to emag_product_offers table
    op.add_column(
        "emag_product_offers",
        sa.Column("part_number_key", sa.String(length=50), nullable=True),
        schema="app"
    )

    # Create index for the new column
    op.create_index("ix_emag_product_offers_part_number_key", "emag_product_offers", ["part_number_key"], schema="app")


def downgrade() -> None:
    """Downgrade schema by removing part_number_key column from emag_product_offers table."""
    op.execute("SET search_path TO app, public")

    # Drop index first
    op.drop_index("ix_emag_product_offers_part_number_key", table_name="emag_product_offers", schema="app")

    # Remove the column
    op.drop_column("emag_product_offers", "part_number_key", schema="app")
