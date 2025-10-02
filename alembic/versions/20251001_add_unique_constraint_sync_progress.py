"""Add unique constraint to emag_sync_progress.sync_log_id

Revision ID: 20251001_add_unique_constraint_sync_progress
Revises: 20250929_add_enhanced_emag_models
Create Date: 2025-10-01 19:56:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251001_add_unique_constraint_sync_progress"
down_revision = "20250929_add_enhanced_emag_models"
branch_labels = None
depends_on = None


def upgrade():
    """Add unique constraint on sync_log_id for ON CONFLICT support."""
    
    # Add unique constraint to sync_log_id
    op.create_unique_constraint(
        "uq_emag_sync_progress_sync_log_id",
        "emag_sync_progress",
        ["sync_log_id"]
    )


def downgrade():
    """Remove unique constraint on sync_log_id."""
    
    # Drop unique constraint
    op.drop_constraint(
        "uq_emag_sync_progress_sync_log_id",
        "emag_sync_progress",
        type_="unique"
    )
