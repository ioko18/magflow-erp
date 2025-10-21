"""Add supplier_id to product_supplier_sheets

Revision ID: 20251020_add_supplier_id
Revises: 72ba0528563c
Create Date: 2025-10-20 23:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251020_add_supplier_id'
down_revision = '72ba0528563c'
branch_labels = None
depends_on = None


def upgrade():
    # Add supplier_id column (nullable for now)
    op.add_column('product_supplier_sheets', 
        sa.Column('supplier_id', sa.Integer(), nullable=True),
        schema='app'
    )
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_product_supplier_sheets_supplier_id',
        'product_supplier_sheets', 'suppliers',
        ['supplier_id'], ['id'],
        source_schema='app', referent_schema='app',
        ondelete='SET NULL'
    )
    
    # Create index for better query performance
    op.create_index(
        'ix_product_supplier_sheets_supplier_id',
        'product_supplier_sheets',
        ['supplier_id'],
        schema='app'
    )
    
    # Migrate existing data: match supplier_name to supplier.name
    # This will set supplier_id for existing records where we can find a match
    op.execute("""
        UPDATE app.product_supplier_sheets pss
        SET supplier_id = s.id
        FROM app.suppliers s
        WHERE pss.supplier_name ILIKE s.name
        AND pss.supplier_id IS NULL
    """)


def downgrade():
    op.drop_index('ix_product_supplier_sheets_supplier_id', 
                  table_name='product_supplier_sheets', schema='app')
    op.drop_constraint('fk_product_supplier_sheets_supplier_id', 
                      'product_supplier_sheets', schema='app', type_='foreignkey')
    op.drop_column('product_supplier_sheets', 'supplier_id', schema='app')
