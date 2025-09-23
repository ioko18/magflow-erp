"""Test configuration for explain plan tests."""

from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base_class import Base

# Test database URL with a different name to avoid conflicts
test_db_name = "test_magflow_explain"
TEST_DATABASE_URL = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASS}@{settings.DB_HOST}:{settings.DB_PORT}/{test_db_name}"

# Create test engine
engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=settings.SQL_ECHO,
)

# Create test session factory
TestingSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="module")
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Database session fixture for explain plan tests."""
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create a new session for the test
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.rollback()
        finally:
            await session.close()

    # Clean up all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
async def enable_explain():
    """Enable EXPLAIN for all queries during tests."""
    import os

    os.environ["SQLALCHEMY_ECHO"] = "1"
    yield
    os.environ.pop("SQLALCHEMY_ECHO", None)
