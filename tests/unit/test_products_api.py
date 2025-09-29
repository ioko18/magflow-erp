"""
Test cases for MagFlow Products API endpoints.
This module contains test cases for the products API endpoints.
"""

import os
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.sql import text

from app.models.base import Base
from app.db.session import get_async_db
from app.models.category import Category
from app.models.product import Product
from app.main import app as fastapi_app

# Set test environment
os.environ["ENVIRONMENT"] = "test"

# Use the same test database configuration as other tests
from tests.config import test_config

TEST_DATABASE_URL = test_config.TEST_DB_URL
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create a test database engine with schema."""
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=True,  # Enable SQL echo for debugging
        pool_pre_ping=True,
        pool_recycle=300,
    )

    # Create tables for each test function
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield test_engine

    # Cleanup after test
    await test_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    """Create a test database session with automatic rollback."""
    from sqlalchemy.orm import sessionmaker

    # Create a session factory
    session_factory = sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    """Create a test client with overridden dependencies."""

    # Override the database dependency
    async def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_async_db] = override_get_db

    try:
        # Create test client
        async with AsyncClient(
            transport=ASGITransport(app=fastapi_app), base_url="http://test"
        ) as test_client:
            yield test_client
    finally:
        # Clean up
        fastapi_app.dependency_overrides.clear()


# Test data fixtures
@pytest_asyncio.fixture(scope="function")
async def test_category(db_session):
    """Create a test category."""
    category = Category(
        name=f"Test Category {uuid4().hex[:8]}",
        description="A test category",
    )
    db_session.add(category)
    await db_session.flush()
    await db_session.refresh(category)
    return category


@pytest_asyncio.fixture(scope="function")
async def test_product(db_session, test_category):
    """Create a test product with all required fields."""
    product = Product(
        name=f"Test Product {uuid4().hex[:8]}",
        sku=f"SKU-{uuid4().hex[:6]}",
        base_price=99.99,
        description="A test product",
        is_active=True,
        currency="RON",  # Required field
    )
    product.categories.append(test_category)
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    # Verify the product was created with an ID
    assert product.id is not None, "Product ID should be generated"
    print(f"Created test product with ID: {product.id}")

    return product


@pytest.mark.asyncio
async def test_create_product(client: AsyncClient, test_category, db_session):
    """Test creating a new product with all required fields."""
    import secrets

    # Get the category ID, handling both UUID and integer IDs
    category_id = test_category.id
    if hasattr(category_id, "int"):  # If it's a UUID, use the integer value
        category_id = category_id.int

    # Create a unique product name and SKU
    unique_suffix = secrets.token_hex(4)
    product_name = f"Test Product {unique_suffix}"
    sku = f"SKU-{unique_suffix}"

    # Prepare product data according to ProductBase schema
    product_data = {
        "name": product_name,
        "description": "A test product",
        "sku": sku,
        "price": 99.99,  # Required field
        "currency": "RON",  # Required field
        "status": "active",  # Required field
        "is_active": True,
        "stock_quantity": 0,
        "category_id": category_id,
        "characteristics": [],
        "metadata": {},
    }

    print(f"Creating product with data: {product_data}")

    # Make the request with proper headers
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    # First, check if the product with the same SKU already exists
    existing_product = await db_session.execute(
        text("SELECT id FROM app.products WHERE sku = :sku"), {"sku": sku}
    )
    if existing_product.scalar():
        print(f"Product with SKU {sku} already exists, skipping test")
        return

    # Create the product
    response = await client.post("/api/v1/products", json=product_data, headers=headers)

    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")

    # Check if the request was successful
    assert response.status_code == 201, f"Failed to create product: {response.text}"

    # Parse the response data
    data = response.json()
    print(f"Created product with ID: {data.get('id')}")

    # Verify the response data
    assert (
        data["name"] == product_name
    ), f"Expected name {product_name}, got {data.get('name')}"
    assert data["sku"] == sku, f"Expected SKU {sku}, got {data.get('sku')}"
    assert (
        data["is_active"] is True
    ), f"Expected is_active to be True, got {data.get('is_active')}"
    assert (
        float(data["base_price"]) == 99.99
    ), f"Expected base_price to be 99.99, got {data.get('base_price')}"
    assert (
        data["currency"] == "RON"
    ), f"Expected currency to be 'RON', got {data.get('currency')}"

    # Verify the product was created in the database
    product_id = data["id"]
    if hasattr(product_id, "int"):  # If it's a UUID, convert to int
        product_id = product_id.int

    # Use a new session to verify the product exists
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from app.core.config import settings

    # Create a new engine and session for verification
    engine = create_async_engine(settings.DB_URI)
    async with AsyncSession(engine) as verify_session:
        # Verify the product exists
        result = await verify_session.execute(
            text("SELECT * FROM app.products WHERE id = :id"), {"id": product_id}
        )
        db_product = result.mappings().first()

        print(f"Database product: {db_product}")
        assert (
            db_product is not None
        ), f"Product with ID {product_id} not found in database"

        # Verify the product data
        assert (
            db_product["name"] == product_name
        ), f"Expected name {product_name}, got {db_product['name']}"
        assert db_product["sku"] == sku, f"Expected SKU {sku}, got {db_product['sku']}"
        assert (
            db_product["is_active"] is True
        ), f"Expected is_active to be True, got {db_product['is_active']}"
        assert (
            float(db_product["base_price"]) == 99.99
        ), f"Expected base_price to be 99.99, got {db_product['base_price']}"
        assert (
            db_product["currency"] == "RON"
        ), f"Expected currency to be 'RON', got {db_product['currency']}"

    # Clean up
    await engine.dispose()


@pytest.mark.asyncio
async def test_list_products(client: AsyncClient, test_product):
    """Test listing all products."""
    response = await client.get("/api/v1/products")
    assert response.status_code == 200, f"Failed to list products: {response.text}"

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1

    # Convert test_product.id to string for comparison
    test_product_id = str(test_product.id)
    if hasattr(test_product.id, "int"):  # If it's a UUID, use the integer value
        test_product_id = str(test_product.id.int)

    assert any(str(p["id"]) == test_product_id for p in data["items"])


@pytest_asyncio.fixture
async def verify_db_session():
    """Fixture to provide a separate database session for verification."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from app.core.config import settings

    # Create a new engine and session
    engine = create_async_engine(settings.DB_URI)
    async with AsyncSession(engine) as session:
        yield session

    # Clean up
    await engine.dispose()


