"""Add exchange_rate and calculated_price_ron to supplier_products

Revision ID: 20251021_add_price_fields
Revises: 20251020_add_supplier_id
Create Date: 2025-10-21 00:30:00.000000

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = '20251021_add_price_fields'
down_revision = '20251020_add_supplier_id'
branch_labels = None
depends_on = None


def upgrade():
    # Add exchange_rate column
    op.add_column('supplier_products',
        sa.Column('exchange_rate', sa.Float(), nullable=True, comment='Exchange rate CNY to RON'),
        schema='app'
    )

    # Add calculated_price_ron column
    op.add_column('supplier_products',
        sa.Column('calculated_price_ron', sa.Float(), nullable=True, comment='Calculated price in RON using exchange rate'),
        schema='app'
    )

    # Calculate initial values for existing records (assuming default exchange rate of 0.65)
    op.execute("""
        UPDATE app.supplier_products
        SET exchange_rate = 0.65,
            calculated_price_ron = supplier_price * 0.65
        WHERE exchange_rate IS NULL
        AND supplier_currency = 'CNY'
    """)


def downgrade():
    op.drop_column('supplier_products', 'calculated_price_ron', schema='app')
    op.drop_column('supplier_products', 'exchange_rate', schema='app')
