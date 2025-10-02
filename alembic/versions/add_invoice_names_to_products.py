"""add invoice names to products

Revision ID: add_invoice_names
Revises: 
Create Date: 2025-10-01 15:05:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_invoice_names'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add invoice_name_ro and invoice_name_en columns to products table."""
    op.add_column('products', 
        sa.Column('invoice_name_ro', sa.String(200), nullable=True,
                  comment='Product name for Romanian invoices (shorter, customs-friendly)'),
        schema='app'
    )
    op.add_column('products', 
        sa.Column('invoice_name_en', sa.String(200), nullable=True,
                  comment='Product name for English invoices (customs declarations, VAT)'),
        schema='app'
    )


def downgrade():
    """Remove invoice name columns."""
    op.drop_column('products', 'invoice_name_ro', schema='app')
    op.drop_column('products', 'invoice_name_en', schema='app')
