"""
High-Performance Test Configuration for MagFlow ERP

This module provides optimized test fixtures and configuration to dramatically
reduce test setup times from 0.5-1.1 seconds to under 0.1 seconds per test.

Key optimizations:
1. Shared database engine with session scope
2. Optimized connection pooling
3. Schema caching between tests
4. Nested transactions for fast rollbacks
5. Reduced fixture overhead
"""

import asyncio
from pathlib import Path
import sys
from typing import AsyncGenerator

import asyncpg
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import pytest
import pytest_asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
import redis.asyncio as redis

from app.core.config import settings
from app.db.base_class import Base
from app.db.session import get_async_db
from app.db import get_db
from app.api.tasks import router as tasks_router

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Override database settings for testing
settings.TESTING = True

# Optimized test database URL
TEST_DATABASE_URL = (
    "postgresql+asyncpg://magflow_dev:dev_password@localhost:5432/magflow_dev"
)

# Global shared engine (session-scoped)
_shared_engine: AsyncEngine = None
_schema_initialized = False


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


async def ensure_test_database():
    """Ensure the test database exists and is accessible."""
    global _schema_initialized

    if _schema_initialized:
        return

    # Test connection to existing database
    try:
        test_conn = await asyncpg.connect(
            TEST_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        )
        await test_conn.close()
        _schema_initialized = True
    except Exception as e:
        print(f"Warning: Could not connect to test database: {e}")
        _schema_initialized = False


@pytest_asyncio.fixture(scope="session")
async def shared_db_engine():
    """Create a shared database engine for the entire test session."""
    global _shared_engine

    if _shared_engine is None:
        # Ensure database exists
        await ensure_test_database()

        # Create optimized engine with connection pooling
        _shared_engine = create_async_engine(
            TEST_DATABASE_URL,
            echo=False,  # Disable SQL echo for performance
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=5,  # Smaller pool for tests
            max_overflow=10,
            pool_timeout=10,
            # Optimize for test performance
            connect_args={
                "server_settings": {
                    "application_name": "magflow-test",
                    "statement_timeout": "30s",
                },
                "command_timeout": 30,
            },
        )

        # Create schema once per session
        async with _shared_engine.begin() as conn:
            # Only drop/create if needed
            try:
                result = await conn.execute(
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'app'"
                )
                table_count = result.scalar()
                if table_count < 10:  # Assume we need to recreate schema
                    await conn.run_sync(Base.metadata.drop_all)
                    await conn.run_sync(Base.metadata.create_all)
            except Exception:
                # If there's any issue, recreate schema
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)

    yield _shared_engine

    # Cleanup at end of session
    if _shared_engine:
        await _shared_engine.dispose()
        _shared_engine = None


@pytest_asyncio.fixture
async def optimized_db_session(shared_db_engine: AsyncEngine):
    """Create an optimized database session with nested transactions."""
    # Create a connection and start a transaction
    connection = await shared_db_engine.connect()
    transaction = await connection.begin()

    # Create a session bound to this connection
    session_factory = sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        future=True,
    )

    session = session_factory()

    # Start a nested transaction (savepoint)
    nested_transaction = await session.begin_nested()

    try:
        yield session
    finally:
        # Roll back the nested transaction (very fast)
        await nested_transaction.rollback()
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def fast_async_client(
    shared_db_engine: AsyncEngine,
) -> AsyncGenerator[AsyncClient, None]:
    """Create a fast async test client with optimized database dependency."""
    from app.api.v1.api import api_router as v1_router
    from app.api.health import router as health_router
    from app.api.admin import router as admin_router
    from app.api.well_known import router as well_known_router

    # Create a lightweight FastAPI app for testing
    test_app = FastAPI(title="MagFlow Test API")

    # Add minimal middleware
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include essential routers
    test_app.include_router(health_router, prefix="/health", tags=["health"])
    test_app.include_router(v1_router, prefix=settings.API_V1_STR)
    test_app.include_router(admin_router, prefix="/admin", tags=["admin"])
    test_app.include_router(
        well_known_router, prefix="/.well-known", tags=["well-known"]
    )
    test_app.include_router(tasks_router, prefix=f"{settings.API_V1_STR}/tasks")

    # Optimized database dependency override
    async def fast_override_get_db():
        connection = await shared_db_engine.connect()
        session_factory = sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            future=True,
        )
        session = session_factory()
        try:
            yield session
        finally:
            await session.close()
            await connection.close()

    test_app.dependency_overrides[get_async_db] = fast_override_get_db
    test_app.dependency_overrides[get_db] = fast_override_get_db

    # Minimal Redis setup (or skip if not available)
    @test_app.on_event("startup")
    async def startup():
        try:
            redis_client = redis.Redis(
                host="localhost", port=6379, db=0, decode_responses=True
            )
            await FastAPILimiter.init(test_app, redis_client)
        except Exception:
            # Skip Redis if not available
            await FastAPILimiter.init(test_app)

    # Create test client
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
        timeout=10.0,  # Shorter timeout for tests
    ) as client:
        yield client


# Performance test fixtures
@pytest_asyncio.fixture
async def fast_test_category(optimized_db_session: AsyncSession):
    """Create a test category quickly."""
    from app.models.category import Category
    from uuid import uuid4

    category = Category(
        name=f"Test Category {str(uuid4())[:8]}", description="A test category"
    )

    optimized_db_session.add(category)
    await optimized_db_session.commit()
    await optimized_db_session.refresh(category)

    return category


@pytest_asyncio.fixture
async def fast_test_product(optimized_db_session: AsyncSession, fast_test_category):
    """Create a test product quickly."""
    from app.models.product import Product
    from uuid import uuid4

    product = Product(
        name=f"Test Product {uuid4().hex[:8]}",
        sku=f"TEST-{uuid4().hex[:8]}",
        base_price=99.99,
        currency="USD",
        description="A test product",
        is_active=True,
    )

    product.categories.append(fast_test_category)
    optimized_db_session.add(product)
    await optimized_db_session.commit()
    await optimized_db_session.refresh(product)

    return product


# Utility functions for performance testing
def get_fast_test_product_data(**overrides):
    """Return optimized test product data."""
    from uuid import uuid4

    default_data = {
        "name": f"Fast Product {uuid4().hex[:8]}",
        "sku": f"FAST-{uuid4().hex[:8]}".upper(),
        "base_price": 99.99,
        "currency": "USD",
        "description": "A fast test product",
        "is_active": True,
    }
    return {**default_data, **overrides}


# Performance monitoring
class TestPerformanceMonitor:
    """Monitor test performance and provide optimization suggestions."""

    def __init__(self):
        self.setup_times = []
        self.execution_times = []

    def record_setup_time(self, duration: float):
        """Record test setup time."""
        self.setup_times.append(duration)

    def record_execution_time(self, duration: float):
        """Record test execution time."""
        self.execution_times.append(duration)

    def get_performance_report(self):
        """Get performance optimization report."""
        if not self.setup_times:
            return "No performance data available"

        avg_setup = sum(self.setup_times) / len(self.setup_times)
        avg_execution = sum(self.execution_times) / len(self.execution_times)

        return f"""
Performance Report:
- Average setup time: {avg_setup:.3f}s
- Average execution time: {avg_execution:.3f}s
- Total tests: {len(self.setup_times)}
- Performance target: <0.1s setup time
- Status: {'✅ OPTIMIZED' if avg_setup < 0.1 else '⚠️ NEEDS OPTIMIZATION'}
"""


# Global performance monitor
performance_monitor = TestPerformanceMonitor()
