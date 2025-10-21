"""Fix emag_sync_logs account_type constraint to include 'both'

Revision ID: 20251013_fix_account_type
Revises: 20251013_fix_all_tz
Create Date: 2025-10-13 18:45:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '20251013_fix_account_type'
down_revision = '20251013_fix_all_tz'
branch_labels = None
depends_on = None


def upgrade():
    """
    Update the check constraint on emag_sync_logs.account_type to include 'both'
    """
    # Drop the old constraint
    op.drop_constraint(
        'ck_emag_sync_logs_account_type',
        'emag_sync_logs',
        schema='app',
        type_='check'
    )

    # Create the new constraint with 'both' included
    op.create_check_constraint(
        'ck_emag_sync_logs_account_type',
        'emag_sync_logs',
        "account_type IN ('main', 'fbe', 'both')",
        schema='app'
    )


def downgrade():
    """
    Revert the constraint to only allow 'main' and 'fbe'
    """
    # Drop the new constraint
    op.drop_constraint(
        'ck_emag_sync_logs_account_type',
        'emag_sync_logs',
        schema='app',
        type_='check'
    )

    # Recreate the old constraint
    op.create_check_constraint(
        'ck_emag_sync_logs_account_type',
        'emag_sync_logs',
        "account_type IN ('main', 'fbe')",
        schema='app'
    )
