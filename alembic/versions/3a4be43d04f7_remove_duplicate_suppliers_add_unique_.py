"""remove_duplicate_suppliers_add_unique_constraint

Revision ID: 3a4be43d04f7
Revises: 1bf2989cb727
Create Date: 2025-10-03 00:40:59.359371

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '3a4be43d04f7'
down_revision: str | Sequence[str] | None = '4242d9721c62'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Delete duplicate supplier_products entries
    # Keep only the one with the lowest ID for each (supplier_id, local_product_id) pair
    op.execute("""
        DELETE FROM app.supplier_products
        WHERE id IN (
            SELECT sp.id
            FROM app.supplier_products sp
            INNER JOIN (
                SELECT supplier_id, local_product_id, MIN(id) as min_id
                FROM app.supplier_products
                GROUP BY supplier_id, local_product_id
                HAVING COUNT(*) > 1
            ) duplicates
            ON sp.supplier_id = duplicates.supplier_id
            AND sp.local_product_id = duplicates.local_product_id
            AND sp.id != duplicates.min_id
        )
    """)

    # Step 2: Add UNIQUE constraint to prevent future duplicates
    op.create_unique_constraint(
        'uq_supplier_products_supplier_product',
        'supplier_products',
        ['supplier_id', 'local_product_id'],
        schema='app'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove the unique constraint
    op.drop_constraint(
        'uq_supplier_products_supplier_product',
        'supplier_products',
        schema='app',
        type_='unique'
    )
