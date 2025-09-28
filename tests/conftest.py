"""
Test configuration for MagFlow ERP.

This module provides test fixtures and configuration for the MagFlow ERP test suite.
"""
import asyncio
from pathlib import Path
import sys

import asyncpg
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import pytest
from typing import AsyncGenerator
import pytest_asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
import redis.asyncio as redis

from app.core.config import settings
from app.db.base_class import Base
from app.db.session import get_async_db
from app.api.tasks import router as tasks_router

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
# Override database settings for testing
settings.TESTING = True

# Test database URL - Using PostgreSQL for testing to match production
# Use the asyncpg driver for async database operations
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/magflow_test"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

async def create_test_database():
    """Create the test database and required extensions if they don't exist."""
    # Get the database URL without the database name
    db_url = "postgresql://postgres:password@localhost:5432/postgres"

    # Connect to the default 'postgres' database
    conn = await asyncpg.connect(db_url)

    try:
        # Check if the test database exists
        result = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", "magflow_test"
        )

        if not result:
            # Create the test database
            await conn.execute("CREATE DATABASE magflow_test")

        # Create a connection URL for asyncpg (without the +asyncpg part)
        test_db_url = TEST_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        
        # Connect to the test database to create extensions
        test_conn = await asyncpg.connect(test_db_url)
        try:
            # Try to create required extensions, but don't fail if they don't exist
            for ext in ["uuid-ossp", "pgcrypto"]:
                try:
                    await test_conn.execute(f"CREATE EXTENSION IF NOT EXISTS \"{ext}\";")
                except asyncpg.exceptions.DuplicateObject:
                    pass
                except Exception as e:
                    print(f"Warning: Could not create extension {ext}: {e}")
        finally:
            await test_conn.close()

    finally:
        await conn.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create a test database engine with optimized connection pooling."""
    # Create the test database if it doesn't exist
    await create_test_database()
    
    # Create engine with connection pooling
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=settings.SQL_ECHO,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=10,
        max_overflow=20,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    try:
        yield engine
    finally:
        # Ensure the engine is properly disposed
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine):
    """Create a database session for testing with automatic rollback."""
    # Create a connection and transaction
    connection = await db_engine.connect()
    transaction = await connection.begin()
    
    # Create a session bound to this connection
    session_factory = sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        future=True
    )
    
    session = session_factory()
    
    try:
        yield session
    finally:
        # Roll back the transaction and close the session
        await session.rollback()
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def test_category(db_session: AsyncSession):
    """Create a test category in the database."""
    from app.models.category import Category
    from uuid import uuid4
    
    # Create a new category
    category = Category(
        name=f"Test Category {str(uuid4())[:8]}",
        description="A test category"
    )
    
    # Add and commit the category
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    
    # Return the category data
    return {
        "id": category.id,
        "name": category.name,
        "description": category.description
    }


@pytest_asyncio.fixture
async def test_product(db_session: AsyncSession, test_category: dict):
    """Create a test product in the database."""
    from app.models.product import Product
    from app.models.category import Category
    from uuid import uuid4
    
    # Create the product
    product = Product(
        name=f"Test Product {uuid4().hex[:8]}",
        sku=f"TEST-{uuid4().hex[:8]}",
        base_price=99.99,
        currency="USD",
        description="A test product",
        is_active=True
    )
    
    # Get the category
    category = await db_session.get(Category, test_category["id"])
    product.categories.append(category)
    
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    
    return {
        "id": product.id,
        "name": product.name,
        "sku": product.sku,
        "base_price": float(product.base_price),
        "currency": product.currency,
        "description": product.description,
        "is_active": product.is_active,
        "category_ids": [c.id for c in product.categories]
    }


@pytest_asyncio.fixture
def sample_product_data():
    """Sample product data for testing."""
    from uuid import uuid4
    return {
        "name": f"Test Product {str(uuid4())[:8]}",
        "sku": f"TEST-{str(uuid4())[:8]}",
        "base_price": 99.99,
        "currency": "USD",
        "description": "A test product",
        "is_active": True,
        "category_ids": [1],
        "characteristics": [{"name": "color", "value": "red"}],
        "images": ["test.jpg"]
    }


@pytest_asyncio.fixture
async def async_client(db_engine: AsyncEngine) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for FastAPI endpoints using httpx.AsyncClient with ASGITransport."""
    # Create a new FastAPI app for testing
    test_app = FastAPI()
    
    # Add CORS middleware
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include tasks router with version prefix
    test_app.include_router(tasks_router, prefix=f"{settings.API_V1_STR}/tasks")
    
    # Override the database dependency to use our test database
    async def override_get_db():
        connection = await db_engine.connect()
        transaction = await connection.begin()
        session_factory = sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            future=True,
        )
        session = session_factory()
        await session.begin_nested()
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()
            await transaction.rollback()
            await connection.close()
    
    test_app.dependency_overrides[get_async_db] = override_get_db
    
    @test_app.on_event("startup")
    async def startup():
        try:
            redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            await FastAPILimiter.init(test_app, redis_client)
        except Exception as e:
            print(f"Warning: Could not connect to Redis: {e}")
            await FastAPILimiter.init(test_app)
    
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        yield client
    
    if 'redis_client' in locals():
        await redis_client.close()

# Alias fixture for compatibility with tests expecting a 'client' fixture
@pytest.fixture
def client(async_client: AsyncClient) -> AsyncClient:
    """Provide a synchronous alias for the async client used in tests."""
    return async_client

# Alias fixture for tests that expect a 'test_client' fixture
@pytest.fixture
def test_client(async_client: AsyncClient) -> AsyncClient:
    """Alias for 'client' to maintain backward compatibility with tests expecting 'test_client'."""
    return async_client

# Configuration fixtures
@pytest.fixture
def mock_service_context():
    """Provide a simple mock service context for DI tests."""
    from unittest.mock import MagicMock
    return MagicMock()

@pytest.fixture
def test_settings():
    """Test-specific settings override."""
    class TestSettings:
        TESTING = True
        SQL_ECHO = False
        DATABASE_URL = TEST_DATABASE_URL
        SECRET_KEY = "test-secret-key"
        ACCESS_TOKEN_EXPIRE_MINUTES = 30
        ALGORITHM = "HS256"
    return TestSettings()
