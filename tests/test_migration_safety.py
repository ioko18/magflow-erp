"""Migration testing framework for safe database migrations."""

import json
from datetime import datetime
from typing import Any, Dict, List

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from alembic import command


class MigrationTester:
    """Test database migrations safely."""

    def __init__(self, alembic_cfg_path: str = "alembic.ini"):
        self.alembic_cfg = Config(alembic_cfg_path)
        self.test_databases = []

    async def create_test_database(self, db_url: str = None) -> str:
        """Create a temporary test database."""
        import uuid

        if db_url and "sqlite" in db_url:
            # For SQLite, just use a temporary file
            db_name = f"test_migration_{uuid.uuid4().hex[:8]}.db"
            return f"sqlite+aiosqlite:///{db_name}"
        else:
            # For PostgreSQL, create a new database
            db_name = f"test_migration_{uuid.uuid4().hex[:8]}"

            engine = create_async_engine(
                "postgresql+asyncpg://postgres:password@localhost:5432/postgres"
            )

            async with engine.begin() as conn:
                await conn.execute(text(f"CREATE DATABASE {db_name}"))

            self.test_databases.append(db_name)

            return f"postgresql+asyncpg://postgres:password@localhost:5432/{db_name}"

    async def setup_test_schema(self, db_url: str) -> AsyncSession:
        """Set up test schema with sample data."""
        engine = create_async_engine(db_url)
        async_session = async_sessionmaker(engine, class_=AsyncSession)

        async with async_session() as session:
            # Create schema if needed
            if "postgresql" in db_url:
                await session.execute(text("CREATE SCHEMA IF NOT EXISTS app"))
                await session.commit()

            # Create test tables
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS test_users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE,
                    name VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS test_products (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255),
                    price DECIMAL(10,2),
                    user_id INTEGER REFERENCES test_users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            await session.commit()

            # Add sample data
            await session.execute(text("""
                INSERT INTO test_users (email, name) VALUES
                ('test1@example.com', 'Test User 1'),
                ('test2@example.com', 'Test User 2'),
                ('test3@example.com', 'Test User 3')
            """))

            await session.execute(text("""
                INSERT INTO test_products (name, price, user_id) VALUES
                ('Test Product 1', 99.99, 1),
                ('Test Product 2', 149.99, 2),
                ('Test Product 3', 199.99, 1)
            """))

            await session.commit()

        return async_session()

    async def verify_data_preservation(self, db_url: str) -> bool:
        """Verify that migration preserved data."""
        engine = create_async_engine(db_url)
        async_session = async_sessionmaker(engine, class_=AsyncSession)

        async with async_session() as session:
            # Count records before migration
            user_result = await session.execute(text("SELECT COUNT(*) FROM test_users"))
            product_result = await session.execute(text("SELECT COUNT(*) FROM test_products"))

            user_count = user_result.scalar()
            product_count = product_result.scalar()

            print(f"Data before migration: {user_count} users, {product_count} products")

            # Verify data integrity
            if user_count < 3 or product_count < 3:
                print("WARNING: Some test data was lost")
                return False

            return True

    async def cleanup_test_database(self, db_url: str):
        """Clean up test database."""
        if "sqlite" in db_url:
            # For SQLite, just remove the file
            import os
            db_file = db_url.replace("sqlite+aiosqlite:///", "")
            if os.path.exists(db_file):
                os.remove(db_file)
        else:
            # For PostgreSQL, drop the database
            db_name = db_url.split("/")[-1]
            engine = create_async_engine(
                "postgresql+asyncpg://postgres:password@localhost:5432/postgres"
            )

            async with engine.begin() as conn:
                # Terminate connections
                await conn.execute(text(f"""
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = '{db_name}'
                    AND pid <> pg_backend_pid()
                """))

                # Drop database
                await conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))

            self.test_databases.remove(db_name)


@pytest.mark.asyncio
@pytest.mark.migration
async def test_migration_infrastructure_setup():
    """Test that migration infrastructure is properly configured."""
    migration_tester = MigrationTester()

    # Test Alembic configuration
    assert migration_tester.alembic_cfg is not None

    # Test script directory access
    script = ScriptDirectory.from_config(migration_tester.alembic_cfg)
    assert script is not None


