"""Initial database schema with ALL tables and ENUM types

Revision ID: 86f7456767fd
Revises:
Create Date: 2025-09-24 09:05:10.231641
Updated: 2025-10-13 12:10:00 - Complete schema creation

This migration creates the COMPLETE database schema including:
- All ENUM types
- All base tables
    - All indexes and constraints
    - Seed data for roles and permissions
"""
import logging
from collections.abc import Sequence

from alembic import op

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '86f7456767fd'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create complete database schema using SQLAlchemy metadata."""
    from sqlalchemy import inspect, text

    # Ensure application schema exists
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    op.execute("SET search_path TO app, public")

    # Get connection and inspector
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names(schema='app')

    # Check if schema is already initialized by looking for users table
    if 'users' in existing_tables:
        logger.info(
            f"Schema already initialized (found {len(existing_tables)} tables), "
            "skipping creation"
        )
        return

    logger.info("Creating complete database schema...")

    # Import all models to register them with SQLAlchemy
    import app.models  # noqa: F401
    from app.db.base_class import Base

    # Create ALL tables using SQLAlchemy metadata
    # This will create all ENUMs and tables in the correct order
    logger.info("Creating all tables and ENUM types...")

    # Exclude alembic_version from metadata (it's managed by Alembic itself)
    tables_to_create = [
        table for table in Base.metadata.sorted_tables
        if table.name != 'alembic_version'
    ]

    # Create tables with error handling for concurrent creation
    created_count = 0
    skipped_count = 0

    for table in tables_to_create:
        try:
            # Check if table already exists (in case of race condition)
            result = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'app' AND table_name = :table_name"
            ), {"table_name": table.name})
            if result.scalar() > 0:
                skipped_count += 1
                continue

            table.create(bind=conn, checkfirst=True)
            created_count += 1
        except Exception as e:
            # If table already exists due to race condition, skip it
            if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                skipped_count += 1
                logger.info(f"Table {table.name} already exists, skipping...")
                continue
            else:
                # Re-raise unexpected errors
                raise

    logger.info(
        f"Created {created_count} tables successfully! "
        f"(Skipped {skipped_count} existing tables)"
    )

    # Seed base roles and permissions
    logger.info("Seeding initial data...")
    op.execute(
        """
        INSERT INTO app.roles (name, description, is_system_role, created_at, updated_at)
        VALUES ('admin', 'Administrator with full access', true, now(), now())
        ON CONFLICT (name) DO NOTHING
        """
    )

    op.execute(
        """
        INSERT INTO app.permissions (name, description, created_at, updated_at)
        VALUES
            ('users:read', 'View user accounts', now(), now()),
            ('users:write', 'Create and update user accounts', now(), now()),
            ('users:delete', 'Delete user accounts', now(), now()),
            ('roles:read', 'View roles and permissions', now(), now()),
            ('roles:write', 'Create and update roles and permissions', now(), now()),
            ('roles:delete', 'Delete roles and permissions', now(), now())
        ON CONFLICT (name) DO NOTHING
        """
    )
    logger.info("Initial data seeded successfully!")


def downgrade() -> None:
    """Downgrade schema by dropping ALL tables."""
    # Import models to get metadata
    import app.models  # noqa: F401
    from app.db.base_class import Base

    conn = op.get_bind()

    # Drop all tables using SQLAlchemy metadata
    logger.info("Dropping all tables...")
    Base.metadata.drop_all(bind=conn)
    logger.info("All tables dropped successfully!")

    # Note: We don't drop the schema itself to prevent accidental data loss
