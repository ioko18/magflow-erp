"""
Database Schema Validation Module for MagFlow ERP

This module provides utilities to validate database schema requirements
before running sync operations, preventing runtime errors and providing
helpful error messages.
"""

import logging

from sqlalchemy import inspect, text

logger = logging.getLogger(__name__)


class SchemaValidator:
    """Validates database schema for sync operations."""

    # Required columns for each table used in sync operations
    REQUIRED_COLUMNS = {
        "orders": {
            "id",
            "customer_id",
            "order_date",
            "status",
            "total_amount",
            "external_id",
            "external_source",
            "created_at",
            "updated_at",
        },
        "order_lines": {"id", "order_id", "product_id", "quantity", "unit_price"},
        "products": {"id", "name", "sku", "base_price", "is_active"},
        "emag_products": {
            "id",
            "emag_id",
            "name",
            "characteristics",
            "images",
            "is_active",
        },
        "emag_product_offers": {
            "id",
            "emag_product_id",
            "emag_offer_id",
            "price",
            "stock",
            "account_type",
        },
        "emag_offer_syncs": {
            "id",
            "sync_id",
            "account_type",
            "status",
            "total_offers_processed",
            "created_at",
        },
    }

    def __init__(self, async_session_factory):
        self.async_session_factory = async_session_factory

    async def validate_schema(self) -> dict[str, list[str]]:
        """
        Validate that all required columns exist in the database tables.

        Returns:
            Dict mapping table names to lists of missing columns
        """
        missing_columns = {}

        try:
            # Create a sync engine for inspection (since inspect() doesn't work with async engines)
            from sqlalchemy import create_engine

            from app.core.config import settings

            sync_engine = create_engine(
                settings.DB_URI.replace("postgresql+asyncpg", "postgresql")
            )
            inspector = inspect(sync_engine)

            for table_name, required_columns in self.REQUIRED_COLUMNS.items():
                try:
                    # Get existing columns for this table (with schema prefix)
                    existing_columns = inspector.get_columns(table_name, schema="app")
                    existing_column_names = {col["name"] for col in existing_columns}

                    # Find missing columns
                    missing = required_columns - existing_column_names
                    if missing:
                        missing_columns[table_name] = list(missing)
                        logger.error(f"Missing columns in {table_name}: {missing}")

                except Exception as e:
                    logger.error(f"Error checking columns for table {table_name}: {e}")
                    missing_columns[table_name] = [f"Error checking table: {str(e)}"]

        except Exception as e:
            logger.error(f"Error creating database inspector: {e}")
            # Return all columns as missing if we can't check
            for table_name in self.REQUIRED_COLUMNS:
                missing_columns[table_name] = list(self.REQUIRED_COLUMNS[table_name])

        return missing_columns

    async def validate_sync_requirements(self) -> dict[str, any]:
        """
        Validate all requirements for sync operations.

        Returns:
            Dict with validation results and error messages
        """
        async with self.async_session_factory() as session:
            validation_results = {
                "schema_valid": True,
                "missing_columns": {},
                "errors": [],
                "warnings": [],
            }

            try:
                # Check schema
                missing_columns = await self.validate_schema()
                if missing_columns:
                    validation_results["schema_valid"] = False
                    validation_results["missing_columns"] = missing_columns
                    validation_results["errors"].append(
                        f"Missing required columns in {len(missing_columns)} tables"
                    )

                # Check if we can execute basic queries
                try:
                    result = await session.execute(text("SELECT 1"))
                    if not result.scalar():
                        validation_results["warnings"].append("Basic query test failed")
                except Exception as e:
                    validation_results["errors"].append(
                        f"Database connectivity issue: {e}"
                    )

                # Check if required environment variables are set using settings
                from app.core.config import settings

                required_env_vars = [
                    "EMAG_USERNAME_FBE",
                    "EMAG_PASSWORD_FBE",
                    "EMAG_USERNAME",
                    "EMAG_PASSWORD",
                ]
                missing_env_vars = []
                for var in required_env_vars:
                    # Get the value from settings (which loads from .env file)
                    setting_value = getattr(settings, var, None)
                    if not setting_value:
                        missing_env_vars.append(var)

                if missing_env_vars:
                    validation_results["warnings"].append(
                        f"Missing environment variables: {missing_env_vars}"
                    )

            except Exception as e:
                validation_results["errors"].append(f"Validation failed: {e}")
                validation_results["schema_valid"] = False

        return validation_results

    def generate_migration_suggestions(
        self, missing_columns: dict[str, list[str]]
    ) -> str:
        """
        Generate SQL migration suggestions for missing columns.

        Args:
            missing_columns: Dict mapping table names to missing column lists

        Returns:
            String containing SQL migration suggestions
        """
        suggestions = []
        suggestions.append("-- Migration suggestions for missing columns")
        suggestions.append("-- Run these commands to add missing columns:")
        suggestions.append("")

        for table_name, missing_cols in missing_columns.items():
            for col in missing_cols:
                if col == "external_id":
                    suggestions.append(
                        f"ALTER TABLE {table_name} ADD COLUMN external_id VARCHAR(255);"
                    )
                elif col == "external_source":
                    suggestions.append(
                        f"ALTER TABLE {table_name} ADD COLUMN external_source VARCHAR(50);"
                    )
                elif col in ["created_at", "updated_at"]:
                    suggestions.append(
                        f"ALTER TABLE {table_name} ADD COLUMN {col} TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
                    )
                else:
                    suggestions.append(
                        f"ALTER TABLE {table_name} ADD COLUMN {col} TEXT;"
                    )

        return "\n".join(suggestions)


async def validate_sync_environment(async_session_factory) -> dict[str, any]:
    """
    Validate the environment and database schema for sync operations.

    Args:
        async_session_factory: SQLAlchemy async session factory

    Returns:
        Dict with validation results
    """
    validator = SchemaValidator(async_session_factory)
    return await validator.validate_sync_requirements()


def print_validation_report(validation_results: dict[str, any]) -> None:
    """
    Print a formatted validation report.

    Args:
        validation_results: Results from validate_sync_requirements
    """
    logger.info("=" * 60)
    logger.info("Database Schema Validation Report")
    logger.info("=" * 60)

    if validation_results["schema_valid"]:
        logger.info("✅ Database schema is valid for sync operations")
    else:
        logger.error("❌ Database schema validation failed")
        logger.error("Missing columns:")
        for table, columns in validation_results["missing_columns"].items():
            logger.error(f"  {table}: {', '.join(columns)}")

    if validation_results["errors"]:
        logger.error("❌ Errors:")
        for error in validation_results["errors"]:
            logger.error(f"  • {error}")

    if validation_results["warnings"]:
        logger.warning("⚠️  Warnings:")
        for warning in validation_results["warnings"]:
            logger.warning(f"  • {warning}")

    # Generate migration suggestions if there are missing columns
    if validation_results["missing_columns"]:
        validator = SchemaValidator(None)  # We don't need a session for this
        suggestions = validator.generate_migration_suggestions(
            validation_results["missing_columns"]
        )
        logger.info(f"💡 Migration suggestions:\n{suggestions}")

    logger.info("=" * 60)