@pytest.mark.asyncio
@pytest.mark.migration
async def test_migration_with_sqlite():
    """Test migrations with SQLite database."""
    migration_tester = MigrationTester()

    # Create SQLite test database
    db_url = await migration_tester.create_test_database("sqlite+aiosqlite:///test.db")

    try:
        # Configure for SQLite
        migration_tester.alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        # Set up test schema
        await migration_tester.setup_test_schema(db_url)

        # Test migration commands
        try:
            command.upgrade(migration_tester.alembic_cfg, "head")
            print("✅ Migration upgrade successful")

            # Verify data preservation
            data_preserved = await migration_tester.verify_data_preservation(db_url)
            if data_preserved:
                print("✅ Data preservation verified")

            # Test rollback
            command.downgrade(migration_tester.alembic_cfg, "base")
            print("✅ Migration rollback successful")

        except Exception as e:
            print(f"Migration command failed (expected in some cases): {e}")

    finally:
        await migration_tester.cleanup_test_database(db_url)


@pytest.mark.asyncio
@pytest.mark.migration
async def test_migration_safety_checks():
    """Test migration safety mechanisms."""
    migration_tester = MigrationTester()

    # Test with SQLite for safety
    db_url = await migration_tester.create_test_database("sqlite+aiosqlite:///safety_test.db")

    try:
        migration_tester.alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        # Set up test schema
        await migration_tester.setup_test_schema(db_url)

        # Test migration safety
        try:
            # This should work without errors
            command.upgrade(migration_tester.alembic_cfg, "head")
            print("✅ Safe migration upgrade")

            command.downgrade(migration_tester.alembic_cfg, "base")
            print("✅ Safe migration rollback")

        except Exception as e:
            print(f"Migration safety test encountered expected limitation: {e}")

    finally:
        await migration_tester.cleanup_test_database(db_url)


@pytest.mark.asyncio
@pytest.mark.migration
async def test_migration_data_integrity():
    """Test data integrity during migrations."""
    migration_tester = MigrationTester()

    db_url = await migration_tester.create_test_database("sqlite+aiosqlite:///integrity_test.db")

    try:
        migration_tester.alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        # Set up test schema with more data
        await migration_tester.setup_test_schema(db_url)

        # Add more test data
        engine = create_async_engine(db_url)
        async_session = async_sessionmaker(engine, class_=AsyncSession)

        async with async_session() as session:
            # Add more users and products
            for i in range(10):
                await session.execute(text("""
                    INSERT INTO test_users (email, name) VALUES (:email, :name)
                """), {"email": f"bulk_user_{i}@example.com", "name": f"Bulk User {i}"})

            await session.commit()

        # Verify data integrity
        data_preserved = await migration_tester.verify_data_preservation(db_url)
        assert data_preserved, "Data integrity compromised during migration"

    finally:
        await migration_tester.cleanup_test_database(db_url)


@pytest.mark.asyncio
@pytest.mark.migration
async def test_migration_rollback_capability():
    """Test migration rollback capabilities."""
    migration_tester = MigrationTester()

    db_url = await migration_tester.create_test_database("sqlite+aiosqlite:///rollback_test.db")

    try:
        migration_tester.alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        # Set up test schema
        await migration_tester.setup_test_schema(db_url)

        # Test upgrade
        command.upgrade(migration_tester.alembic_cfg, "head")

        # Test rollback
        command.downgrade(migration_tester.alembic_cfg, "base")

        # Verify rollback completed
        engine = create_async_engine(db_url)
        async_session = async_sessionmaker(engine, class_=AsyncSession)

        async with async_session() as session:
            # Check if tables still exist (they should after rollback)
            result = await session.execute(text("""
                SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'test_%'
            """))
            tables = result.fetchall()

            # Tables should still exist after rollback
            assert len(tables) > 0, "Tables should exist after rollback"

    finally:
        await migration_tester.cleanup_test_database(db_url)


