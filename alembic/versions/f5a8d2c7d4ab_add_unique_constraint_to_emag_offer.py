"""Add composite unique constraint for eMAG offers per account type

Revision ID: f5a8d2c7d4ab
Revises: 9a5e6b199c94
Create Date: 2025-09-26 08:46:00.000000
"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f5a8d2c7d4ab"
down_revision: str | Sequence[str] | None = "9a5e6b199c94"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema by enforcing unique offers per account type."""
    op.execute("SET search_path TO app, public")

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'emag_product_offers_emag_offer_id_key'
                  AND conrelid = 'app.emag_product_offers'::regclass
            ) THEN
                ALTER TABLE app.emag_product_offers
                DROP CONSTRAINT emag_product_offers_emag_offer_id_key;
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_emag_product_offers_offer_id_account_type'
                  AND conrelid = 'app.emag_product_offers'::regclass
            ) THEN
                ALTER TABLE app.emag_product_offers
                ADD CONSTRAINT uq_emag_product_offers_offer_id_account_type
                UNIQUE (emag_offer_id, account_type);
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    """Downgrade schema by reverting to legacy unique constraint."""
    op.execute("SET search_path TO app, public")

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_emag_product_offers_offer_id_account_type'
                  AND conrelid = 'app.emag_product_offers'::regclass
            ) THEN
                ALTER TABLE app.emag_product_offers
                DROP CONSTRAINT uq_emag_product_offers_offer_id_account_type;
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'emag_product_offers_emag_offer_id_key'
                  AND conrelid = 'app.emag_product_offers'::regclass
            ) THEN
                ALTER TABLE app.emag_product_offers
                ADD CONSTRAINT emag_product_offers_emag_offer_id_key
                UNIQUE (emag_offer_id);
            END IF;
        END
        $$;
        """
    )
