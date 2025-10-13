"""fix_all_timezone_columns

Revision ID: 20251013_fix_all_tz
Revises: 20251010_add_auxiliary
Create Date: 2025-10-13 04:10:00.000000

This migration consolidates timezone fixes for multiple tables:
- import_logs (started_at, completed_at)
- product_mappings (last_imported_at)
- product_supplier_sheets (price_updated_at, last_imported_at, verified_at, created_at, updated_at)

Note: Now follows 20251010_add_auxiliary which consolidated audit_logs and product relationships tables.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20251013_fix_all_tz'
down_revision: str | Sequence[str] | None = '20251010_add_auxiliary'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Convert datetime columns to TIMESTAMP WITH TIME ZONE for multiple tables."""
    conn = op.get_bind()

    # Define tables and their columns to convert
    tables_columns = {
        'import_logs': ['started_at', 'completed_at'],
        'product_mappings': ['last_imported_at'],
        'product_supplier_sheets': [
            'price_updated_at',
            'last_imported_at',
            'verified_at',
            'created_at',
            'updated_at'
        ]
    }

    # Process each table and its columns
    for table_name, columns in tables_columns.items():
        for column_name in columns:
            # Check if column exists and needs conversion
            result = conn.execute(sa.text("""
                SELECT data_type FROM information_schema.columns
                WHERE table_schema = 'app'
                  AND table_name = :table_name
                  AND column_name = :column_name
            """), {"table_name": table_name, "column_name": column_name}).scalar()

            if result and 'without time zone' in result.lower():
                # Convert to TIMESTAMP WITH TIME ZONE
                op.execute(sa.text(f"""
                    ALTER TABLE app.{table_name}
                    ALTER COLUMN {column_name} TYPE TIMESTAMP WITH TIME ZONE
                    USING {column_name} AT TIME ZONE 'UTC'
                """))
                print(f"✅ Converted {table_name}.{column_name} to TIMESTAMP WITH TIME ZONE")
            elif result:
                print(f"⏭️  Skipped {table_name}.{column_name} (already TIMESTAMP WITH TIME ZONE)")
            else:
                print(f"⚠️  Column {table_name}.{column_name} not found")


def downgrade() -> None:
    """Revert datetime columns to TIMESTAMP WITHOUT TIME ZONE."""

    # Revert import_logs columns
    op.execute("""
        ALTER TABLE app.import_logs
        ALTER COLUMN started_at TYPE TIMESTAMP WITHOUT TIME ZONE
        USING started_at AT TIME ZONE 'UTC'
    """)

    op.execute("""
        ALTER TABLE app.import_logs
        ALTER COLUMN completed_at TYPE TIMESTAMP WITHOUT TIME ZONE
        USING completed_at AT TIME ZONE 'UTC'
    """)

    # Revert product_mappings columns
    op.execute("""
        ALTER TABLE app.product_mappings
        ALTER COLUMN last_imported_at TYPE TIMESTAMP WITHOUT TIME ZONE
        USING last_imported_at AT TIME ZONE 'UTC'
    """)

    # Revert product_supplier_sheets columns
    columns = ['price_updated_at', 'last_imported_at', 'verified_at', 'created_at', 'updated_at']
    for column in columns:
        op.execute(f"""
            ALTER TABLE app.product_supplier_sheets
            ALTER COLUMN {column} TYPE TIMESTAMP WITHOUT TIME ZONE
            USING {column} AT TIME ZONE 'UTC'
        """)
