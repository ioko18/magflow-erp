"""Merge multiple migration heads

Revision ID: 9986388d397d
Revises: add_emag_reference_data, add_invoice_names, add_section8_fields, supplier_matching_001, create_product_mapping
Create Date: 2025-10-01 15:19:51.451169

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9986388d397d'
down_revision: Union[str, Sequence[str], None] = ('add_emag_reference_data', 'add_invoice_names', 'add_section8_fields', 'supplier_matching_001', 'create_product_mapping')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