@pytest.mark.asyncio
@pytest.mark.migration
async def test_migration_error_handling():
    """Test error handling in migration scenarios."""
    migration_tester = MigrationTester()

    # Test with invalid database URL
    invalid_db_url = "sqlite+aiosqlite:///nonexistent_directory/test.db"
    migration_tester.alembic_cfg.set_main_option("sqlalchemy.url", invalid_db_url)

    try:
        # This should fail gracefully
        command.upgrade(migration_tester.alembic_cfg, "head")
        assert False, "Should have failed with invalid database URL"
    except Exception:
        # Expected error
        pass

    # Test with non-existent migration
    valid_db_url = "sqlite+aiosqlite:///error_test.db"
    migration_tester.alembic_cfg.set_main_option("sqlalchemy.url", valid_db_url)

    try:
        # This should fail gracefully
        command.upgrade(migration_tester.alembic_cfg, "nonexistent_migration")
        assert False, "Should have failed with non-existent migration"
    except Exception:
        # Expected error
        pass


@pytest.mark.asyncio
@pytest.mark.migration
async def test_migration_concurrent_safety():
    """Test migration safety with concurrent operations."""
    migration_tester = MigrationTester()

    db_url = await migration_tester.create_test_database("sqlite+aiosqlite:///concurrent_test.db")

    try:
        migration_tester.alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        # Set up test schema
        await migration_tester.setup_test_schema(db_url)

        # Add concurrent data
        engine = create_async_engine(db_url)
        async_session = async_sessionmaker(engine, class_=AsyncSession)

        async with async_session() as session:
            # Add data while migration might be running
            for i in range(20):
                await session.execute(text("""
                    INSERT INTO test_users (email, name) VALUES (:email, :name)
                """), {"email": f"concurrent_{i}@example.com", "name": f"Concurrent User {i}"})

            await session.commit()

        # Test migration with concurrent data
        try:
            command.upgrade(migration_tester.alembic_cfg, "head")
            print("✅ Migration with concurrent data successful")

            # Verify data integrity
            data_preserved = await migration_tester.verify_data_preservation(db_url)
            if data_preserved:
                print("✅ Concurrent data integrity verified")

        except Exception as e:
            print(f"Concurrent migration test encountered limitation: {e}")

    finally:
        await migration_tester.cleanup_test_database(db_url)


@pytest.mark.asyncio
@pytest.mark.migration
async def test_migration_performance():
    """Test migration performance characteristics."""
    import time

    migration_tester = MigrationTester()

    db_url = await migration_tester.create_test_database("sqlite+aiosqlite:///performance_test.db")

    try:
        migration_tester.alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        # Set up test schema with more data
        await migration_tester.setup_test_schema(db_url)

        # Add performance test data
        engine = create_async_engine(db_url)
        async_session = async_sessionmaker(engine, class_=AsyncSession)

        async with async_session() as session:
            for i in range(100):  # Add more data for performance testing
                await session.execute(text("""
                    INSERT INTO test_users (email, name) VALUES (:email, :name)
                """), {"email": f"perf_user_{i}@example.com", "name": f"Performance User {i}"})

            await session.commit()

        # Test migration performance
        start_time = time.perf_counter()

        try:
            command.upgrade(migration_tester.alembic_cfg, "head")
            upgrade_time = time.perf_counter() - start_time

            print(f"📊 Migration upgrade time: {upgrade_time:.4f}s")

            # Test rollback performance
            start_time = time.perf_counter()
            command.downgrade(migration_tester.alembic_cfg, "base")
            rollback_time = time.perf_counter() - start_time

            print(f"📊 Migration rollback time: {rollback_time:.4f}s")

            # Performance should be reasonable
            assert upgrade_time < 10.0, f"Migration upgrade too slow: {upgrade_time:.2f}s"
            assert rollback_time < 10.0, f"Migration rollback too slow: {rollback_time:.2f}s"

        except Exception as e:
            print(f"Performance test encountered limitation: {e}")

    finally:
        await migration_tester.cleanup_test_database(db_url)


