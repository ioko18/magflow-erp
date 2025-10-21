"""
Unit Tests for eMAG Product Publishing Services

Tests for:
- Product Publishing Service
- Category Service
- Reference Data Service
- EAN Matching Service
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

from app.services.emag.emag_product_publishing_service import EmagProductPublishingService
from app.services.emag.emag_category_service import EmagCategoryService
from app.services.emag.emag_reference_data_service import EmagReferenceDataService
from app.core.exceptions import ServiceError


class TestProductPublishingService:
    """Tests for Product Publishing Service"""
    
    @pytest.fixture
    def mock_client(self):
        """Create mock eMAG API client"""
        client = AsyncMock()
        client.start = AsyncMock()
        client.close = AsyncMock()
        client._request = AsyncMock()
        return client
    
    @pytest.fixture
    async def service(self, mock_client):
        """Create service instance with mocked client"""
        with patch(
            'app.services.emag.emag_product_publishing_service.EmagApiClient',
            return_value=mock_client,
        ):
            service = EmagProductPublishingService("main")
            service.client = mock_client
            yield service
    
    @pytest.mark.asyncio
    async def test_create_draft_product_success(self, service, mock_client):
        """Test successful draft product creation"""
        # Arrange
        mock_client._request.return_value = {
            "isError": False,
            "results": [{"id": 12345, "status": "draft"}]
        }
        
        # Act
        result = await service.create_draft_product(
            product_id=12345,
            name="Test Product",
            brand="Test Brand",
            part_number="TEST123"
        )
        
        # Assert
        assert result["isError"] is False
        assert result["results"][0]["id"] == 12345
        mock_client._request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_draft_product_with_optional_fields(self, service, mock_client):
        """Test draft product creation with optional fields"""
        # Arrange
        mock_client._request.return_value = {
            "isError": False,
            "results": [{"id": 12345}]
        }
        
        # Act
        result = await service.create_draft_product(
            product_id=12345,
            name="Test Product",
            brand="Test Brand",
            part_number="TEST123",
            category_id=506,
            ean=["5941234567890"],
            source_language="en"
        )
        
        # Assert
        assert result["isError"] is False
        call_args = mock_client._request.call_args
        payload = call_args[1]["json"]
        assert payload["category_id"] == 506
        assert payload["ean"] == ["5941234567890"]
        assert payload["source_language"] == "en"
    
    @pytest.mark.asyncio
    async def test_create_complete_product_success(self, service, mock_client):
        """Test successful complete product creation"""
        # Arrange
        mock_client._request.return_value = {
            "isError": False,
            "results": [{"id": 12345, "status": "active"}]
        }
        
        # Act
        result = await service.create_complete_product(
            product_id=12345,
            category_id=506,
            name="Test Product",
            part_number="TEST123",
            brand="Test Brand",
            description="<p>Test description</p>",
            images=[{"display_type": 1, "url": "https://example.com/image.jpg"}],
            characteristics=[{"id": 100, "value": "Black"}],
            sale_price=199.99,
            vat_id=1,
            stock=[{"warehouse_id": 1, "value": 50}],
            handling_time=[{"warehouse_id": 1, "value": 1}]
        )
        
        # Assert
        assert result["isError"] is False
        assert result["results"][0]["id"] == 12345
        mock_client._request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_attach_offer_by_part_number_key(self, service, mock_client):
        """Test attaching offer to existing product by part_number_key"""
        # Arrange
        mock_client._request.return_value = {
            "isError": False,
            "results": [{"id": 12345, "attached": True}]
        }
        
        # Act
        result = await service.attach_offer_to_existing_product(
            product_id=12345,
            part_number_key="D5DD9BBBM",
            sale_price=199.99,
            vat_id=1,
            stock=[{"warehouse_id": 1, "value": 50}],
            handling_time=[{"warehouse_id": 1, "value": 1}]
        )
        
        # Assert
        assert result["isError"] is False
        call_args = mock_client._request.call_args
        payload = call_args[1]["json"]
        assert payload["part_number_key"] == "D5DD9BBBM"
    
    @pytest.mark.asyncio
    async def test_attach_offer_by_ean(self, service, mock_client):
        """Test attaching offer by EAN"""
        # Arrange
        mock_client._request.return_value = {
            "isError": False,
            "results": [{"id": 12345, "attached": True}]
        }
        
        # Act
        result = await service.attach_offer_by_ean(
            product_id=12345,
            ean=["5941234567890"],
            sale_price=199.99,
            vat_id=1,
            stock=[{"warehouse_id": 1, "value": 50}],
            handling_time=[{"warehouse_id": 1, "value": 1}]
        )
        
        # Assert
        assert result["isError"] is False
        call_args = mock_client._request.call_args
        payload = call_args[1]["json"]
        assert payload["ean"] == ["5941234567890"]
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, service, mock_client):
        """Test API error handling"""
        # Arrange
        from app.services.emag.emag_api_client import EmagApiError
        mock_client._request.side_effect = EmagApiError("API Error")
        
        # Act & Assert
        with pytest.raises(ServiceError, match="Draft product creation failed"):
            await service.create_draft_product(
                product_id=12345,
                name="Test",
                brand="Test",
                part_number="TEST"
            )


class TestCategoryService:
    """Tests for Category Service"""
    
    @pytest.fixture
    def mock_client(self):
        """Create mock eMAG API client"""
        client = AsyncMock()
        client.start = AsyncMock()
        client.close = AsyncMock()
        client._request = AsyncMock()
        return client
    
    @pytest.fixture
    async def service(self, mock_client):
        """Create service instance with mocked client"""
        with patch(
            'app.services.emag.emag_category_service.EmagApiClient',
            return_value=mock_client,
        ):
            service = EmagCategoryService("main")
            service.client = mock_client
            yield service
    
    @pytest.mark.asyncio
    async def test_get_categories_success(self, service, mock_client):
        """Test successful category retrieval"""
        # Arrange
        mock_client._request.return_value = {
            "isError": False,
            "results": [
                {"id": 506, "name": "Electronics", "is_allowed": 1},
                {"id": 507, "name": "Books", "is_allowed": 1}
            ]
        }
        
        # Act
        result = await service.get_categories(current_page=1, items_per_page=10)
        
        # Assert
        assert result["isError"] is False
        assert len(result["results"]) == 2
        assert result["results"][0]["id"] == 506
    
    @pytest.mark.asyncio
    async def test_get_category_by_id(self, service, mock_client):
        """Test getting specific category details"""
        # Arrange
        mock_client._request.return_value = {
            "isError": False,
            "results": [{
                "id": 506,
                "name": "Electronics",
                "is_allowed": 1,
                "characteristics": [
                    {"id": 100, "name": "Color", "is_mandatory": 1}
                ]
            }]
        }
        
        # Act
        result = await service.get_category_by_id(506)
        
        # Assert
        assert result["isError"] is False
        assert result["results"][0]["id"] == 506
        assert len(result["results"][0]["characteristics"]) == 1
    
    @pytest.mark.asyncio
    async def test_category_caching(self, service, mock_client):
        """Test category caching mechanism"""
        # Arrange
        mock_client._request.return_value = {
            "isError": False,
            "results": [{"id": 506, "name": "Electronics"}]
        }
        
        # Act - First call
        result1 = await service.get_categories(current_page=1)
        # Second call should use cache
        result2 = await service.get_categories(current_page=1, use_cache=True)
        
        # Assert - API should be called only once
        assert mock_client._request.call_count == 1
        assert result1 == result2
    
    @pytest.mark.asyncio
    async def test_count_categories(self, service, mock_client):
        """Test category counting"""
        # Arrange
        mock_client._request.return_value = {
            "isError": False,
            "results": {"count": 150}
        }
        
        # Act
        count = await service.count_categories()
        
        # Assert
        assert count == 150
    
    @pytest.mark.asyncio
    async def test_get_allowed_categories(self, service, mock_client):
        """Test filtering allowed categories"""
        # Arrange
        mock_client._request.return_value = {
            "isError": False,
            "results": [
                {"id": 506, "name": "Electronics", "is_allowed": 1},
                {"id": 507, "name": "Books", "is_allowed": 0},
                {"id": 508, "name": "Toys", "is_allowed": 1}
            ]
        }
        
        # Act
        allowed = await service.get_allowed_categories()
        
        # Assert
        assert len(allowed) == 2
        assert all(cat["is_allowed"] == 1 for cat in allowed)


class TestReferenceDataService:
    """Tests for Reference Data Service"""
    
    @pytest.fixture
    def mock_client(self):
        """Create mock eMAG API client"""
        client = AsyncMock()
        client.start = AsyncMock()
        client.close = AsyncMock()
        client.get_vat_rates = AsyncMock()
        client.get_handling_times = AsyncMock()
        return client
    
    @pytest.fixture
    async def service(self, mock_client):
        """Create service instance with mocked client"""
        with patch(
            'app.services.emag.emag_reference_data_service.EmagApiClient',
            return_value=mock_client,
        ):
            service = EmagReferenceDataService("main")
            service.client = mock_client
            yield service
    
    @pytest.mark.asyncio
    async def test_get_vat_rates_success(self, service, mock_client):
        """Test successful VAT rates retrieval"""
        # Arrange
        mock_client.get_vat_rates.return_value = {
            "isError": False,
            "results": [
                {"id": 1, "name": "Standard 19%", "rate": 0.19},
                {"id": 2, "name": "Reduced 9%", "rate": 0.09}
            ]
        }
        
        # Act
        result = await service.get_vat_rates()
        
        # Assert
        assert len(result) == 2
        assert result[0]["rate"] == 0.19
    
    @pytest.mark.asyncio
    async def test_get_handling_times_success(self, service, mock_client):
        """Test successful handling times retrieval"""
        # Arrange
        mock_client.get_handling_times.return_value = {
            "isError": False,
            "results": [
                {"id": 1, "value": 0, "name": "Same day"},
                {"id": 2, "value": 1, "name": "Next day"}
            ]
        }
        
        # Act
        result = await service.get_handling_times()
        
        # Assert
        assert len(result) == 2
        assert result[0]["value"] == 0
    
    @pytest.mark.asyncio
    async def test_vat_rates_caching(self, service, mock_client):
        """Test VAT rates caching"""
        # Arrange
        mock_client.get_vat_rates.return_value = {
            "isError": False,
            "results": [{"id": 1, "name": "Standard", "rate": 0.19}]
        }
        
        # Act
        result1 = await service.get_vat_rates()
        result2 = await service.get_vat_rates(use_cache=True)
        
        # Assert - API should be called only once
        assert mock_client.get_vat_rates.call_count == 1
        assert result1 == result2
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self, service, mock_client):
        """Test cache expiration after TTL"""
        # Arrange
        mock_client.get_vat_rates.return_value = {
            "isError": False,
            "results": [{"id": 1}]
        }
        
        # Act
        await service.get_vat_rates()
        # Simulate cache expiration
        service._cache_timestamp = datetime.now() - timedelta(days=8)
        await service.get_vat_rates()
        
        # Assert - API should be called twice
        assert mock_client.get_vat_rates.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_vat_rate_by_id(self, service, mock_client):
        """Test getting specific VAT rate by ID"""
        # Arrange
        mock_client.get_vat_rates.return_value = {
            "isError": False,
            "results": [
                {"id": 1, "name": "Standard", "rate": 0.19},
                {"id": 2, "name": "Reduced", "rate": 0.09}
            ]
        }
        
        # Act
        result = await service.get_vat_rate_by_id(2)
        
        # Assert
        assert result is not None
        assert result["id"] == 2
        assert result["rate"] == 0.09
    
    @pytest.mark.asyncio
    async def test_get_handling_time_by_value(self, service, mock_client):
        """Test getting specific handling time by value"""
        # Arrange
        mock_client.get_handling_times.return_value = {
            "isError": False,
            "results": [
                {"id": 1, "value": 0, "name": "Same day"},
                {"id": 2, "value": 1, "name": "Next day"}
            ]
        }
        
        # Act
        result = await service.get_handling_time_by_value(1)
        
        # Assert
        assert result is not None
        assert result["value"] == 1
        assert result["name"] == "Next day"
    
    @pytest.mark.asyncio
    async def test_refresh_all_cache(self, service, mock_client):
        """Test refreshing all cached data"""
        # Arrange
        mock_client.get_vat_rates.return_value = {
            "isError": False,
            "results": [{"id": 1}]
        }
        mock_client.get_handling_times.return_value = {
            "isError": False,
            "results": [{"id": 1}]
        }
        
        # Act
        result = await service.refresh_all_cache()
        
        # Assert
        assert result["success"] is True
        assert "vat_rates_count" in result
        assert "handling_times_count" in result
        mock_client.get_vat_rates.assert_called_once()
        mock_client.get_handling_times.assert_called_once()
    
    def test_clear_cache(self, service):
        """Test clearing cache"""
        # Arrange
        service._vat_cache = [{"id": 1}]
        service._handling_time_cache = [{"id": 1}]
        service._cache_timestamp = datetime.now()
        
        # Act
        service.clear_cache()
        
        # Assert
        assert len(service._vat_cache) == 0
        assert len(service._handling_time_cache) == 0
        assert service._cache_timestamp is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
