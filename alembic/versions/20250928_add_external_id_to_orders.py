"""Add external order identifiers

Revision ID: 20250928_add_external_id
Revises:
Create Date: 2025-09-28 09:53:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20250928_add_external_id"
down_revision: Union[str, None] = "f8a938c16fd8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("external_id", sa.String(length=100), nullable=True),
        schema="app",
    )
    op.add_column(
        "orders",
        sa.Column("external_source", sa.String(length=50), nullable=True),
        schema="app",
    )
    op.create_index(
        "ix_orders_external_id",
        "orders",
        ["external_id"],
        unique=False,
        schema="app",
    )
    op.create_unique_constraint(
        "uq_orders_external_source",
        "orders",
        ["external_id", "external_source"],
        schema="app",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_orders_external_source",
        "orders",
        type_="unique",
        schema="app",
    )
    op.drop_index("ix_orders_external_id", table_name="orders", schema="app")
    op.drop_column("orders", "external_source", schema="app")
    op.drop_column("orders", "external_id", schema="app")
