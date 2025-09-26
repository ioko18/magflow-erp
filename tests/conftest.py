"""
Test configuration for MagFlow ERP.

This module provides test fixtures and configuration for the MagFlow ERP test suite.
"""

# Standard library imports
import inspect
import sys
from pathlib import Path
from typing import AsyncGenerator

# Third-party imports
import pytest_asyncio
from httpx import AsyncClient
from httpx import ASGITransport
from fastapi import status
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import JSON as SQLAlchemyJSON
import json

# Application imports
from app.core.database import get_async_session
from app.db import get_db
from app.main import app
from app.core.config import settings
from app.models.base import Base
from app.services.cache_service import CacheManager, get_cache_service

# Import all models to ensure they are registered with SQLAlchemy
# The imports are used by SQLAlchemy's metadata, so we suppress unused import warnings
from app.models import (  # noqa: F401
    User, Role, Permission, RefreshToken, Product, Category,
    Warehouse, StockMovement, InventoryItem, Order, OrderLine,
    Customer, Supplier, PurchaseOrder, PurchaseOrderLine,
    PurchaseReceipt, PurchaseReceiptLine, SupplierPayment,
    PurchaseRequisition, PurchaseRequisitionLine, Invoice,
    InvoiceItem, CancellationRequest, CancellationItem,
    CancellationRefund, EmagCancellationIntegration,
    ReturnRequest, ReturnItem, RefundTransaction,
    EmagReturnIntegration, EmagProductOffer, EmagOfferSync,
    UserSession, AuditLog
)

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Override database settings for testing
TEST_DB_URL = "sqlite+aiosqlite:///:memory:?cache=shared"
settings.SQL_ECHO = False  # Disable SQL echo for cleaner test output
settings.TESTING = True


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """
    Create a test database engine with proper schema setup.

    This fixture creates a PostgreSQL database with all application
    models properly initialized. The database is created once per test session
    and properly cleaned up after all tests complete.
    """
    # Create a custom JSON type for SQLite
    from sqlalchemy.types import TypeDecorator, VARCHAR
    
    class JSONEncodedDict(TypeDecorator):
        """Represents an immutable structure as a json-encoded string."""
        impl = VARCHAR
        
        def load_dialect_impl(self, dialect):
            if dialect.name == 'postgresql':
                return dialect.type_descriptor(SQLAlchemyJSON())
            else:
                return dialect.type_descriptor(self.impl)
        
        def process_bind_param(self, value, dialect):
            if value is not None:
                value = json.dumps(value)
            return value
        
        def process_result_value(self, value, dialect):
            if value is not None:
                value = json.loads(value)
            return value
    
    # Replace JSONB with our custom type for SQLite and remove schema references
    from sqlalchemy.dialects.postgresql import JSONB
    
    def _patch_for_sqlite():
        # Patch JSONB columns and strip schema-qualified references that SQLite
        # does not understand.
        for table in Base.metadata.tables.values():
            # Remove schema for SQLite
            table.schema = None

            # Replace JSONB with our custom type
            for column in table.columns:
                if isinstance(column.type, JSONB):
                    column.type = JSONEncodedDict()

                # Strip schema prefix from column-level foreign keys (e.g. "app.roles.id")
                for fk in list(column.foreign_keys):
                    colspec = fk._get_colspec()
                    if colspec and "." in colspec:
                        fk._colspec = colspec.split(".", 1)[1]

            # Also strip schema prefixes from table-level foreign key constraints
            for fk_constraint in list(table.foreign_key_constraints):
                for element in fk_constraint.elements:
                    colspec = element.target_fullname
                    if colspec and "." in colspec:
                        element._colspec = colspec.split(".", 1)[1]
                        element._resolved_target = None
    
    # Create engine with SQLite in-memory database
    engine = create_async_engine(
        TEST_DB_URL,
        echo=settings.SQL_ECHO,
        future=True,
        connect_args={"check_same_thread": False},
        json_serializer=json.dumps,
        json_deserializer=json.loads,
        poolclass=StaticPool,
    )
    
    _patch_for_sqlite()
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a transactional database session for tests."""
    session_factory = async_sessionmaker(
        bind=db_engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        transaction = await session.begin()
        try:
            yield session
        finally:
            await transaction.rollback()
            await session.close()


@pytest_asyncio.fixture
async def clean_db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a session that commits changes for tests that need persistence."""
    session_factory = async_sessionmaker(
        bind=db_engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture
async def client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for the FastAPI application."""

    async_session_factory = async_sessionmaker(
        bind=db_engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    from app.core import database as core_database_module
    from app import db as db_module
    from app.services import cache_service as cache_module

    original_core_engine = getattr(core_database_module, "engine", None)
    original_core_factory = getattr(core_database_module, "async_session_factory", None)
    original_db_factory = getattr(db_module, "AsyncSessionFactory", None)
    original_get_async_session = getattr(core_database_module, "get_async_session", None)
    original_get_db_dependency = getattr(db_module, "get_db", None)
    original_cache_service_instance = getattr(cache_module, "cache_service", None)
    original_get_cache_service = getattr(cache_module, "get_cache_service", None)
    original_redis_enabled = getattr(settings, "REDIS_ENABLED", False)

    core_database_module.engine = db_engine
    core_database_module.async_session_factory = async_session_factory
    db_module.AsyncSessionFactory = async_session_factory

    settings.REDIS_ENABLED = False

    class InMemoryCacheService:
        def __init__(self):
            self.store = {}

        async def connect(self):
            return

        async def is_connected(self):
            return True

        def _key(self, namespace: str, key: str) -> tuple[str, str]:
            return (namespace, key)

        async def get(self, key, namespace="default"):
            return self.store.get(self._key(namespace, key))

        async def set(self, key, value, ttl=None, namespace="default"):
            self.store[self._key(namespace, key)] = value
            return True

        async def delete(self, key, namespace="default"):
            self.store.pop(self._key(namespace, key), None)
            return True

        async def delete_pattern(self, pattern, namespace="default"):
            prefix = pattern.rstrip("*")
            to_delete = [k for k in self.store if k[0] == namespace and k[1].startswith(prefix)]
            for k in to_delete:
                self.store.pop(k, None)
            return len(to_delete)

        async def invalidate_user_cache(self, user_id: int):
            await self.delete(f"user:{user_id}:permissions", "permissions")
            await self.delete_pattern(f"user:{user_id}:", "sessions")
            return True

        async def get_or_set(self, key, value_func, ttl=None, namespace="default"):
            existing = await self.get(key, namespace)
            if existing is not None:
                return existing

            if callable(value_func):
                value_candidate = value_func()
                if inspect.isawaitable(value_candidate):
                    value_candidate = await value_candidate
            else:
                value_candidate = value_func

            await self.set(key, value_candidate, ttl, namespace)
            return value_candidate

        async def get_cache_stats(self):
            return {
                "connected": True,
                "used_memory": 0,
                "used_memory_peak": 0,
                "total_connections": len(self.store),
            }

    cache_stub = InMemoryCacheService()

    async def override_get_cache_service_dependency():
        return CacheManager(cache_stub)

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    core_database_module.get_async_session = override_get_session
    db_module.get_db = override_get_db
    cache_module.cache_service = cache_stub
    cache_module.get_cache_service = override_get_cache_service_dependency

    app.dependency_overrides[get_async_session] = override_get_session
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_cache_service] = override_get_cache_service_dependency

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        if original_core_engine is not None:
            core_database_module.engine = original_core_engine
        if original_core_factory is not None:
            core_database_module.async_session_factory = original_core_factory
        if original_db_factory is not None:
            db_module.AsyncSessionFactory = original_db_factory
        if original_get_async_session is not None:
            core_database_module.get_async_session = original_get_async_session
        if original_get_db_dependency is not None:
            db_module.get_db = original_get_db_dependency
        if original_cache_service_instance is not None:
            cache_module.cache_service = original_cache_service_instance
        if original_get_cache_service is not None:
            cache_module.get_cache_service = original_get_cache_service
        settings.REDIS_ENABLED = original_redis_enabled


@pytest_asyncio.fixture
async def async_client(client: AsyncClient) -> AsyncGenerator[AsyncClient, None]:
    """Provide a backwards-compatible alias for the async HTTP client."""

    yield client


# Authentication helpers


@pytest_asyncio.fixture
async def test_user(clean_db_session) -> dict:
    """Ensure a baseline test user exists in the database."""
    from sqlalchemy import select

    from app.core.security import get_password_hash
    from app.models.user import User as UserModel

    email = "test@example.com"

    result = await clean_db_session.execute(select(UserModel).where(UserModel.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        user = UserModel(
            email=email,
            full_name="Test User",
            hashed_password=get_password_hash("testpassword"),
            is_active=True,
            is_superuser=False,
        )
        clean_db_session.add(user)
        await clean_db_session.commit()
        await clean_db_session.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "password": "testpassword",
    }


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, test_user: dict) -> dict[str, str]:
    """Obtain Authorization header by logging in the baseline test user."""

    response = await client.post(
        f"{settings.API_V1_STR}/auth/login",
        data={
            "username": test_user["email"],
            "password": test_user["password"],
        },
    )

    if response.status_code != status.HTTP_200_OK:
        raise RuntimeError(f"Failed to authenticate test user: {response.text}")

    token_data = response.json()
    return {
        "Authorization": f"Bearer {token_data['access_token']}",
    }

@pytest_asyncio.fixture
def mock_redis():
    """Mock Redis client for testing."""
    class MockRedis:
        def __init__(self):
            self.data = {}

        async def get(self, key):
            return self.data.get(key)

        async def set(self, key, value, ex=None):
            self.data[key] = value

        async def delete(self, key):
            self.data.pop(key, None)

    return MockRedis()


# Test data fixtures
@pytest_asyncio.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "full_name": "Test User",
        "password": "test_password123",
        "is_active": True
    }


@pytest_asyncio.fixture
def sample_product_data():
    """Sample product data for testing."""
    return {
        "emag_id": "test-123",
        "name": "Test Product",
        "price": 99.99,
        "stock": 10,
        "is_active": True
    }


# Configuration fixtures
@pytest_asyncio.fixture(scope="session")
def test_settings():
    """Test-specific settings override."""
    # Store original settings
    original_settings = {
        "SQL_ECHO": settings.SQL_ECHO,
        "TESTING": settings.TESTING
    }

    # Override for testing
    settings.SQL_ECHO = False
    settings.TESTING = True

    yield settings

    # Restore original settings
    for key, value in original_settings.items():
        setattr(settings, key, value)
