"""add_missing_supplier_columns

Revision ID: 14b0e514876f
Revises: perf_idx_20251010
Create Date: 2025-10-10 17:04:16.352982

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '14b0e514876f'
down_revision: str | Sequence[str] | None = 'perf_idx_20251010'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add missing columns to suppliers table
    op.add_column('suppliers', sa.Column('code', sa.String(length=20), nullable=True), schema='app')
    op.add_column('suppliers', sa.Column('address', sa.Text(), nullable=True), schema='app')
    op.add_column('suppliers', sa.Column('city', sa.String(length=50), nullable=True), schema='app')
    op.add_column('suppliers', sa.Column('tax_id', sa.String(length=50), nullable=True), schema='app')

    # Create indexes for the new columns
    op.create_index(op.f('ix_app_suppliers_code'), 'suppliers', ['code'], unique=True, schema='app')


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes first
    op.drop_index(op.f('ix_app_suppliers_code'), table_name='suppliers', schema='app')

    # Drop columns
    op.drop_column('suppliers', 'tax_id', schema='app')
    op.drop_column('suppliers', 'city', schema='app')
    op.drop_column('suppliers', 'address', schema='app')
    op.drop_column('suppliers', 'code', schema='app')
