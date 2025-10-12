"""add_manual_reorder_quantity_to_inventory_items

Revision ID: eef6ff065ce9
Revises: 20251011_enhanced_po_adapted
Create Date: 2025-10-13 01:11:09.596559

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'eef6ff065ce9'
down_revision: str | Sequence[str] | None = '20251011_enhanced_po_adapted'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add manual_reorder_quantity column to inventory_items table
    op.add_column(
        'inventory_items',
        sa.Column('manual_reorder_quantity', sa.Integer(), nullable=True),
        schema='app'
    )

    # Add comment to explain the column
    op.execute("""
        COMMENT ON COLUMN app.inventory_items.manual_reorder_quantity IS
        'Manual override for reorder quantity. If set, this value takes precedence over automatic calculation.'
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove manual_reorder_quantity column
    op.drop_column('inventory_items', 'manual_reorder_quantity', schema='app')
