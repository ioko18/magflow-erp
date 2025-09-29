"""
Simple Performance Tests for MagFlow ERP
========================================

Robust, reliable performance tests using the Simple Performance Monitor.
This test suite focuses on stability and accurate performance measurement.
"""

import asyncio
import statistics
import time
import uuid
import pytest
import pytest_asyncio
from contextlib import asynccontextmanager
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.product import Product
from app.models.category import Category
from app.db.base_class import Base
from tests.simple_performance_monitor import get_simple_monitor

# Initialize simple monitor with optimized settings
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/magflow_test"
monitor = get_simple_monitor(TEST_DATABASE_URL)

# Global engine and session factory
engine = None
AsyncSessionLocal = None


async def init_db():
    """Initialize database engine and session factory."""
    global engine, AsyncSessionLocal

    if engine is None:
        # Create engine with optimized settings for testing
        engine = create_async_engine(
            TEST_DATABASE_URL,
            echo=False,
            future=True,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        # Create session factory
        AsyncSessionLocal = sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            future=True,
            autocommit=False,
            autoflush=False,
        )

        # Initialize database schema
        async with engine.begin() as conn:
            # Drop all tables if they exist
            await conn.run_sync(Base.metadata.drop_all)
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)

    return AsyncSessionLocal


class DBSessionManager:
    def __init__(self):
        self._session_factory = None

    async def get_session_factory(self):
        if self._session_factory is None:
            self._session_factory = await init_db()
        return self._session_factory

    async def get_session(self, autocommit=False):
        session_factory = await self.get_session_factory()
        session = session_factory()

        if not autocommit:
            await session.begin()

        return session

    async def close_session(self, session):
        try:
            if session.in_transaction():
                await session.rollback()
            await session.close()
        except Exception as e:
            print(f"Error closing session: {e}")
        finally:
            # Small delay to ensure cleanup
            await asyncio.sleep(0.05)


# Global session manager
db_manager = DBSessionManager()


@asynccontextmanager
async def get_db_session(autocommit=False):
    """Get a database session with automatic cleanup.

    Args:
        autocommit: If True, don't start a transaction automatically
    """
    session = await db_manager.get_session(autocommit=autocommit)
    try:
        yield session
    finally:
        await db_manager.close_session(session)


async def create_test_data(session):
    """Helper function to create test data."""
    # Create test category
    category = Category(
        name=f"Test Category {uuid.uuid4().hex[:8]}",
        description="Test category for performance tests",
    )
    session.add(category)
    await session.flush()

    # Create test products
    products = []
    for i in range(3):  # Reduced number of test products
        product = Product(
            name=f"Test Product {i}",
            sku=f"TST-{uuid.uuid4().hex[:8]}",
            base_price=float(100.0 + (i * 10)),
            currency="USD",
            is_active=True,
        )
        product.categories.append(category)
        products.append(product)

    session.add_all(products)
    await session.flush()

    return category, products


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a new database session with optimized settings."""
    await init_db()  # Initialize the database without assigning to session_factory

    async with get_db_session(autocommit=True) as session:
        # Set statement timeout
        await session.execute(text("SET statement_timeout = 5000"))
        yield session

        # Ensure any pending operations are completed
        if session.in_transaction():
            await session.rollback()


@pytest.fixture(autouse=True)
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_simple_delete_product():
    """Test product deletion with simple monitoring."""
    test_context = monitor.start_test("simple_delete_product")

    try:
        # Get a new session with autocommit=False to control transactions manually
        db_session = await db_manager.get_session(autocommit=False)

        try:
            # Create test data
            category, products = await create_test_data(db_session)
            await db_session.commit()

            # Get first product to delete
            product = products[0]
            product_id = product.id

            # Mark setup complete
            test_context["setup_time"] = time.time() - test_context["start_time"]

            # Start a new transaction for the delete operation
            await db_session.begin()
            try:
                # Delete product
                await db_session.delete(product)
                await db_session.commit()

                # Verify deletion in a new transaction
                await db_session.begin()
                try:
                    result = await db_session.execute(
                        select(Product).filter(Product.id == product_id)
                    )
                    deleted_product = result.scalar_one_or_none()
                    await db_session.commit()

                    assert (
                        deleted_product is None
                    ), f"Product with ID {product_id} was not deleted"

                    # End test successfully
                    await monitor.end_test(test_context)

                except Exception as _inner_e:
                    await db_session.rollback()
                    raise

            except Exception as _e:
                await db_session.rollback()
                raise

        finally:
            # Ensure session is properly closed
            await db_manager.close_session(db_session)

    except Exception as e:
        # Ensure test context is properly ended on error
        if "test_context" in locals():
            await monitor.end_test(test_context, error=str(e))
        raise


@pytest.mark.asyncio
async def test_simple_performance_report():
    """Generate and verify simple performance report."""
    test_context = monitor.start_test("simple_performance_report")

    # Get a new session with autocommit=False to control transactions manually
    db_session = await db_manager.get_session(autocommit=False)

    try:
        # Create test data
        await create_test_data(db_session)
        await db_session.commit()

        # Mark setup complete
        test_context["setup_time"] = time.time() - test_context["start_time"]

        # Generate the report
        report = monitor.generate_report()

        # Basic validation of the report structure
        assert isinstance(report, str), "Report should be a string"

        # Get metrics summary directly from metrics
        metrics_summary = monitor.metrics.get_summary()
        assert isinstance(
            metrics_summary, dict
        ), "Metrics summary should be a dictionary"
        assert "status" in metrics_summary, "Metrics summary should contain status"

        # Print the report
        print("\n" + "=" * 60)
        print("🚀 Simple Performance Report - MagFlow ERP")
        print("=" * 60)
        print(report)

        # Check if we have any test results
        test_count = len(monitor.metrics.test_names)
        print("\n📊 Test Metrics Summary (from metrics):")
        print(f"Total tests run: {test_count}")

        if test_count > 0 and monitor.metrics.test_times:
            total_time = sum(monitor.metrics.test_times)
            avg_time = statistics.mean(monitor.metrics.test_times)
            print(f"Total test time: {total_time:.3f}s")
            print(f"Average test time: {avg_time:.3f}s")
        else:
            print("No test results were recorded")

        # End test successfully
        await monitor.end_test(test_context)

    except Exception as _e:
        # Ensure we rollback on error
        if db_session.in_transaction():
            await db_session.rollback()
        # Ensure test context is properly ended on error
        if "test_context" in locals():
            await monitor.end_test(test_context, error=str(_e))
        raise

    finally:
        # Ensure session is properly closed
        await db_manager.close_session(db_session)
        # Small delay to ensure all pending tasks are cleared
        await asyncio.sleep(0.1)
