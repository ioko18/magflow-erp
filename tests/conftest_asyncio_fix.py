"""
Enhanced test configuration with proper asyncio event loop management.

This module provides fixtures and utilities to prevent asyncio event loop issues
that cause RuntimeError: Event loop is closed during test teardown.
"""

import asyncio
import logging
import warnings
from typing import Any, AsyncGenerator, Dict, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


from app.db.base_class import Base
from app.db.session import get_db
from app.main import app

# Suppress specific warnings that clutter test output
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*Event loop is closed.*")

# Configure logging for tests
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


class AsyncioEventLoopManager:
    """Manages asyncio event loops for tests to prevent closure issues."""

    def __init__(self):
        self._loop = None
        self._engines = []
        self._sessions = []

    def get_or_create_loop(self):
        """Get existing loop or create a new one."""
        try:
            loop = asyncio.get_running_loop()
            if loop.is_closed():
                raise RuntimeError("Loop is closed")
            self._loop = loop
            return loop
        except RuntimeError:
            # Create new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            return loop

    def register_engine(self, engine):
        """Register an engine for proper cleanup."""
        self._engines.append(engine)

    def register_session(self, session):
        """Register a session for proper cleanup."""
        self._sessions.append(session)

    async def cleanup(self):
        """Clean up all registered resources."""
        # Close sessions first
        for session in self._sessions:
            try:
                if hasattr(session, "close"):
                    await session.close()
            except Exception as e:
                logging.debug(f"Error closing session: {e}")

        # Close engines
        for engine in self._engines:
            try:
                if hasattr(engine, "dispose"):
                    await engine.dispose()
            except Exception as e:
                logging.debug(f"Error disposing engine: {e}")

        # Clear registrations
        self._engines.clear()
        self._sessions.clear()


# Global event loop manager
_loop_manager = AsyncioEventLoopManager()


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the entire test session."""
    loop = _loop_manager.get_or_create_loop()
    yield loop

    # Cleanup at the end of session
    try:
        # Run cleanup in the loop
        if not loop.is_closed():
            loop.run_until_complete(_loop_manager.cleanup())

            # Cancel all remaining tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()

            # Wait for tasks to complete cancellation
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
    except Exception as e:
        logging.debug(f"Error during event loop cleanup: {e}")
    finally:
        try:
            if not loop.is_closed():
                loop.close()
        except Exception as e:
            logging.debug(f"Error closing event loop: {e}")


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create a test database engine with proper connection management."""
    # Use in-memory SQLite for tests
    database_url = "sqlite+aiosqlite:///:memory:"

    engine = create_async_engine(
        database_url,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
        },
        echo=False,  # Reduce noise in tests
        pool_pre_ping=True,
        pool_recycle=300,
    )

    # Register for cleanup
    _loop_manager.register_engine(engine)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup is handled by the loop manager


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with proper transaction management."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # Register for cleanup
        _loop_manager.register_session(session)

        # Start a transaction
        async with session.begin():
            yield session
            # Transaction will be rolled back automatically


@pytest_asyncio.fixture
async def test_app_with_db(test_session):
    """Create a test FastAPI application with database dependency override."""

    def get_test_db():
        return test_session

    # Override the database dependency
    app.dependency_overrides[get_db] = get_test_db

    yield app

    # Clean up dependency overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_client(test_app_with_db) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client with proper resource management."""
    async with AsyncClient(
        app=test_app_with_db,
        base_url="http://testserver",
        timeout=30.0,  # Increase timeout for slow tests
    ) as client:
        yield client


@pytest_asyncio.fixture
async def authenticated_client(
    test_client, test_session
) -> AsyncGenerator[AsyncClient, None]:
    """Create an authenticated test client."""
    # This would integrate with your auth system
    # For now, just return the regular client
    yield test_client


# Performance monitoring fixtures
@pytest.fixture(autouse=True)
def monitor_test_performance(request):
    """Monitor test performance and log slow tests."""
    import time

    start_time = time.time()

    yield

    duration = time.time() - start_time
    if duration > 1.0:  # Log tests that take more than 1 second
        logging.warning(f"Slow test detected: {request.node.name} took {duration:.2f}s")


# Utility functions for test data
def create_test_product_data(name_suffix: str = "") -> Dict[str, Any]:
    """Create test product data."""
    import uuid

    unique_id = str(uuid.uuid4())[:8]
    return {
        "name": f"Test Product {name_suffix} {unique_id}",
        "sku": f"SKU-{unique_id}",
        "price": 99.99,
        "description": "A test product",
        "is_active": True,
        "currency": "USD",
        "is_discontinued": False,
    }


def create_test_user_data(email_suffix: str = "") -> Dict[str, Any]:
    """Create test user data."""
    import uuid

    unique_id = str(uuid.uuid4())[:8]
    return {
        "email": f"test{email_suffix}_{unique_id}@example.com",
        "password": "TestPassword123!",
        "full_name": f"Test User {unique_id}",
        "is_active": True,
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Mark tests in certain directories
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Mark slow tests based on name patterns
        if any(
            keyword in item.name.lower()
            for keyword in ["slow", "performance", "benchmark"]
        ):
            item.add_marker(pytest.mark.slow)
