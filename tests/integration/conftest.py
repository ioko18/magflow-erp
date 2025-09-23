import asyncio
import os
from typing import AsyncGenerator

import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.core.config import settings
from app.db.base_class import Base
from app.main import app as _app

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Override settings for testing
os.environ["ENVIRONMENT"] = "testing"

# Set test database configuration
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5432"
os.environ["DB_USER"] = "test"
os.environ["DB_PASS"] = "test"
os.environ["DB_NAME"] = "test_magflow"
os.environ["DB_SCHEMA"] = "public"
os.environ["SQL_ECHO"] = "True"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["JWT_ALGORITHM"] = "HS256"

# Make sure we're using the in-memory SQLite for testing
os.environ["DB_HOST"] = ""
os.environ["DB_URL"] = TEST_DATABASE_URL


# Create async engine and session factory for testing
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine() -> AsyncEngine:
    """Create a test database engine."""
    # Create engine with SQLite in-memory database
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=True,
        future=True,
        connect_args={"check_same_thread": False},
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

    # Clear the database URL to prevent connection pool issues
    if hasattr(settings, "DB_URL"):
        del os.environ["DB_URL"]


@pytest.fixture(scope="session")
async def app(engine: AsyncEngine):
    """Create a test FastAPI application with test settings."""
    # Ensure we're using test settings
    assert (
        settings.ENVIRONMENT == "testing"
    ), "Tests must be run with ENVIRONMENT=testing"
    return _app


class AsyncSessionContext:
    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self.connection = None
        self.transaction = None
        self.session: AsyncSession | None = None

    async def __aenter__(self):
        self.connection = await self.engine.connect()
        self.transaction = await self.connection.begin()
        self.session = AsyncSession(bind=self.connection, expire_on_commit=False)
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.session is not None:
                await self.session.flush()
                await self.transaction.rollback()
                await self.session.close()
        finally:
            if self.connection is not None:
                await self.connection.close()


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for testing.

    Yields:
        AsyncSession: A database session that will be automatically rolled back after each test.

    """
    # Create a new session
    session = AsyncSession(engine, expire_on_commit=False)

    try:
        # Begin a transaction
        await session.begin()

        # Yield the session for the test to use
        yield session
    finally:
        # Always rollback the transaction and close the session
        await session.rollback()
        await session.close()


@pytest.fixture
def test_user():
    """Create test user data for authentication tests."""
    return {
        "email": "test@example.com",
        "password": "testpassword",
        "full_name": "Test User",
        "is_active": True,
        "is_superuser": False,
    }


@pytest.fixture
async def create_test_user(db_session):
    """Create a test user in the database and return the user data with ID."""
    from app.core.security import get_password_hash
    from app.db.models import User

    # Create a new user
    user_data = {
        "email": "test@example.com",
        "password": "testpassword",
        "full_name": "Test User",
        "is_active": True,
        "is_superuser": False,
    }

    # Create user object
    user = User(
        email=user_data["email"],
        hashed_password=get_password_hash(user_data["password"]),
        full_name=user_data["full_name"],
        is_active=user_data["is_active"],
        is_superuser=user_data["is_superuser"],
    )

    # Add user to the database
    db_session.add(user)
    await db_session.flush()
    user_data["id"] = user.id
    await db_session.commit()

    # Refresh the user to ensure we have the latest data
    await db_session.refresh(user)

    return user_data


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator:
    """Create a test client for the FastAPI app.

    This fixture creates an async HTTP client that can be used to make requests
    to the test application. It automatically handles async context management.
    """
    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://testserver") as test_client:
        yield test_client
