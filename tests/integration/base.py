"""Base test class for integration tests."""

from typing import Any, Dict, Optional

import pytest
from app.db.base import Base
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


class BaseIntegrationTest:
    """Base class for integration tests with database support."""

    @pytest.fixture(autouse=True)
    async def setup_db(self, db: AsyncSession) -> None:
        """Set up the test database.

        This fixture runs before each test method.
        """
        # Clear all data before each test
        await self._clear_database(db)

        # Additional setup can be done here
        await self._setup_test_data(db)

    async def _clear_database(self, db: AsyncSession) -> None:
        """Clear all data from the database.

        This method drops all data from all tables while keeping the schema.
        """
        # Get all table names
        result = await db.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = :schema
            """,
            {"schema": settings.DB_SCHEMA},
        )
        tables = [row[0] for row in result.fetchall()]

        # Disable triggers to avoid foreign key constraint issues
        await db.execute("SET session_replication_role = 'replica';")

        try:
            # Truncate all tables
            for table in tables:
                await db.execute(
                    f'TRUNCATE TABLE {settings.DB_SCHEMA}."{table}" CASCADE;'
                )

            # Reset sequences
            await db.execute(
                """
                SELECT setval(c.oid, 1, false)
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind = 'S'
                AND n.nspname = :schema
            """,
                {"schema": settings.DB_SCHEMA},
            )

            await db.commit()
        except Exception as e:
            await db.rollback()
            raise e
        finally:
            # Re-enable triggers
            await db.execute("SET session_replication_role = 'origin';")

    async def _setup_test_data(self, db: AsyncSession) -> None:
        """Set up test data for the database.

        This method can be overridden by subclasses to set up test data.
        """

    async def create_test_data(
        self,
        db: AsyncSession,
        model: type[Base],
        data: Dict[str, Any],
        commit: bool = True,
    ) -> Base:
        """Helper method to create test data.

        Args:
            db: Database session
            model: SQLAlchemy model class
            data: Dictionary of data to create the model instance with
            commit: Whether to commit the transaction

        Returns:
            The created model instance

        """
        instance = model(**data)
        db.add(instance)

        if commit:
            await db.commit()
            await db.refresh(instance)

        return instance

    async def get_by_id(
        self,
        db: AsyncSession,
        model: type[Base],
        id: Any,
    ) -> Optional[Base]:
        """Get a model instance by ID.

        Args:
            db: Database session
            model: SQLAlchemy model class
            id: ID of the instance to get

        Returns:
            The model instance if found, None otherwise

        """
        return await db.get(model, id)
