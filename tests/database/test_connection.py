"""
Comprehensive database connection and operations tests.

This module consolidates all database connection tests into a single,
well-organized test suite covering:
- Basic database connectivity
- Connection pool testing
- Session management
- Transaction handling
- Schema operations
- Performance testing
"""

import pytest
import asyncio

from sqlalchemy import text, select, Column, Integer, String, create_engine

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# Test model for connection tests
TestBase = declarative_base()
TestBase.__test__ = False  # Prevent pytest from collecting this as a test class


class ConnectionTestModel(TestBase):
    __tablename__ = "test_connection_table"
    __test__ = False  # Prevent pytest from collecting this as a test class

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    value = Column(Integer)


class TestDatabaseConnection:
    """Comprehensive database connection tests."""

    @pytest.mark.asyncio
    async def test_basic_database_connectivity(self, db_engine):
        """Test basic database connectivity with simple query."""
        async with db_engine.connect() as conn:
            result = await conn.execute(select(1))
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_database_engine_creation(self, db_engine):
        """Test that database engine is properly configured."""
        assert db_engine is not None
        assert hasattr(db_engine, 'pool')

    @pytest.mark.asyncio
    async def test_table_creation_and_cleanup(self, db_engine):
        """Test table creation and cleanup operations."""
        # Create all tables for our test models
        async with db_engine.begin() as conn:
            await conn.run_sync(TestBase.metadata.create_all)

        try:
            # Verify tables exist
            async with db_engine.connect() as conn:
                result = await conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                )
                db_tables = {row[0] for row in result}

            assert "test_connection_table" in db_tables

            # Get metadata table names
            model_table_names = {table.name for table in TestBase.metadata.tables.values()}
            assert len(model_table_names) > 0
        finally:
            # Clean up
            async with db_engine.begin() as conn:
                await conn.run_sync(TestBase.metadata.drop_all)

    @pytest.mark.asyncio
    async def test_crud_operations(self, db_engine):
        """Test basic CRUD operations."""
        # Create all tables
        async with db_engine.begin() as conn:
            await conn.run_sync(TestBase.metadata.create_all)

        # Create session factory
        async_session_factory = async_sessionmaker(
            bind=db_engine, expire_on_commit=False
        )

        async with async_session_factory() as session:
            try:
                # CREATE
                test_item = ConnectionTestModel(name="test_item", value=42)
                session.add(test_item)
                await session.commit()

                # READ
                result = await session.execute(
                    select(ConnectionTestModel).where(ConnectionTestModel.name == "test_item")
                )
                items = result.scalars().all()
                assert len(items) == 1
                assert items[0].name == "test_item"
                assert items[0].value == 42

                # UPDATE
                items[0].name = "updated_item"
                items[0].value = 100
                await session.commit()

                # Verify update
                result = await session.execute(
                    select(ConnectionTestModel).where(ConnectionTestModel.id == test_item.id)
                )
                updated_item = result.scalars().first()
                assert updated_item.name == "updated_item"
                assert updated_item.value == 100

                # DELETE
                await session.delete(updated_item)
                await session.commit()

                # Verify delete
                result = await session.execute(
                    select(ConnectionTestModel).where(ConnectionTestModel.id == test_item.id)
                )
                assert result.scalars().first() is None

            finally:
                await session.close()
                async with db_engine.begin() as conn:
                    await conn.run_sync(TestBase.metadata.drop_all)

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, db_engine):
        """Test transaction rollback functionality."""
        # Create all tables
        async with db_engine.begin() as conn:
            await conn.run_sync(TestBase.metadata.create_all)

        async_session_factory = async_sessionmaker(
            bind=db_engine, expire_on_commit=False, autocommit=False
        )

        try:
            # Create initial item
            async with async_session_factory() as session:
                test_item = ConnectionTestModel(name="test_rollback", value=100)
                session.add(test_item)
                await session.commit()

            # Test rollback
            async with async_session_factory() as session:
                result = await session.execute(
                    select(ConnectionTestModel).where(ConnectionTestModel.name == "test_rollback")
                )
                test_item = result.scalars().first()
                assert test_item is not None

                # Modify and rollback
                test_item.value = 200
                await session.flush()
                assert test_item.value == 200

                await session.rollback()

                # Verify rollback
                await session.refresh(test_item)
                assert test_item.value == 100

                # Clean up
                await session.delete(test_item)
                await session.commit()
        finally:
            async with db_engine.begin() as conn:
                await conn.run_sync(TestBase.metadata.drop_all)

    @pytest.mark.asyncio
    async def test_connection_pool_behavior(self, db_engine):
        """Test connection pool behavior and limits."""
        # Test multiple concurrent connections
        async def create_test_connection():
            async with db_engine.connect() as conn:
                result = await conn.execute(select(1))
                return result.scalar()

        # Run multiple concurrent connections
        tasks = [create_test_connection() for _ in range(5)]
        results = await asyncio.gather(*tasks)

        assert all(result == 1 for result in results)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_session_isolation(self, db_engine):
        """Test that database sessions are properly isolated."""
        # Create all tables
        async with db_engine.begin() as conn:
            await conn.run_sync(TestBase.metadata.create_all)

        async_session_factory = async_sessionmaker(
            bind=db_engine, expire_on_commit=False
        )

        try:
            # Create item in one session
            async with async_session_factory() as session1:
                item1 = ConnectionTestModel(name="session1", value=1)
                session1.add(item1)
                await session1.commit()

            # Verify item exists in another session
            async with async_session_factory() as session2:
                result = await session2.execute(
                    select(ConnectionTestModel).where(ConnectionTestModel.name == "session1")
                )
                item = result.scalars().first()
                assert item is not None
                assert item.value == 1

        finally:
            async with db_engine.begin() as conn:
                await conn.run_sync(TestBase.metadata.drop_all)

    @pytest.mark.asyncio
    async def test_database_settings_configuration(self):
        """Test that database settings are properly configured."""
        # Test database connection settings exist
        assert hasattr(settings, "DB_HOST")
        assert hasattr(settings, "DB_PORT")
        assert hasattr(settings, "DB_NAME")
        assert hasattr(settings, "DB_USER")
        assert hasattr(settings, "DB_PASS")
        assert hasattr(settings, "DB_SCHEMA")

        # Test database pool settings exist
        assert hasattr(settings, "DB_POOL_SIZE")
        assert hasattr(settings, "DB_MAX_OVERFLOW")
        assert hasattr(settings, "DB_POOL_TIMEOUT")
        assert hasattr(settings, "DB_POOL_RECYCLE")
        assert hasattr(settings, "DB_POOL_PRE_PING")

        # Test that property methods work
        assert settings.db_pool_size == settings.DB_POOL_SIZE
        assert settings.db_max_overflow == settings.DB_MAX_OVERFLOW
        assert settings.db_pool_timeout == settings.DB_POOL_TIMEOUT
        assert settings.db_pool_recycle == settings.DB_POOL_RECYCLE
        assert settings.db_pool_pre_ping == settings.DB_POOL_PRE_PING
        assert settings.search_path == settings.DB_SCHEMA

    def test_sync_database_connection(self):
        """Test synchronous database connection for comparison."""
        try:
            engine = create_engine(
                "sqlite:///:memory:",
                echo=False
            )

            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
        except Exception as e:
            pytest.fail(f"Sync database connection failed: {e}")

    @pytest.mark.asyncio
    async def test_database_engine_disposal(self, db_engine):
        """Test that database engine can be properly disposed."""
        # This test ensures the engine cleanup works properly
        assert db_engine is not None
        await db_engine.dispose()

        # After disposal, the engine should still exist but pool should be invalid
        assert hasattr(db_engine, 'pool')