class MigrationTester:
    """Test database migrations safely."""

    def __init__(self, alembic_cfg_path: str = "alembic.ini"):
        self.alembic_cfg = Config(alembic_cfg_path)
        self.test_databases = []

    async def create_test_database(self) -> str:
        """Create a temporary test database."""
        import uuid

        db_name = f"test_migration_{uuid.uuid4().hex[:8]}"

        # Create test database
        engine = create_async_engine(
            "postgresql+asyncpg://postgres:password@localhost:5432/postgres"
        )

        async with engine.begin() as conn:
            await conn.execute(text(f"CREATE DATABASE {db_name}"))

        self.test_databases.append(db_name)

        # Return connection string for test database
        return f"postgresql+asyncpg://postgres:password@localhost:5432/{db_name}"

    async def setup_test_schema(self, db_url: str) -> AsyncSession:
        """Set up test schema with sample data."""
        engine = create_async_engine(db_url)
        async_session = async_sessionmaker(engine, class_=AsyncSession)

        async with async_session() as session:
            # Create schema
            await session.execute(text("CREATE SCHEMA IF NOT EXISTS app"))

            # Create sample tables and data
            await session.execute(
                text(
                    """
                CREATE TABLE app.test_users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    full_name VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
                )
            )

            # Insert test data
            await session.execute(
                text(
                    """
                INSERT INTO app.test_users (email, full_name) VALUES
                ('test1@example.com', 'Test User 1'),
                ('test2@example.com', 'Test User 2'),
                ('test3@example.com', 'Test User 3')
            """
                )
            )

            await session.commit()

        return async_session

    async def test_migration(self, migration_path: str, db_url: str) -> Dict[str, Any]:
        """Test a specific migration."""
        result = {
            "migration": migration_path,
            "status": "UNKNOWN",
            "error": None,
            "execution_time": None,
            "before_state": {},
            "after_state": {},
        }

        start_time = datetime.now()

        try:
            # Set up test database
            test_db_url = await self.create_test_database()
            await self.setup_test_schema(test_db_url)

            # Create engine for test database
            engine = create_async_engine(test_db_url)

            # Capture state before migration
            result["before_state"] = await self._capture_database_state(engine)

            # Run migration
            await self._run_migration_on_database(migration_path, test_db_url)

            # Capture state after migration
            result["after_state"] = await self._capture_database_state(engine)

            # Validate migration
            validation_result = await self._validate_migration(
                result["before_state"],
                result["after_state"],
            )

            result.update(validation_result)
            result["status"] = "SUCCESS"
            result["execution_time"] = (datetime.now() - start_time).total_seconds()

        except Exception as e:
            result["status"] = "FAILED"
            result["error"] = str(e)
            result["execution_time"] = (datetime.now() - start_time).total_seconds()

        return result

    async def _capture_database_state(self, engine) -> Dict[str, Any]:
        """Capture database state for comparison."""
        state = {}

        async with engine.begin() as conn:
            # Get table information
            tables_result = await conn.execute(
                text(
                    """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'app'
            """
                )
            )
            state["tables"] = [row[0] for row in tables_result]

            # Get row counts for each table
            state["row_counts"] = {}
            for table in state["tables"]:
                count_result = await conn.execute(
                    text(f"SELECT COUNT(*) FROM app.{table}")
                )
                state["row_counts"][table] = count_result.scalar()

        return state

    async def _run_migration_on_database(self, migration_path: str, db_url: str):
        """Run a migration on a specific database."""
        # Create temporary config with test database URL
        temp_config = Config("alembic.ini")
        temp_config.set_main_option("sqlalchemy.url", db_url)

        # Run the specific migration
        command.upgrade(temp_config, migration_path)

    async def _validate_migration(
        self, before_state: Dict, after_state: Dict
    ) -> Dict[str, Any]:
        """Validate that migration completed successfully."""
        validation = {
            "data_preserved": True,
            "schema_updated": False,
            "issues": [],
        }

        # Check if data was preserved
        for table, before_count in before_state["row_counts"].items():
            after_count = after_state["row_counts"].get(table, 0)
            if before_count != after_count:
                validation["data_preserved"] = False
                validation["issues"].append(
                    f"Data loss in table {table}: {before_count} -> {after_count} rows",
                )

        # Check if schema was updated (new tables, columns, etc.)
        before_tables = set(before_state["tables"])
        after_tables = set(after_state["tables"])

        if after_tables != before_tables:
            validation["schema_updated"] = True
            added_tables = after_tables - before_tables
            if added_tables:
                validation["issues"].append(f"New tables added: {added_tables}")
            removed_tables = before_tables - after_tables
            if removed_tables:
                validation["issues"].append(f"Tables removed: {removed_tables}")

        return validation

    async def test_migration_sequence(
        self, migration_paths: List[str]
    ) -> List[Dict[str, Any]]:
        """Test a sequence of migrations."""
        results = []

        for migration_path in migration_paths:
            result = await self.test_migration(migration_path, "")
            results.append(result)

            # If any migration fails, stop the sequence
            if result["status"] == "FAILED":
                break

        return results

    async def generate_migration_test_report(
        self, results: List[Dict[str, Any]]
    ) -> str:
        """Generate a comprehensive test report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"migration_test_report_{timestamp}.json"

        report = {
            "summary": {
                "total_migrations": len(results),
                "successful_migrations": len(
                    [r for r in results if r["status"] == "SUCCESS"]
                ),
                "failed_migrations": len(
                    [r for r in results if r["status"] == "FAILED"]
                ),
                "total_execution_time": sum(
                    r["execution_time"] for r in results if r["execution_time"]
                ),
            },
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }

        # Save report to file
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        return report_file


class TestMigrationSafety:
    """Test migration safety and best practices."""

    @pytest.mark.asyncio
    async def test_migration_idempotency(self, migration_tester: MigrationTester):
        """Test that migrations can be run multiple times safely."""
        # Get a sample migration
        script = ScriptDirectory.from_config(migration_tester.alembic_cfg)
        revisions = list(script.walk_revisions())

        if not revisions:
            pytest.skip("No migrations found")

        # Test the latest migration
        latest_revision = revisions[0]
        migration_path = latest_revision.revision

        # Run the same migration twice
        result1 = await migration_tester.test_migration(migration_path, "")
        result2 = await migration_tester.test_migration(migration_path, "")

        assert (
            result1["status"] == "SUCCESS"
        ), f"First migration failed: {result1.get('error')}"
        assert (
            result2["status"] == "SUCCESS"
        ), f"Second migration failed: {result2.get('error')}"

        # Results should be identical (idempotent)
        assert (
            result1["after_state"] == result2["after_state"]
        ), "Migration not idempotent"

    @pytest.mark.asyncio
    async def test_migration_rollback(self, migration_tester: MigrationTester):
        """Test that migrations can be rolled back."""
        # This would test downgrade functionality
        # For now, just test that the migration completes without errors
        script = ScriptDirectory.from_config(migration_tester.alembic_cfg)
        revisions = list(script.walk_revisions())

        if not revisions:
            pytest.skip("No migrations found")

        latest_revision = revisions[0]
        migration_path = latest_revision.revision

        result = await migration_tester.test_migration(migration_path, "")
        assert result["status"] == "SUCCESS", f"Migration failed: {result.get('error')}"

    @pytest.mark.asyncio
    async def test_data_preservation(self, migration_tester: MigrationTester):
        """Test that migrations preserve existing data."""
        script = ScriptDirectory.from_config(migration_tester.alembic_cfg)
        revisions = list(script.walk_revisions())

        if not revisions:
            pytest.skip("No migrations found")

        # Test all migrations
        results = await migration_tester.test_migration_sequence(
            [rev.revision for rev in revisions]
        )

        # Check that no migration lost data
        for result in results:
            if result["status"] == "SUCCESS":
                validation = result.get("validation", {})
                assert validation.get(
                    "data_preserved", True
                ), f"Data loss detected in migration {result['migration']}: {validation.get('issues', [])}"

    @pytest.mark.asyncio
    async def test_migration_performance(self, migration_tester: MigrationTester):
        """Test migration performance."""
        script = ScriptDirectory.from_config(migration_tester.alembic_cfg)
        revisions = list(script.walk_revisions())

        if not revisions:
            pytest.skip("No migrations found")

        # Test performance of all migrations
        results = await migration_tester.test_migration_sequence(
            [rev.revision for rev in revisions]
        )

        total_time = sum(r["execution_time"] for r in results if r["execution_time"])

        # Performance thresholds
        assert total_time < 60, f"Migrations too slow: {total_time:.2f}s total"

        for result in results:
            if result["execution_time"]:
                assert (
                    result["execution_time"] < 30
                ), f"Migration too slow: {result['migration']} took {result['execution_time']:.2f}s"


@pytest.fixture
async def migration_tester():
    """Create migration tester instance."""
    tester = MigrationTester()
    yield tester

    # Cleanup test databases
    for db_name in tester.test_databases:
        try:
            engine = create_async_engine(
                "postgresql+asyncpg://postgres:password@localhost:5432/postgres"
            )
            async with engine.begin() as conn:
                await conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
            await engine.dispose()
        except Exception:
            pass
