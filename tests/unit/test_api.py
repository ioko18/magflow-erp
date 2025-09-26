"""
Test cases for MagFlow API endpoints.
This module contains test cases for the main API endpoints of the MagFlow ERP system.
It tests CRUD operations for products and categories, as well as search functionality.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

def get_test_product():
    """Return a test product dictionary."""
    return {
        "name": "Test Product",
        "sku": "TEST-PROD-001",
        "price": 99.99,
        "currency": "RON",
        "description": "A test product",
        "stock_quantity": 10,
        "status": "active",
        "is_active": True,
        "category_id": 1,
        "images": [
            {
                "url": "https://example.com/test.jpg",
                "is_main": True,
                "position": 0,
                "alt": "Test Product"
            }
        ],
        "characteristics": [
            {
                "id": 1,
                "name": "color",
                "value": "red",
                "unit": None
            },
            {
                "id": 2,
                "name": "size",
                "value": "M",
                "unit": None
            }
        ]
    }

def get_test_category():
    return {
        "name": "Test Category",
        "description": "A test category",
        "slug": "test-category",
        "is_active": True
    }

# Import fixtures from our test client module
pytest_plugins = ["tests.conftest"]

@pytest_asyncio.fixture
async def test_product(client: AsyncClient) -> dict:
    """Create a test product and return its data."""
    response = await client.post("/api/v1/catalog/products", json=get_test_product())
    assert response.status_code == 201
    product_data = response.json()
    yield product_data
    # Cleanup
    await client.delete(f"/api/v1/catalog/products/{product_data['id']}")

@pytest.fixture
def test_product_id(test_product: dict) -> str:
    """Return the ID of the test product."""
    return str(test_product["id"])

class TestProductEndpoints:
    """Tests for product endpoints."""
    
    async def test_create_product(self, client: AsyncClient):
        """Test creating a new product."""
        response = await client.post(
            "/api/v1/catalog/products", 
            json=get_test_product()
        )
        assert response.status_code == 201
        data = response.json()
        test_product = get_test_product()
        assert data["name"] == test_product["name"]
        assert data["price"] == test_product["price"]
        assert "id" in data

        product_id = data["id"]

        # Ensure the created product is removed to keep tests isolated
        cleanup_response = await client.delete(f"/api/v1/catalog/products/{product_id}")
        assert cleanup_response.status_code in (200, 204)

    async def test_get_product(self, client: AsyncClient, test_product: dict):
        """Test retrieving a product by ID."""
        product_id = test_product["id"]
        response = await client.get(f"/api/v1/catalog/products/{product_id}")
        assert response.status_code == 200
        data = response.json()
        assert str(data["id"]) == str(product_id)
        assert data["name"] == test_product["name"]

    async def test_list_products(self, client: AsyncClient, test_product: dict):
        """Test listing products with pagination."""
        # Debug: Print the test product ID for reference
        print(f"Test product ID: {test_product['id']}")
        
        # Make the request
        url = "/api/v1/catalog/products"
        params = {
            "sort_by": "created_at",
            "sort_direction": "desc",
            "limit": 20,
            "include_inactive": True
        }
        print(f"Making request to: {url} with params: {params}")
        
        response = await client.get(url, params=params)
        
        # Debug: Print the response status and content
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text}")
        
        # If the response is JSON, print it in a more readable format
        if 'application/json' in response.headers.get('content-type', ''):
            try:
                print("Response JSON:", response.json())
            except ValueError:
                print("Could not parse response as JSON")
        assert response.status_code == 200
        payload = response.json()
        assert "data" in payload
        items = payload["data"] if isinstance(payload["data"], list) else payload.get("data", {}).get("items", [])
        assert any(str(p["id"]) == str(test_product["id"]) for p in items)

    async def test_update_product(self, client: AsyncClient, test_product: dict):
        """Test updating a product."""
        product_id = test_product["id"]
        update_data = {
            "name": "Updated Product", 
            "sku": "UPDATED-SKU-001",
            "price": 199.99,
            "description": "Updated description",
            "stock_quantity": 5,
            "status": "active",
            "category_id": 1  # Required field
        }
        response = await client.put(
            f"/api/v1/catalog/products/{product_id}",
            json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["price"] == update_data["price"]
        assert data["description"] == update_data["description"]

    async def test_search_products(self, client: AsyncClient, test_product: dict):
        """Test searching for products."""
        # Search by name
        response = await client.get(
            "/api/v1/catalog/products",
            params={
                "q": test_product['name'],
                "sort_by": "created_at",
                "sort_direction": "desc",
                "limit": 20,
                "include_inactive": True
            },
        )
        assert response.status_code == 200
        payload = response.json()
        items = payload.get("data", [])
        assert isinstance(items, list)
        assert any(str(p["id"]) == str(test_product["id"]) for p in items)

    async def test_delete_product(self, client: AsyncClient, test_product: dict):
        """Test deleting a product."""
        product_id = test_product["id"]

        # First, verify the product exists and is active
        response = await client.get(f"/api/v1/catalog/products/{product_id}")
        assert response.status_code == 200

        # Check if is_active is either None or True (some APIs might not set it on creation)
        product_data = response.json()
        if product_data.get("is_active") is not None:
            assert product_data["is_active"] is True

        # Delete the product
        response = await client.delete(f"/api/v1/catalog/products/{product_id}")

        # Some APIs return 200 with the updated resource, others return 204 No Content
        if response.status_code == 200:
            # If the API returns the updated product, check is_active is False
            data = response.json()
            assert data.get("is_active") is False
        else:
            # If the API returns 204, verify the product is marked as inactive
            assert response.status_code == 204

            # Verify the product is marked as inactive
            response = await client.get(
                f"/api/v1/catalog/products/{product_id}",
                params={"include_inactive": "true"},
            )
            assert response.status_code == 200
            data = response.json()
            # Check if is_active is explicitly set to False or None (some APIs might use None for soft delete)
            assert data.get("is_active") is not True
