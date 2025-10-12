"""Add metadata column to emag product offers

Revision ID: b1234f5d6c78
Revises: 6d303f2068d4
Create Date: 2025-09-25 07:24:20.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1234f5d6c78"
down_revision: str | Sequence[str] | None = "6d303f2068d4"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    has_column = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = :schema
                  AND table_name = :table
                  AND column_name = :column
            )
            """
        ),
        {"schema": "app", "table": "emag_product_offers", "column": "metadata"},
    ).scalar()

    if not has_column:
        op.add_column(
            "emag_product_offers",
            sa.Column(
                "metadata",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            schema="app",
        )


def downgrade() -> None:
    conn = op.get_bind()
    has_column = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = :schema
                  AND table_name = :table
                  AND column_name = :column
            )
            """
        ),
        {"schema": "app", "table": "emag_product_offers", "column": "metadata"},
    ).scalar()

    if has_column:
        op.drop_column("emag_product_offers", "metadata", schema="app")
