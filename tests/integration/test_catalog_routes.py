"""Integration tests for the Catalog API routes."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import status

from app.core.problem import Problem

# Test data
TEST_PRODUCT_ID = uuid4()
TEST_BRAND_ID = 1
TEST_CATEGORY_ID = 1
TEST_CHARACTERISTIC_ID = 1


class TestProductRoutes:
    """Test cases for product-related routes."""

    @pytest.mark.asyncio
    async def test_list_products_success(self, test_client, mock_catalog_service):
        """Test listing products with filters."""
        with patch("app.api.routes.catalog.get_service", return_value=mock_catalog_service):
            response = await test_client.get(
                "/api/v1/catalog/products",
                params={
                    "sort_by": "name",
                    "sort_direction": "asc",
                },
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["data"]) == 0
            assert data["meta"]["total_items"] == 0
            mock_catalog_service.list_products.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_product_success(self, test_client, mock_catalog_service):
        """Test getting a product by ID."""
        with patch("app.api.routes.catalog.get_service", return_value=mock_catalog_service):
            response = await test_client.get(f"/api/v1/catalog/products/{TEST_PRODUCT_ID}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == str(TEST_PRODUCT_ID)
            assert data["name"] == "Test Product"
            mock_catalog_service.get_product_by_id.assert_called_once_with(TEST_PRODUCT_ID)

    @pytest.mark.asyncio
    async def test_get_product_not_found(self, test_client, mock_catalog_service):
        """Test getting a non-existent product."""
        mock_catalog_service.get_product_by_id.side_effect = Problem(
            status=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail=f"Product with ID {TEST_PRODUCT_ID} not found",
        )
        with patch("app.api.routes.catalog.get_service", return_value=mock_catalog_service):
            response = await test_client.get(f"/api/v1/catalog/products/{TEST_PRODUCT_ID}")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert data["detail"] == f"Product with ID {TEST_PRODUCT_ID} not found"
            mock_catalog_service.get_product_by_id.assert_called_once_with(TEST_PRODUCT_ID)

    @pytest.mark.asyncio
    async def test_create_product_success(self, test_client, mock_catalog_service):
        """Test creating a new product."""
        product_data = {
            "name": "New Product",
            "description": "A new product",
            "sku": "NEW-001",
            "price": 199.99,
            "status": "draft",
            "is_active": True,
            "stock_quantity": 0,
            "category_id": 1,
        }

        with patch("app.api.routes.catalog.get_service", return_value=mock_catalog_service):
            response = await test_client.post(
                "/api/v1/catalog/products",
                json=product_data,
            )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["id"] == str(TEST_PRODUCT_ID)
            assert data["name"] == product_data["name"]
            mock_catalog_service.create_product.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_product_validation_error(self, test_client):
        """Test creating a product with invalid data."""
        invalid_data = {
            "name": "",  # Empty name is not allowed
            "price": -10,  # Negative price is not allowed
        }

        response = await test_client.post("/api/v1/catalog/products", json=invalid_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        data = response.json()
        assert "detail" in data
        assert any("name" in error["loc"] for error in data["detail"])
        assert any("price" in error["loc"] for error in data["detail"])

    @pytest.mark.asyncio
    async def test_update_product_success(self, test_client, mock_catalog_service):
        """Test updating a product."""
        update_data = {
            "name": "Updated Product",
            "price": 249.99,
            "stock_quantity": 5,
        }

        with patch("app.api.routes.catalog.get_service", return_value=mock_catalog_service):
            response = await test_client.put(
                f"/api/v1/catalog/products/{TEST_PRODUCT_ID}",
                json=update_data,
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == str(TEST_PRODUCT_ID)
            assert data["name"] == update_data["name"]
            assert data["price"] == update_data["price"]
            assert data["stock_quantity"] == update_data["stock_quantity"]
            mock_catalog_service.update_product.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_product_success(self, test_client, mock_catalog_service):
        """Test deleting a product."""
        with patch("app.api.routes.catalog.get_service", return_value=mock_catalog_service):
            response = await test_client.delete(f"/api/v1/catalog/products/{TEST_PRODUCT_ID}")

            assert response.status_code == status.HTTP_204_NO_CONTENT
            mock_catalog_service.delete_product.assert_called_once_with(TEST_PRODUCT_ID)


class TestBrandRoutes:
    """Test cases for brand-related routes."""

    @pytest.mark.asyncio
    async def test_list_brands_success(self, test_client, mock_catalog_service):
        """Test listing brands."""
        with patch("app.api.routes.catalog.get_service", return_value=mock_catalog_service):
            response = await test_client.get("/api/v1/catalog/brands")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["data"]) == 1
            assert data["data"][0]["id"] == TEST_BRAND_ID
            mock_catalog_service.list_brands.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_brand_success(self, test_client, mock_catalog_service):
        """Test getting a brand by ID."""
        with patch("app.api.routes.catalog.get_service", return_value=mock_catalog_service):
            response = await test_client.get(f"/api/v1/catalog/brands/{TEST_BRAND_ID}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == TEST_BRAND_ID
            assert data["name"] == "Test Brand"
            mock_catalog_service.get_brand_by_id.assert_called_once_with(TEST_BRAND_ID)


class TestCharacteristicRoutes:
    """Test cases for characteristic-related routes."""

    @pytest.mark.asyncio
    async def test_list_characteristics_success(self, test_client, mock_catalog_service):
        """Test listing characteristics for a category."""
        with patch("app.api.routes.catalog.get_service", return_value=mock_catalog_service):
            response = await test_client.get(
                "/api/v1/catalog/characteristics",
                params={"category_id": TEST_CATEGORY_ID},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["data"]) == 1
            assert data["data"][0]["id"] == TEST_CHARACTERISTIC_ID
            mock_catalog_service.list_characteristics.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_characteristic_values_success(self, test_client, mock_catalog_service):
        """Test getting values for a characteristic."""
        with patch("app.api.routes.catalog.get_service", return_value=mock_catalog_service):
            response = await test_client.get(
                f"/api/v1/catalog/characteristics/{TEST_CHARACTERISTIC_ID}/values",
                params={"category_id": TEST_CATEGORY_ID},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 2
            assert data[0]["value"] == "Red"
            assert data[1]["value"] == "Blue"
            mock_catalog_service.get_characteristic_values.assert_called_once_with(
                category_id=TEST_CATEGORY_ID,
                characteristic_id=TEST_CHARACTERISTIC_ID,
            )


class TestErrorHandling:
    """Test error handling in the API routes."""

    @pytest.mark.asyncio
    async def test_http_exception_handling(self, test_client, mock_catalog_service):
        """Test handling of HTTP exceptions."""
        mock_catalog_service.get_product_by_id.side_effect = Problem(
            status=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail="Product not found",
        )
        with patch("app.api.routes.catalog.get_service", return_value=mock_catalog_service):
            response = await test_client.get(f"/api/v1/catalog/products/{TEST_PRODUCT_ID}")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert data["title"] == "Not Found"
            assert data["detail"] == "Product not found"

    @pytest.mark.asyncio
    async def test_validation_error_handling(self, test_client):
        """Test handling of validation errors."""
        response = await test_client.post(
            "/api/v1/catalog/products",
            json={
                "name": "",  # Empty name
                "price": -10,  # Negative price
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        data = response.json()
        assert "detail" in data
        assert any("name" in error["loc"] for error in data["detail"])
        assert any("price" in error["loc"] for error in data["detail"])