@pytest.mark.asyncio
async def test_update_product(client: AsyncClient, test_product, db_session):
    """Test updating a product."""
    # Get the numeric ID from the product object
    product_id = test_product.id
    if hasattr(product_id, "int"):  # If it's a UUID, convert to int
        product_id = product_id.int

    update_data = {
        "name": "Updated Product Name",
        "description": "Updated description",
        "is_active": False,
        "currency": "RON",  # Required by the API
    }

    response = await client.put(
        f"/api/v1/products/{product_id}",
        json=update_data,
    )
    assert response.status_code == 200, f"Failed to update product: {response.text}"
    data = response.json()

    # Verify the response
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]
    assert data["is_active"] == update_data["is_active"]
    assert data["currency"] == update_data["currency"]
    # Verify the product was updated in the database using the verify session
    db_product = await db_session.get(Product, test_product.id)
    assert (
        db_product is not None
    ), f"Product with ID {test_product.id} was not updated in the database"
    assert (
        db_product.name == update_data["name"]
    ), f"Expected name {update_data['name']}, got {db_product.name}"
    assert (
        db_product.description == update_data["description"]
    ), f"Expected description {update_data['description']}, got {db_product.description}"
    assert (
        db_product.is_active == update_data["is_active"]
    ), f"Expected is_active {update_data['is_active']}, got {db_product.is_active}"
    assert (
        db_product.currency == update_data["currency"]
    ), f"Expected currency {update_data['currency']}, got {db_product.currency}"


@pytest.mark.asyncio
async def test_delete_product(client: AsyncClient, test_product, db_session):
    """Test deleting a product."""
    response = await client.delete(f"/api/v1/products/{test_product.id}")
    product_id = test_product.id
    if hasattr(product_id, "int"):  # If it's a UUID, convert to int
        product_id = product_id.int

    # Delete the product
    response = await client.delete(f"/api/v1/products/{product_id}")
    assert response.status_code == 200, f"Failed to delete product: {response.text}"

    # Verify the product is deleted
    db_product = await db_session.get(Product, product_id)
    assert db_product is None or db_product.is_deleted is True
    result = await db_session.execute(
        text("SELECT id FROM app.products WHERE id = :id"), {"id": product_id}
    )
    assert (
        result.scalar_one_or_none() is None
    ), "Product should be deleted from the database"
