"""Add eliminated_suggestions table

Revision ID: 20251021_add_eliminated_suggestions
Revises: 20251020_add_emag_price_columns
Create Date: 2025-10-21 17:35:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20251021_eliminated_suggest'
down_revision: str | None = '20251021_add_price_fields'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add eliminated_suggestions table to track manually eliminated product suggestions."""

    # Create eliminated_suggestions table
    op.create_table(
        'eliminated_suggestions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('supplier_product_id', sa.Integer(), nullable=False),
        sa.Column('local_product_id', sa.Integer(), nullable=False),
        sa.Column('eliminated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('eliminated_by', sa.Integer(), nullable=True),
        sa.Column('reason', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['supplier_product_id'], ['supplier_products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['local_product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['eliminated_by'], ['users.id'], ondelete='SET NULL'),
    )

    # Create indexes for better query performance
    op.create_index(
        'ix_eliminated_suggestions_supplier_product_id',
        'eliminated_suggestions',
        ['supplier_product_id']
    )
    op.create_index(
        'ix_eliminated_suggestions_local_product_id',
        'eliminated_suggestions',
        ['local_product_id']
    )
    op.create_index(
        'ix_eliminated_suggestions_eliminated_at',
        'eliminated_suggestions',
        ['eliminated_at']
    )

    # Create unique constraint to prevent duplicate eliminations
    op.create_unique_constraint(
        'uq_eliminated_suggestions_supplier_local',
        'eliminated_suggestions',
        ['supplier_product_id', 'local_product_id']
    )


def downgrade() -> None:
    """Remove eliminated_suggestions table."""

    # Drop indexes
    op.drop_index('ix_eliminated_suggestions_eliminated_at', table_name='eliminated_suggestions')
    op.drop_index('ix_eliminated_suggestions_local_product_id', table_name='eliminated_suggestions')
    op.drop_index('ix_eliminated_suggestions_supplier_product_id', table_name='eliminated_suggestions')

    # Drop unique constraint
    op.drop_constraint('uq_eliminated_suggestions_supplier_local', 'eliminated_suggestions', type_='unique')

    # Drop table
    op.drop_table('eliminated_suggestions')
