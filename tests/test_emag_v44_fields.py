"""Tests for eMAG API v4.4.8 new fields and features.

This module tests the new API fields introduced in eMAG API v4.4.8:
- images_overwrite
- green_tax (RO only)
- supply_lead_time
- GPSR fields (safety_information, manufacturer, eu_representative)
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.emag.emag_integration_service import (
    EmagApiConfig,
    EmagApiEnvironment,
    EmagProduct,
)


class TestEmagV44Fields:
    """Test cases for eMAG API v4.4.8 new fields."""

    def test_emag_product_v44_fields(self):
        """Test EmagProduct with v4.4.8 fields."""
        product = EmagProduct(
            id="test_123",
            name="Test Product v4.4.8",
            sku="TEST001",
            description="Test product with new fields",
            price=299.99,
            currency="RON",
            stock_quantity=50,
            brand="Test Brand",
            # New v4.4.8 fields
            images_overwrite=True,
            green_tax=5.99,
            supply_lead_time=14,
            safety_information="Safety instructions for product",
            manufacturer=[
                {
                    "name": "Test Manufacturer",
                    "address": "123 Test Street, Test City",
                    "email": "manufacturer@test.com",
                },
            ],
            eu_representative=[
                {
                    "name": "Test EU Rep",
                    "address": "456 EU Street, EU City",
                    "email": "eu@test.com",
                },
            ],
        )

        # Verify all fields are set correctly
        assert product.images_overwrite is True
        assert product.green_tax == 5.99
        assert product.supply_lead_time == 14
        assert product.safety_information == "Safety instructions for product"
        assert len(product.manufacturer) == 1
        assert len(product.eu_representative) == 1

        # Verify manufacturer data
        manufacturer = product.manufacturer[0]
        assert manufacturer["name"] == "Test Manufacturer"
        assert manufacturer["address"] == "123 Test Street, Test City"
        assert manufacturer["email"] == "manufacturer@test.com"

        # Verify EU representative data
        eu_rep = product.eu_representative[0]
        assert eu_rep["name"] == "Test EU Rep"
        assert eu_rep["address"] == "456 EU Street, EU City"
        assert eu_rep["email"] == "eu@test.com"

    def test_emag_product_defaults(self):
        """Test EmagProduct default values for v4.4.8 fields."""
        product = EmagProduct(
            name="Basic Product",
            sku="BASIC001",
            price=99.99,
        )

        # Verify defaults
        assert product.images_overwrite is False  # Default
        assert product.green_tax is None
        assert product.supply_lead_time is None
        assert product.safety_information is None
        assert product.manufacturer == []  # Empty list
        assert product.eu_representative == []  # Empty list

    def test_emag_product_validation(self):
        """Test EmagProduct field validation."""
        # Test valid GPSR data structure
        valid_manufacturer = {
            "name": "Valid Name",
            "address": "Valid Address",
            "email": "valid@email.com",
        }

        product = EmagProduct(
            name="Test Product",
            sku="TEST001",
            price=100.0,
            manufacturer=[valid_manufacturer],
        )

        assert product.manufacturer[0] == valid_manufacturer

        # Note: In a real implementation, you might want to add Pydantic validation
        # for GPSR fields, but for now we rely on API-level validation


@pytest.mark.skip(reason="Tests need to be updated for new EmagIntegrationService architecture")
class TestEmagApiClientV44Fields:
    """Test cases for eMAG API client with v4.4.8 fields."""

    @pytest.fixture
    def api_config(self):
        """Create test API configuration."""
        return EmagApiConfig(
            environment=EmagApiEnvironment.SANDBOX,
            api_username="test_user",
            api_password="test_pass",
        )

    @pytest.fixture
    def api_client(self, api_config):
        """Create test API client - DEPRECATED, needs refactoring."""
        # This fixture is deprecated and needs to be updated
        # to use EmagIntegrationService instead
        pytest.skip("API client fixture needs refactoring")

    @pytest.mark.asyncio
    async def test_create_product_with_v44_fields(self, api_client):
        """Test creating product with v4.4.8 fields."""
        product = EmagProduct(
            id="test_123",
            name="Test Product v4.4.8",
            sku="TEST001",
            description="Test product with new fields",
            price=299.99,
            currency="RON",
            stock_quantity=50,
            brand="Test Brand",
            emag_category_id="123",
            # New v4.4.8 fields
            images_overwrite=True,
            green_tax=5.99,
            supply_lead_time=14,
            safety_information="Safety instructions",
            manufacturer=[
                {
                    "name": "Test Manufacturer",
                    "address": "123 Test Street",
                    "email": "manufacturer@test.com",
                }
            ],
            eu_representative=[
                {
                    "name": "Test EU Rep",
                    "address": "456 EU Street",
                    "email": "eu@test.com",
                }
            ],
        )

        expected_payload = {
            "name": "Test Product v4.4.8",
            "sku": "TEST001",
            "description": "Test product with new fields",
            "price": 299.99,
            "currency": "RON",
            "stock": 50,
            "category_id": "123",
            "brand": "Test Brand",
            "images": [],
            "characteristics": {},
            "active": True,
            # v4.4.8 fields should be included
            "images_overwrite": True,
            "green_tax": 5.99,
            "supply_lead_time": 14,
            "safety_information": "Safety instructions",
            "manufacturer": [
                {
                    "name": "Test Manufacturer",
                    "address": "123 Test Street",
                    "email": "manufacturer@test.com",
                }
            ],
            "eu_representative": [
                {
                    "name": "Test EU Rep",
                    "address": "456 EU Street",
                    "email": "eu@test.com",
                }
            ],
        }

        with patch.object(api_client.session, "request") as mock_request:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "isError": False,
                "data": {"id": "test_123"},
            }
            mock_response.status = 200
            mock_request.return_value.__aenter__.return_value = mock_response

            await api_client.create_product(product)

            # Verify the request was made with correct payload
            call_args = mock_request.call_args
            assert call_args[1]["method"] == "POST"
            assert call_args[1]["url"].endswith("/products")

            # Check that JSON payload contains all expected fields
            json_payload = call_args[1]["json"]
            for key, expected_value in expected_payload.items():
                assert json_payload[key] == expected_value, f"Field {key} mismatch"

    @pytest.mark.asyncio
    async def test_create_product_without_v44_fields(self, api_client):
        """Test creating product without v4.4.8 fields (backward compatibility)."""
        product = EmagProduct(
            id="test_123",
            name="Basic Product",
            sku="BASIC001",
            price=99.99,
            currency="RON",
            stock_quantity=10,
            brand="Basic Brand",
            emag_category_id="456",
        )

        expected_payload = {
            "name": "Basic Product",
            "sku": "BASIC001",
            "description": "",
            "price": 99.99,
            "currency": "RON",
            "stock": 10,
            "category_id": "456",
            "brand": "Basic Brand",
            "images": [],
            "characteristics": {},
            "active": True,
            # v4.4.8 fields should NOT be included when None/empty
            # "images_overwrite": False,  # Should be omitted since False
            # "green_tax": None,  # Should be omitted since None
            # "supply_lead_time": None,  # Should be omitted since None
            # "safety_information": None,  # Should be omitted since None
            # "manufacturer": [],  # Should be omitted since empty
            # "eu_representative": [],  # Should be omitted since empty
        }

        with patch.object(api_client, "_session") as mock_session:
            mock_request = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "isError": False,
                "data": {"id": "test_123"},
            }
            mock_response.status = 200
            mock_request.return_value.__aenter__.return_value = mock_response
            mock_session.request = mock_request

            await api_client.create_product(product)

            json_payload = mock_request.call_args[1]["json"]

            # Verify expected fields are present
            for key, expected_value in expected_payload.items():
                assert json_payload[key] == expected_value, f"Field {key} mismatch"

            # Verify v4.4.8 fields are NOT present when not set
            assert "images_overwrite" not in json_payload
            assert "green_tax" not in json_payload
            assert "supply_lead_time" not in json_payload
            assert "safety_information" not in json_payload
            assert "manufacturer" not in json_payload
            assert "eu_representative" not in json_payload

    @pytest.mark.asyncio
    async def test_update_product_with_v44_fields(self, api_client):
        """Test updating product with v4.4.8 fields."""
        product = EmagProduct(
            id="existing_123",
            name="Updated Product",
            sku="UPDATE001",
            price=199.99,
            green_tax=3.99,
            supply_lead_time=7,
        )

        with patch.object(api_client, "_session") as mock_session:
            mock_request = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "isError": False,
                "data": {"updated": True},
            }
            mock_response.status = 200
            mock_request.return_value.__aenter__.return_value = mock_response
            mock_session.request = mock_request

            await api_client.update_product("existing_123", product)

            json_payload = mock_request.call_args[1]["json"]

            # Verify v4.4.8 fields are included in update
            assert json_payload["green_tax"] == 3.99
            assert json_payload["supply_lead_time"] == 7

            # Verify request went to correct endpoint
            assert mock_request.call_args[1]["method"] == "PUT"
            assert "existing_123" in mock_request.call_args[1]["url"]


@pytest.mark.skip(reason="Tests need to be updated for new EmagIntegrationService architecture")
class TestEmagSmartDealsPriceCheck:
    """Test cases for Smart Deals price check functionality."""

    @pytest.fixture
    def api_client(self):
        """Create test API client - DEPRECATED."""
        pytest.skip("API client fixture needs refactoring")

    @pytest.mark.asyncio
    async def test_smart_deals_price_check_success(self, api_client):
        """Test successful Smart Deals price check."""
        product_id = "12345"
        expected_response = {
            "isError": False,
            "data": {
                "productId": "12345",
                "targetPrice": 249.99,
                "badgeEligible": True,
                "discountPercentage": 15,
            },
        }

        with patch.object(api_client, "_session") as mock_session:
            mock_request = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json.return_value = expected_response
            mock_response.status = 200
            mock_request.return_value.__aenter__.return_value = mock_response
            mock_session.request = mock_request

            result = await api_client.smart_deals_price_check(product_id)

            assert result == expected_response

            # Verify correct endpoint and parameters
            call_args = mock_request.call_args
            assert call_args[1]["method"] == "GET"
            assert "smart-deals-price-check" in call_args[1]["url"]
            assert call_args[1]["params"]["productId"] == product_id

    @pytest.mark.asyncio
    async def test_smart_deals_price_check_error(self, api_client):
        """Test Smart Deals price check with API error."""
        product_id = "invalid_id"

        with patch.object(api_client, "_session") as mock_session:
            mock_request = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "isError": True,
                "messages": ["Product not found"],
            }
            mock_response.status = 200
            mock_request.return_value.__aenter__.return_value = mock_response
            mock_session.request = mock_request

            with pytest.raises(Exception) as exc_info:
                await api_client.smart_deals_price_check(product_id)

            assert "Product not found" in str(exc_info.value)


class TestEmagGpsrCompliance:
    """Test cases for GPSR (General Product Safety Regulation) compliance."""

    def test_manufacturer_data_structure(self):
        """Test manufacturer data structure compliance."""
        # Valid manufacturer data
        valid_manufacturer = {
            "name": "ACME Manufacturing Ltd",
            "address": "123 Industrial Street, Manufacturing City, MC 12345",
            "email": "compliance@acme-manufacturing.com",
        }

        product = EmagProduct(
            name="Test Product",
            sku="TEST001",
            price=100.0,
            manufacturer=[valid_manufacturer],
        )

        assert len(product.manufacturer) == 1
        manufacturer = product.manufacturer[0]
        assert manufacturer["name"] == "ACME Manufacturing Ltd"
        assert "Street" in manufacturer["address"]
        assert "@" in manufacturer["email"]

    def test_eu_representative_data_structure(self):
        """Test EU representative data structure compliance."""
        valid_eu_rep = {
            "name": "EU Compliance Services GmbH",
            "address": "456 Compliance Strasse, Berlin, Germany 10115",
            "email": "info@eu-compliance.de",
        }

        product = EmagProduct(
            name="Test Product",
            sku="TEST001",
            price=100.0,
            eu_representative=[valid_eu_rep],
        )

        assert len(product.eu_representative) == 1
        eu_rep = product.eu_representative[0]
        assert eu_rep["name"] == "EU Compliance Services GmbH"
        assert "Germany" in eu_rep["address"]

    def test_safety_information_field(self):
        """Test safety information field."""
        safety_text = """
        WARNING: This product contains small parts.
        Not suitable for children under 3 years.
        Choking hazard.
        """

        product = EmagProduct(
            name="Test Product",
            sku="TEST001",
            price=100.0,
            safety_information=safety_text,
        )

        assert product.safety_information == safety_text
        assert "WARNING" in product.safety_information

    def test_green_tax_ro_only(self):
        """Test green tax field (Romania only)."""
        product = EmagProduct(
            name="Test Product",
            sku="TEST001",
            price=100.0,
            green_tax=2.50,  # 2.50 RON green tax
        )

        assert product.green_tax == 2.50
        assert isinstance(product.green_tax, float)
