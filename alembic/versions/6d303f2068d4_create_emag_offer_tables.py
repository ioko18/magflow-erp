"""create emag offer tables

Revision ID: 6d303f2068d4
Revises: 1519392e1e24
Create Date: 2025-09-25 06:44:43.863580
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "6d303f2068d4"
down_revision: Union[str, Sequence[str], None] = "1519392e1e24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSONB_EMPTY_OBJECT = sa.text("'{}'::jsonb")
JSONB_EMPTY_ARRAY = sa.text("'[]'::jsonb")
NOW = sa.text("now()")


def upgrade() -> None:
    """Upgrade schema by creating eMAG offer-related tables."""
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    op.execute("SET search_path TO app, public")

    # Products table
    op.create_table(
        "emag_products",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("emag_id", sa.String(length=100), nullable=False, unique=True),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("part_number", sa.String(length=100), nullable=True),
        sa.Column("emag_category_id", sa.Integer(), nullable=True),
        sa.Column("emag_brand_id", sa.Integer(), nullable=True),
        sa.Column("emag_category_name", sa.String(length=255), nullable=True),
        sa.Column("emag_brand_name", sa.String(length=255), nullable=True),
        sa.Column("characteristics", JSONB, server_default=JSONB_EMPTY_OBJECT, nullable=False),
        sa.Column("images", JSONB, server_default=JSONB_EMPTY_ARRAY, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_imported_at", sa.DateTime(), nullable=True),
        sa.Column("emag_updated_at", sa.DateTime(), nullable=True),
        sa.Column("raw_data", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=NOW, nullable=False),
        schema="app",
    )

    op.create_index("ix_emag_products_part_number", "emag_products", ["part_number"], schema="app")
    op.create_index("ix_emag_products_category", "emag_products", ["emag_category_id"], schema="app")
    op.create_index("ix_emag_products_brand", "emag_products", ["emag_brand_id"], schema="app")

    # Offers table
    op.create_table(
        "emag_product_offers",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("emag_product_id", sa.String(length=100), nullable=False),
        sa.Column("emag_offer_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("app.emag_products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("sale_price", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default=sa.text("'RON'"), nullable=False),
        sa.Column("stock", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("stock_status", sa.String(length=50), nullable=True),
        sa.Column("handling_time", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("is_available", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_visible", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("vat_rate", sa.Float(), nullable=True),
        sa.Column("vat_included", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=True),
        sa.Column("warehouse_name", sa.String(length=255), nullable=True),
        sa.Column("account_type", sa.String(length=10), server_default=sa.text("'main'"), nullable=False),
        sa.Column("warranty", sa.Integer(), nullable=True),
        sa.Column("last_imported_at", sa.DateTime(), nullable=True),
        sa.Column("emag_updated_at", sa.DateTime(), nullable=True),
        sa.Column("import_batch_id", sa.String(length=100), nullable=True),
        sa.Column("raw_data", JSONB, nullable=True),
        sa.Column("metadata", JSONB, server_default=JSONB_EMPTY_OBJECT, nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=NOW, nullable=False),
        schema="app",
    )

    op.create_index("idx_emag_offer_product", "emag_product_offers", ["emag_product_id"], schema="app")
    op.create_index("idx_emag_offer_status", "emag_product_offers", ["status"], schema="app")
    op.create_index("idx_emag_offer_imported", "emag_product_offers", ["last_imported_at"], schema="app")
    op.create_index("idx_emag_offer_batch", "emag_product_offers", ["import_batch_id"], schema="app")

    # Sync runs table
    op.create_table(
        "emag_offer_syncs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("sync_id", sa.String(length=100), nullable=False, unique=True),
        sa.Column("account_type", sa.String(length=10), server_default=sa.text("'main'"), nullable=False),
        sa.Column("operation_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("total_offers_processed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("offers_created", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("offers_updated", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("offers_failed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("offers_skipped", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("errors", JSONB, server_default=JSONB_EMPTY_ARRAY, nullable=False),
        sa.Column("filters", JSONB, server_default=JSONB_EMPTY_OBJECT, nullable=False),
        sa.Column("initiated_by", sa.String(length=100), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("metadata", JSONB, server_default=JSONB_EMPTY_OBJECT, nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=NOW, nullable=False),
        schema="app",
    )

    op.create_index("idx_emag_sync_status", "emag_offer_syncs", ["status"], schema="app")
    op.create_index("idx_emag_sync_account", "emag_offer_syncs", ["account_type"], schema="app")
    op.create_index("idx_emag_sync_started", "emag_offer_syncs", ["started_at"], schema="app")
    op.create_index("idx_emag_sync_completed", "emag_offer_syncs", ["completed_at"], schema="app")

    # Import conflicts table
    op.create_table(
        "emag_import_conflicts",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("sync_id", sa.String(length=100), sa.ForeignKey("app.emag_offer_syncs.sync_id", ondelete="CASCADE"), nullable=False),
        sa.Column("emag_offer_id", sa.Integer(), nullable=False),
        sa.Column("emag_product_id", sa.String(length=100), nullable=False),
        sa.Column("conflict_type", sa.String(length=50), nullable=False),
        sa.Column("emag_data", JSONB, nullable=False),
        sa.Column("internal_data", JSONB, nullable=True),
        sa.Column("resolution", sa.String(length=50), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata", JSONB, server_default=JSONB_EMPTY_OBJECT, nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=NOW, nullable=False),
        schema="app",
    )

    op.create_index("idx_emag_conflicts_sync", "emag_import_conflicts", ["sync_id"], schema="app")
    op.create_index("idx_emag_conflicts_offer", "emag_import_conflicts", ["emag_offer_id"], schema="app")


def downgrade() -> None:
    """Downgrade schema by dropping eMAG offer tables."""
    op.execute("SET search_path TO app, public")

    op.drop_index("idx_emag_conflicts_offer", table_name="emag_import_conflicts", schema="app")
    op.drop_index("idx_emag_conflicts_sync", table_name="emag_import_conflicts", schema="app")
    op.drop_table("emag_import_conflicts", schema="app")

    op.drop_index("idx_emag_sync_completed", table_name="emag_offer_syncs", schema="app")
    op.drop_index("idx_emag_sync_started", table_name="emag_offer_syncs", schema="app")
    op.drop_index("idx_emag_sync_account", table_name="emag_offer_syncs", schema="app")
    op.drop_index("idx_emag_sync_status", table_name="emag_offer_syncs", schema="app")
    op.drop_table("emag_offer_syncs", schema="app")

    op.drop_index("idx_emag_offer_batch", table_name="emag_product_offers", schema="app")
    op.drop_index("idx_emag_offer_imported", table_name="emag_product_offers", schema="app")
    op.drop_index("idx_emag_offer_status", table_name="emag_product_offers", schema="app")
    op.drop_index("idx_emag_offer_product", table_name="emag_product_offers", schema="app")
    op.drop_constraint("uq_emag_product_offers_offer_id", "emag_product_offers", type_="unique", schema="app")
    op.drop_table("emag_product_offers", schema="app")

    op.drop_index("ix_emag_products_brand", table_name="emag_products", schema="app")
    op.drop_index("ix_emag_products_category", table_name="emag_products", schema="app")
    op.drop_index("ix_emag_products_part_number", table_name="emag_products", schema="app")
    op.drop_table("emag_products", schema="app")
