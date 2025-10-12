"""create product mapping tables

Revision ID: create_product_mapping
Revises: 20251001_034500
Create Date: 2025-10-01 10:55:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = 'create_product_mapping'
down_revision = '20251001_034500'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create product_mappings table
    op.create_table(
        'product_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('local_sku', sa.String(length=100), nullable=False),
        sa.Column('local_product_name', sa.String(length=500), nullable=False),
        sa.Column('local_price', sa.Float(), nullable=True),
        sa.Column('emag_main_id', sa.Integer(), nullable=True),
        sa.Column('emag_main_part_number', sa.String(length=100), nullable=True),
        sa.Column('emag_main_status', sa.String(length=50), nullable=True),
        sa.Column('emag_fbe_id', sa.Integer(), nullable=True),
        sa.Column('emag_fbe_part_number', sa.String(length=100), nullable=True),
        sa.Column('emag_fbe_status', sa.String(length=50), nullable=True),
        sa.Column('mapping_confidence', sa.Float(), nullable=True),
        sa.Column('mapping_method', sa.String(length=50), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('google_sheet_row', sa.Integer(), nullable=True),
        sa.Column('google_sheet_data', sa.Text(), nullable=True),
        sa.Column('last_imported_at', sa.DateTime(), nullable=True),
        sa.Column('import_source', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('has_conflicts', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('local_sku', name='uq_product_mapping_local_sku'),
        schema='app'
    )

    # Create indexes
    op.create_index('ix_product_mappings_local_sku', 'product_mappings', ['local_sku'], schema='app')
    op.create_index('ix_product_mappings_emag_main_id', 'product_mappings', ['emag_main_id'], schema='app')
    op.create_index('ix_product_mappings_emag_fbe_id', 'product_mappings', ['emag_fbe_id'], schema='app')

    # Create import_logs table
    op.create_table(
        'import_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('import_type', sa.String(length=50), nullable=False),
        sa.Column('source_name', sa.String(length=200), nullable=False),
        sa.Column('total_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_imports', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_imports', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('skipped_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('auto_mapped_main', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('auto_mapped_fbe', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('unmapped_products', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='in_progress'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('initiated_by', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        schema='app'
    )

    # Create indexes for import_logs
    op.create_index('ix_import_logs_started_at', 'import_logs', ['started_at'], schema='app')
    op.create_index('ix_import_logs_status', 'import_logs', ['status'], schema='app')


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_import_logs_status', table_name='import_logs', schema='app')
    op.drop_index('ix_import_logs_started_at', table_name='import_logs', schema='app')
    op.drop_index('ix_product_mappings_emag_fbe_id', table_name='product_mappings', schema='app')
    op.drop_index('ix_product_mappings_emag_main_id', table_name='product_mappings', schema='app')
    op.drop_index('ix_product_mappings_local_sku', table_name='product_mappings', schema='app')

    # Drop tables
    op.drop_table('import_logs', schema='app')
    op.drop_table('product_mappings', schema='app')
