"""
Database fixtures for testing.

This module provides fixtures for setting up and tearing down a test database.
"""
import asyncio
from typing import AsyncGenerator, Generator

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from tests.config import test_config

# Import models to ensure they are registered with SQLAlchemy
from app.db.base_class import Base
from app.db.models import *  # noqa: F401, F403

# Create test database URL
TEST_DATABASE_URL = (
    f"postgresql+asyncpg://{test_config.TEST_DB_USER}:"
    f"{test_config.TEST_DB_PASSWORD}@{test_config.TEST_DB_HOST}:"
    f"{test_config.TEST_DB_PORT}/{test_config.TEST_DB_NAME}"
)

# Create async engine for testing
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=True,
    poolclass=NullPool,  # Use NullPool for testing to ensure clean state
)

# Create session factory for testing
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_test_database() -> AsyncGenerator[None, None]:
    """
    Create test database and tables.
    """
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Drop all tables after tests
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def db_session(setup_test_database) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a new database session for testing.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    # Begin a nested transaction (using SAVEPOINT).
    nested = connection.begin_nested()
    
    # If the application code calls session.commit, it will end the nested
    # transaction. We need to start a new one when that happens.
    @event.listens_for(session, "after_transaction_end")
    def end_savepoint(session, transaction):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()
    
    yield session
    
    # Cleanup
    session.close()
    transaction.rollback()
    connection.close()
