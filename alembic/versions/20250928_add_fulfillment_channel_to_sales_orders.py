"""Add fulfillment_channel to sales_orders

Revision ID: 20250928_add_fulfillment_channel
Revises: 4242d9721c62
Create Date: 2025-09-28 17:50:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250928_add_fulfillment_channel"
down_revision: str | Sequence[str] | None = "4242d9721c62"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add fulfillment_channel column and backfill values."""
    op.execute("SET search_path TO app, public")

    op.add_column(
        "sales_orders",
        sa.Column(
            "fulfillment_channel",
            sa.String(length=20),
            nullable=True,
            server_default="main",
        ),
        schema="app",
    )

    op.execute(
        """
        UPDATE app.sales_orders
        SET fulfillment_channel = CASE
            WHEN external_source ILIKE 'emag:fbe%%' THEN 'fbe'
            WHEN external_source ILIKE 'emag:main%%' THEN 'main'
            WHEN external_source ILIKE 'emag:%%' THEN 'other'
            ELSE 'main'
        END
        WHERE fulfillment_channel IS NULL;
        """
    )

    op.alter_column(
        "sales_orders",
        "fulfillment_channel",
        schema="app",
        type_=sa.String(length=20),
        nullable=False,
        server_default=None,
    )

    op.create_index(
        "ix_sales_orders_fulfillment_channel",
        "sales_orders",
        ["fulfillment_channel"],
        schema="app",
    )


def downgrade() -> None:
    """Remove fulfillment_channel column."""
    op.execute("SET search_path TO app, public")

    op.drop_index(
        "ix_sales_orders_fulfillment_channel",
        table_name="sales_orders",
        schema="app",
    )

    op.drop_column(
        "sales_orders",
        "fulfillment_channel",
        schema="app",
    )
