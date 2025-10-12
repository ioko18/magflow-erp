"""Fix missing columns in emag_products_v2

Revision ID: fix_emag_v2_cols
Revises: add_section8_fields
Create Date: 2025-10-04 19:35:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = 'fix_emag_v2_cols'
down_revision = 'add_section8_fields'
branch_labels = None
depends_on = None


def upgrade():
    """Add missing emag_id column if it doesn't exist."""

    # Check if emag_id column exists, if not add it
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('emag_products_v2')]

    if 'emag_id' not in columns:
        op.add_column('emag_products_v2', sa.Column('emag_id', sa.String(50), nullable=True))
        op.create_index('idx_emag_products_v2_emag_id', 'emag_products_v2', ['emag_id'])

    # Ensure part_number_key exists (should be added by add_section8_fields migration)
    if 'part_number_key' not in columns:
        op.add_column('emag_products_v2', sa.Column('part_number_key', sa.String(50), nullable=True))
        op.create_index('idx_emag_products_v2_part_number_key', 'emag_products_v2', ['part_number_key'])


def downgrade():
    """Remove emag_id column."""

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('emag_products_v2')]

    if 'emag_id' in columns:
        op.drop_index('idx_emag_products_v2_emag_id', table_name='emag_products_v2')
        op.drop_column('emag_products_v2', 'emag_id')
