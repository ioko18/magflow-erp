"""
Test cases for MagFlow Products API endpoints.
This module contains test cases for the products API endpoints.
"""
import asyncio
from unittest.mock import patch
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.api.products import router as products_router
from app.db.session import get_async_db
from app.models.category import Category
from app.models.product import Product

# Test database configuration - using the main database with test schema
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/magflow"
TEST_SCHEMA = "app"

# Event loop fixture
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Database setup and teardown
@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a test database with tables and return a session."""
    # Create engine and connect to the test database
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    
    # Set the search path to the test schema
    async with engine.begin() as conn:
        await conn.execute(text(f'SET search_path TO {TEST_SCHEMA}'))
    
    # Create session
    TestingSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

@pytest.fixture(autouse=True)
async def mock_services():
    # Mock rate limiter
    async def mock_rate_limit(*args, **kwargs):
        return None

    # Mock Redis cache
    class MockRedis:
        async def get(self, *args, **kwargs):
            return None

        async def set(self, *args, **kwargs):
            return True

        async def delete(self, *args, **kwargs):
            return True

        async def ping(self):
            return True

        async def close(self):
            pass

    # Mock the CacheManager.get_client method to return our mock Redis
    async def mock_get_client():
        return MockRedis()

    # Apply the mocks
    with patch('app.api.products.rate_limit', new=mock_rate_limit), \
         patch('app.services.redis.CacheManager.get_client', new=mock_get_client):
        yield

# Test client fixture
@pytest.fixture
def client(db_session):
    """Create a test client with overridden dependencies."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.products import router as products_router
    from app.db.session import get_async_db
    
    app = FastAPI()
    app.include_router(products_router, prefix="/api/v1")

    # Override the database dependency
    async def override_get_db():
        try:
            yield db_session
        finally:
            await db_session.close()

    app.dependency_overrides[get_async_db] = override_get_db

    # Create a test client
    with TestClient(app) as test_client:
        yield test_client

# Test data fixtures
@pytest_asyncio.fixture
async def test_category(db_session):
    """Create a test category."""
    category = Category(
        name=f"Test Category {uuid4().hex[:8]}",
        description="A test category",
        is_active=True
    )
    db_session.add(category)
    await db_session.commit()
    return category

@pytest_asyncio.fixture
async def test_product(db_session, test_category):
    """Create a test product."""
    product = Product(
        name=f"Test Product {uuid4().hex[:8]}",
        sku=f"SKU-{uuid4().hex[:6]}",
        base_price=99.99,
        description="A test product",
        is_active=True
    )
    product.categories.append(test_category)
    db_session.add(product)
    await db_session.commit()
    return product

def test_create_product(client, test_category):
    """Test creating a new product."""
    import secrets
    
    product_data = {
        "name": f"Test Product {secrets.token_hex(4)}",
        "description": "A test product",
        "sku": f"SKU-{secrets.token_hex(3)}",
        "base_price": 99.99,
        "is_active": True,
        "category_ids": [test_category.id]
    }
    
    response = client.post("/api/v1/products/", json=product_data)
    assert response.status_code == 201, f"Failed to create product: {response.text}"
    data = response.json()
    assert data["name"] == product_data["name"]
    assert data["sku"] == product_data["sku"]
    assert data["base_price"] == product_data["base_price"]
    assert data["is_active"] == product_data["is_active"]
    assert len(data["categories"]) == 1
    assert data["categories"][0]["id"] == test_category.id

def test_get_product(client, test_product):
    """Test retrieving a product by ID."""
    response = client.get(f"/api/v1/products/{test_product.id}")
    assert response.status_code == 200, f"Failed to get product: {response.text}"
    data = response.json()
    assert data["id"] == test_product.id
    assert data["name"] == test_product.name
    assert data["sku"] == test_product.sku
    assert float(data["base_price"]) == float(test_product.base_price)

def test_list_products(client, test_product):
    """Test listing all products."""
    response = client.get("/api/v1/products/")
    assert response.status_code == 200, f"Failed to list products: {response.text}"
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    assert any(p["id"] == test_product.id for p in data["items"])

def test_update_product(client, test_product):
    """Test updating a product."""
    import secrets
    
    update_data = {
        "name": f"Updated Product {secrets.token_hex(4)}",
        "description": "An updated product",
        "base_price": 199.99,
        "is_active": False
    }
    
    response = client.put(f"/api/v1/products/{test_product.id}", json=update_data)
    assert response.status_code == 200, f"Failed to update product: {response.text}"
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]
    assert data["base_price"] == update_data["base_price"]
    assert data["is_active"] == update_data["is_active"]

def test_delete_product(client, test_product):
    """Test deleting a product."""
    # First verify the product exists
    response = client.get(f"/api/v1/products/{test_product.id}")
    assert response.status_code == 200, "Test product should exist before deletion"
    
    # Delete the product
    response = client.delete(f"/api/v1/products/{test_product.id}")
    assert response.status_code == 204, f"Failed to delete product: {response.text}"
    
    # Verify the product no longer exists
    response = client.get(f"/api/v1/products/{test_product.id}")
    assert response.status_code == 404, f"Product should be deleted but still exists. Status: {response.status_code}, Response: {response.text}"
