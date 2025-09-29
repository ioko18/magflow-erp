"""Optimized Test cases for MagFlow Products API endpoints.
This module contains optimized test cases for the products API endpoints.
"""

import logging
import uuid
from typing import Dict, Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# This file now uses the optimized fixtures from conftest.py
# No need for custom database setup - using shared optimized fixtures


# Test cases using optimized fixtures
@pytest.mark.asyncio
async def test_create_product(async_client: AsyncClient, test_category: Dict[str, Any]):
    """Test creating a new product."""
    product_data = {
        "name": f"Test Product {uuid.uuid4().hex[:8]}",
        "description": "A test product",
        "sku": f"SKU-{uuid.uuid4().hex[:6]}",
        "base_price": 99.99,
        "currency": "USD",
        "is_active": True,
        "category_ids": [test_category["id"]],
    }

    response = await async_client.post("/api/v1/products/", json=product_data)
    assert response.status_code == 201, f"Failed to create product: {response.text}"
    data = response.json()
    assert data["name"] == product_data["name"]
    assert data["sku"] == product_data["sku"]
    assert float(data["base_price"]) == product_data["base_price"]
    assert data["is_active"] == product_data["is_active"]


@pytest.mark.asyncio
async def test_get_product(
    async_client: AsyncClient, test_product: Dict[str, Any], db_session: AsyncSession
):
    """Test retrieving a product by ID."""
    logger.info("Starting optimized test_get_product...")

    try:
        # Verify the product exists in the database
        result = await db_session.execute(
            select(Product).filter_by(id=test_product["id"])
        )
        db_product = result.scalar_one_or_none()
        assert (
            db_product is not None
        ), f"Test product not found in database: {test_product['id']}"

        # Make the API request
        url = f"/api/v1/products/{test_product['id']}"
        response = await async_client.get(url)

        assert response.status_code == 200, f"Failed to get product: {response.text}"

        data = response.json()

        # Verify the response data
        assert data["id"] == test_product["id"]
        assert data["name"] == test_product["name"]
        assert data["sku"] == test_product["sku"]
        assert float(data["base_price"]) == float(test_product["base_price"])

        logger.info("test_get_product completed successfully")

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise


@pytest.mark.asyncio
async def test_list_products(async_client: AsyncClient, test_product: Dict[str, Any]):
    """Test listing all products."""
    response = await async_client.get("/api/v1/products/")
    assert response.status_code == 200, f"Failed to list products: {response.text}"
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    assert any(p["id"] == test_product["id"] for p in data["items"])


@pytest.mark.asyncio
async def test_update_product(async_client: AsyncClient, test_product: Dict[str, Any]):
    """Test updating a product."""
    update_data = {
        "name": "Updated Product Name",
        "description": "Updated description",
        "base_price": 199.99,
        "is_active": False,
    }

    response = await async_client.put(
        f"/api/v1/products/{test_product['id']}",
        json=update_data,
    )
    assert response.status_code == 200, f"Failed to update product: {response.text}"
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]
    assert float(data["base_price"]) == update_data["base_price"]
    assert data["is_active"] == update_data["is_active"]


@pytest.mark.asyncio
async def test_delete_product(async_client: AsyncClient, test_product: Dict[str, Any]):
    """Test deleting a product."""
    # First, get the product to ensure it exists
    response = await async_client.get(f"/api/v1/products/{test_product['id']}")
    assert response.status_code == 200

    # Delete the product
    response = await async_client.delete(f"/api/v1/products/{test_product['id']}")
    assert response.status_code == 204

    # Verify the product is deleted
    response = await async_client.get(f"/api/v1/products/{test_product['id']}")
    assert response.status_code == 404
