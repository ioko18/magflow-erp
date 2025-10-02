"""
Integration Tests for eMAG Product Publishing API Endpoints

Tests for:
- Draft product creation endpoint
- Complete product creation endpoint
- Offer attachment endpoints
- EAN matching endpoint
- Category endpoints
- Reference data endpoints
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from app.main import app


@pytest.fixture
async def async_client():
    """Create async test client"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def auth_headers():
    """Create authentication headers with mock JWT token"""
    # In real tests, you would get a real token from login endpoint
    return {"Authorization": "Bearer mock_token"}


@pytest.fixture
def mock_emag_service():
    """Mock eMAG services"""
    with patch('app.api.v1.endpoints.emag_product_publishing.EmagProductPublishingService') as mock_pub, \
         patch('app.api.v1.endpoints.emag_product_publishing.EmagCategoryService') as mock_cat, \
         patch('app.api.v1.endpoints.emag_product_publishing.EmagReferenceDataService') as mock_ref, \
         patch('app.api.v1.endpoints.emag_product_publishing.EmagEANMatchingService') as mock_ean:
        
        # Setup mock returns
        mock_pub_instance = AsyncMock()
        mock_pub.return_value.__aenter__.return_value = mock_pub_instance
        
        mock_cat_instance = AsyncMock()
        mock_cat.return_value.__aenter__.return_value = mock_cat_instance
        
        mock_ref_instance = AsyncMock()
        mock_ref.return_value.__aenter__.return_value = mock_ref_instance
        
        mock_ean_instance = AsyncMock()
        mock_ean.return_value.__aenter__.return_value = mock_ean_instance
        
        yield {
            'publishing': mock_pub_instance,
            'category': mock_cat_instance,
            'reference': mock_ref_instance,
            'ean': mock_ean_instance
        }


