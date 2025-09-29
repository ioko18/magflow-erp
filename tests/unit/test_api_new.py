"""
Test cases for MagFlow API endpoints.
This module contains test cases for the main API endpoints of the MagFlow ERP system.
"""

from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product as ProductModel
from app.models.category import Category as CategoryModel

pytestmark = pytest.mark.asyncio


def get_test_product(**overrides):
    """Return a test product dictionary with valid data."""
    default_data = {
        "name": f"Test Product {uuid4().hex[:8]}",
        "sku": f"TEST-{uuid4().hex[:8]}".upper(),
        "base_price": 99.99,
        "currency": "USD",
        "description": "A test product",
        "is_active": True,
        "images": ["https://example.com/image1.jpg"],
        "characteristics": [{"name": "color", "value": "red"}],
    }
    return {**default_data, **overrides}


@pytest.mark.asyncio
async def test_create_product(async_client: AsyncClient, db_session: AsyncSession):
    """Test creating a new product."""
    product_data = get_test_product()

    # Create a test category
    category = CategoryModel(name="Test Category", description="Test Description")
    db_session.add(category)
    await db_session.commit()

    # Set the category ID
    product_data["category_ids"] = [category.id]

    # Create the product
    response = await async_client.post("/api/v1/products/", json=product_data)
    assert response.status_code == status.HTTP_201_CREATED

    # Verify the response data
    response_data = response.json()
    assert response_data["name"] == product_data["name"]
    assert response_data["sku"] == product_data["sku"]
    assert float(response_data["base_price"]) == product_data["base_price"]

    # Cleanup
    await db_session.delete(category)
    await db_session.commit()


@pytest.mark.asyncio
async def test_get_product(async_client: AsyncClient, db_session: AsyncSession):
    """Test retrieving a product by ID."""
    # Create a test product
    product_data = get_test_product()
    product = ProductModel(
        name=product_data["name"],
        sku=product_data["sku"],
        base_price=product_data["base_price"],
        description=product_data["description"],
        currency=product_data["currency"],
    )
    db_session.add(product)
    await db_session.commit()

    # Test retrieval
    response = await async_client.get(f"/api/v1/products/{product.id}")
    assert response.status_code == status.HTTP_200_OK

    # Verify the response data
    response_data = response.json()
    assert response_data["id"] == product.id
    assert response_data["name"] == product.name

    # Cleanup
    await db_session.delete(product)
    await db_session.commit()


@pytest.mark.asyncio
async def test_delete_product(async_client: AsyncClient, db_session: AsyncSession):
    """Test deleting a product."""
    # Create a test product
    product_data = get_test_product()
    product = ProductModel(
        name=product_data["name"],
        sku=product_data["sku"],
        base_price=product_data["base_price"],
        currency="USD",
    )
    db_session.add(product)
    await db_session.commit()

    # Test deletion
    delete_response = await async_client.delete(f"/api/v1/products/{product.id}")
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    # Verify deletion
    get_response = await async_client.get(f"/api/v1/products/{product.id}")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND
