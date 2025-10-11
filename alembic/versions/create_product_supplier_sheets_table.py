"""create product supplier sheets table

Revision ID: create_supplier_sheets
Revises: add_notification_tables_v2
Create Date: 2025-10-04 20:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'create_supplier_sheets'
down_revision = 'add_notification_tables_v2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create product_supplier_sheets table
    op.create_table(
        'product_supplier_sheets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=False),
        sa.Column('supplier_name', sa.String(length=255), nullable=False),
        sa.Column('price_cny', sa.Float(), nullable=False),
        sa.Column('supplier_contact', sa.String(length=255), nullable=True),
        sa.Column('supplier_url', sa.String(length=1000), nullable=True),
        sa.Column('supplier_notes', sa.Text(), nullable=True),
        sa.Column('price_updated_at', sa.DateTime(), nullable=True),
        sa.Column('exchange_rate_cny_ron', sa.Float(), nullable=True),
        sa.Column('calculated_price_ron', sa.Float(), nullable=True),
        sa.Column('google_sheet_row', sa.Integer(), nullable=True),
        sa.Column('last_imported_at', sa.DateTime(), nullable=True),
        sa.Column('import_source', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_preferred', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('verified_by', sa.String(length=100), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sku', 'supplier_name', name='uq_product_supplier_sku_name'),
        schema='app'
    )
    
    # Create indexes
    op.create_index('ix_product_supplier_sheets_sku', 'product_supplier_sheets', ['sku'], schema='app')
    op.create_index('ix_product_supplier_sheets_supplier_name', 'product_supplier_sheets', ['supplier_name'], schema='app')
    op.create_index('ix_product_supplier_sheets_is_active', 'product_supplier_sheets', ['is_active'], schema='app')


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_product_supplier_sheets_is_active', table_name='product_supplier_sheets', schema='app')
    op.drop_index('ix_product_supplier_sheets_supplier_name', table_name='product_supplier_sheets', schema='app')
    op.drop_index('ix_product_supplier_sheets_sku', table_name='product_supplier_sheets', schema='app')
    
    # Drop table
    op.drop_table('product_supplier_sheets', schema='app')