class TestDraftProductEndpoint:
    """Tests for draft product creation endpoint"""
    
    @pytest.mark.asyncio
    async def test_create_draft_product_success(self, async_client, auth_headers, mock_emag_service):
        """Test successful draft product creation"""
        # Arrange
        mock_emag_service['publishing'].create_draft_product.return_value = {
            "isError": False,
            "results": [{"id": 12345, "status": "draft"}]
        }
        
        payload = {
            "product_id": 12345,
            "name": "Test Product",
            "brand": "Test Brand",
            "part_number": "TEST123"
        }
        
        # Act
        response = await async_client.post(
            "/api/v1/emag/publishing/draft?account_type=main",
            json=payload,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
    
    @pytest.mark.asyncio
    async def test_create_draft_product_validation_error(self, async_client, auth_headers):
        """Test validation error for invalid payload"""
        # Arrange
        payload = {
            "product_id": 12345,
            # Missing required fields
        }
        
        # Act
        response = await async_client.post(
            "/api/v1/emag/publishing/draft?account_type=main",
            json=payload,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_create_draft_product_unauthorized(self, async_client):
        """Test unauthorized access without token"""
        # Arrange
        payload = {
            "product_id": 12345,
            "name": "Test",
            "brand": "Test",
            "part_number": "TEST"
        }
        
        # Act
        response = await async_client.post(
            "/api/v1/emag/publishing/draft?account_type=main",
            json=payload
        )
        
        # Assert
        assert response.status_code == 401


class TestCompleteProductEndpoint:
    """Tests for complete product creation endpoint"""
    
    @pytest.mark.asyncio
    async def test_create_complete_product_success(self, async_client, auth_headers, mock_emag_service):
        """Test successful complete product creation"""
        # Arrange
        mock_emag_service['publishing'].create_complete_product.return_value = {
            "isError": False,
            "results": [{"id": 12345, "status": "active"}]
        }
        
        payload = {
            "product_id": 12345,
            "category_id": 506,
            "name": "Test Product",
            "part_number": "TEST123",
            "brand": "Test Brand",
            "description": "<p>Test description</p>",
            "images": [{"display_type": 1, "url": "https://example.com/image.jpg"}],
            "characteristics": [{"id": 100, "value": "Black"}],
            "sale_price": 199.99,
            "vat_id": 1,
            "stock": [{"warehouse_id": 1, "value": 50}],
            "handling_time": [{"warehouse_id": 1, "value": 1}]
        }
        
        # Act
        response = await async_client.post(
            "/api/v1/emag/publishing/complete?account_type=main",
            json=payload,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestAttachOfferEndpoint:
    """Tests for offer attachment endpoint"""
    
    @pytest.mark.asyncio
    async def test_attach_offer_by_part_number_key(self, async_client, auth_headers, mock_emag_service):
        """Test attaching offer by part_number_key"""
        # Arrange
        mock_emag_service['publishing'].attach_offer_to_existing_product.return_value = {
            "isError": False,
            "results": [{"id": 12345, "attached": True}]
        }
        
        payload = {
            "product_id": 12345,
            "part_number_key": "D5DD9BBBM",
            "sale_price": 199.99,
            "vat_id": 1,
            "stock": [{"warehouse_id": 1, "value": 50}],
            "handling_time": [{"warehouse_id": 1, "value": 1}]
        }
        
        # Act
        response = await async_client.post(
            "/api/v1/emag/publishing/attach-offer?account_type=main",
            json=payload,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_attach_offer_missing_identifier(self, async_client, auth_headers):
        """Test error when both part_number_key and ean are missing"""
        # Arrange
        payload = {
            "product_id": 12345,
            # Missing both part_number_key and ean
            "sale_price": 199.99,
            "vat_id": 1,
            "stock": [{"warehouse_id": 1, "value": 50}],
            "handling_time": [{"warehouse_id": 1, "value": 1}]
        }
        
        # Act
        response = await async_client.post(
            "/api/v1/emag/publishing/attach-offer?account_type=main",
            json=payload,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 400


class TestEANMatchingEndpoint:
    """Tests for EAN matching endpoint"""
    
    @pytest.mark.asyncio
    async def test_match_ean_success(self, async_client, auth_headers, mock_emag_service):
        """Test successful EAN matching"""
        # Arrange
        mock_emag_service['ean'].bulk_find_products_by_eans.return_value = {
            "success": True,
            "eans_searched": 2,
            "products_found": 2,
            "products": [
                {"eans": "5941234567890", "part_number_key": "ABC123"},
                {"eans": "5941234567891", "part_number_key": "DEF456"}
            ]
        }
        
        payload = {
            "eans": ["5941234567890", "5941234567891"]
        }
        
        # Act
        response = await async_client.post(
            "/api/v1/emag/publishing/match-ean?account_type=main",
            json=payload,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["products_found"] == 2
    
    @pytest.mark.asyncio
    async def test_match_ean_too_many(self, async_client, auth_headers):
        """Test error when too many EANs provided"""
        # Arrange
        payload = {
            "eans": ["123456789012" + str(i) for i in range(101)]  # 101 EANs
        }
        
        # Act
        response = await async_client.post(
            "/api/v1/emag/publishing/match-ean?account_type=main",
            json=payload,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 422  # Validation error


class TestCategoryEndpoints:
    """Tests for category endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_categories_success(self, async_client, auth_headers, mock_emag_service):
        """Test successful category listing"""
        # Arrange
        mock_emag_service['category'].get_categories.return_value = {
            "isError": False,
            "results": [
                {"id": 506, "name": "Electronics"},
                {"id": 507, "name": "Books"}
            ]
        }
        
        # Act
        response = await async_client.get(
            "/api/v1/emag/publishing/categories?current_page=1&items_per_page=10&account_type=main",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]["results"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_category_by_id_success(self, async_client, auth_headers, mock_emag_service):
        """Test getting specific category"""
        # Arrange
        mock_emag_service['category'].get_category_by_id.return_value = {
            "isError": False,
            "results": [{
                "id": 506,
                "name": "Electronics",
                "characteristics": []
            }]
        }
        
        # Act
        response = await async_client.get(
            "/api/v1/emag/publishing/categories/506?account_type=main",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["results"][0]["id"] == 506
    
    @pytest.mark.asyncio
    async def test_get_allowed_categories(self, async_client, auth_headers, mock_emag_service):
        """Test getting allowed categories only"""
        # Arrange
        mock_emag_service['category'].get_allowed_categories.return_value = [
            {"id": 506, "name": "Electronics", "is_allowed": 1}
        ]
        
        # Act
        response = await async_client.get(
            "/api/v1/emag/publishing/categories/allowed?account_type=main",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]["categories"]) == 1


class TestReferenceDataEndpoints:
    """Tests for reference data endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_vat_rates_success(self, async_client, auth_headers, mock_emag_service):
        """Test getting VAT rates"""
        # Arrange
        mock_emag_service['reference'].get_vat_rates.return_value = [
            {"id": 1, "name": "Standard 19%", "rate": 0.19}
        ]
        
        # Act
        response = await async_client.get(
            "/api/v1/emag/publishing/vat-rates?account_type=main",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]["vat_rates"]) == 1
    
    @pytest.mark.asyncio
    async def test_get_handling_times_success(self, async_client, auth_headers, mock_emag_service):
        """Test getting handling times"""
        # Arrange
        mock_emag_service['reference'].get_handling_times.return_value = [
            {"id": 1, "value": 0, "name": "Same day"},
            {"id": 2, "value": 1, "name": "Next day"}
        ]
        
        # Act
        response = await async_client.get(
            "/api/v1/emag/publishing/handling-times?account_type=main",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]["handling_times"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
