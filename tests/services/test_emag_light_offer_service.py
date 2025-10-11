"""
Unit tests for eMAG Light Offer Service.

Tests the Light Offer API implementation according to eMAG API v4.4.9 specifications.
"""

import pytest
from unittest.mock import patch, AsyncMock
from app.services.emag.emag_light_offer_service import EmagLightOfferService
from app.core.exceptions import ServiceError


class TestEmagLightOfferService:
    """Test suite for EmagLightOfferService."""
    
    @pytest.fixture
    def service(self):
        """Create service instance for testing."""
        with patch('app.services.emag.emag_light_offer_service.EmagApiClient'):
            return EmagLightOfferService("main")
    
    @pytest.fixture
    def mock_client(self):
        """Create mock API client."""
        client = AsyncMock()
        return client
    
    @pytest.mark.asyncio
    async def test_update_offer_price_success(self, service, mock_client):
        """Test successful price update."""
        # Mock response
        mock_response = {
            'isError': False,
            'messages': [],
            'results': []
        }
        mock_client.post = AsyncMock(return_value=mock_response)
        service.client = mock_client
        
        # Test
        result = await service.update_offer_price(
            product_id=12345,
            sale_price=99.99
        )
        
        # Assertions
        assert result['isError'] is False
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/offer/save"
        assert call_args[0][1]['id'] == 12345
        assert call_args[0][1]['sale_price'] == 99.99
    
    @pytest.mark.asyncio
    async def test_update_offer_stock_success(self, service, mock_client):
        """Test successful stock update."""
        # Mock response
        mock_response = {
            'isError': False,
            'messages': [],
            'results': []
        }
        mock_client.post = AsyncMock(return_value=mock_response)
        service.client = mock_client
        
        # Test
        result = await service.update_offer_stock(
            product_id=12345,
            stock=50
        )
        
        # Assertions
        assert result['isError'] is False
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/offer/save"
        assert call_args[0][1]['id'] == 12345
        assert call_args[0][1]['stock'][0]['value'] == 50
    
    @pytest.mark.asyncio
    async def test_update_offer_price_and_stock(self, service, mock_client):
        """Test combined price and stock update."""
        # Mock response
        mock_response = {
            'isError': False,
            'messages': [],
            'results': []
        }
        mock_client.post = AsyncMock(return_value=mock_response)
        service.client = mock_client
        
        # Test
        result = await service.update_offer_price_and_stock(
            product_id=12345,
            sale_price=99.99,
            stock=50
        )
        
        # Assertions
        assert result['isError'] is False
        call_args = mock_client.post.call_args
        payload = call_args[0][1]
        assert payload['id'] == 12345
        assert payload['sale_price'] == 99.99
        assert payload['stock'][0]['value'] == 50
    
    @pytest.mark.asyncio
    async def test_update_offer_status(self, service, mock_client):
        """Test offer status update."""
        # Mock response
        mock_response = {
            'isError': False,
            'messages': [],
            'results': []
        }
        mock_client.post = AsyncMock(return_value=mock_response)
        service.client = mock_client
        
        # Test
        result = await service.update_offer_status(
            product_id=12345,
            status=0  # inactive
        )
        
        # Assertions
        assert result['isError'] is False
        call_args = mock_client.post.call_args
        assert call_args[0][1]['status'] == 0
    
    @pytest.mark.asyncio
    async def test_documentation_error_handling(self, service, mock_client):
        """Test that documentation errors don't raise exceptions."""
        # Mock response with documentation error
        mock_response = {
            'isError': True,
            'messages': [{'text': 'Documentation error: missing field'}],
            'results': []
        }
        mock_client.post = AsyncMock(return_value=mock_response)
        service.client = mock_client
        
        # Test - should not raise exception
        result = await service.update_offer_price(
            product_id=12345,
            sale_price=99.99
        )
        
        # Assertions - offer is still saved despite error
        assert result['isError'] is True
        assert 'documentation' in str(result['messages']).lower()
    
    @pytest.mark.asyncio
    async def test_api_error_raises_exception(self, service, mock_client):
        """Test that real API errors raise exceptions."""
        # Mock response with real error
        mock_response = {
            'isError': True,
            'messages': [{'text': 'Invalid product ID'}],
            'results': []
        }
        mock_client.post = AsyncMock(return_value=mock_response)
        service.client = mock_client
        
        # Test - should raise exception
        with pytest.raises(ServiceError):
            await service.update_offer_price(
                product_id=12345,
                sale_price=99.99
            )
    
    @pytest.mark.asyncio
    async def test_missing_isError_field(self, service, mock_client):
        """Test that missing isError field raises exception."""
        # Mock response without isError
        mock_response = {
            'messages': [],
            'results': []
        }
        mock_client.post = AsyncMock(return_value=mock_response)
        service.client = mock_client
        
        # Test - should raise exception
        with pytest.raises(ValueError):
            await service.update_offer_price(
                product_id=12345,
                sale_price=99.99
            )
    
    @pytest.mark.asyncio
    async def test_bulk_update_prices(self, service, mock_client):
        """Test bulk price updates."""
        # Mock successful responses
        mock_response = {
            'isError': False,
            'messages': [],
            'results': []
        }
        mock_client.post = AsyncMock(return_value=mock_response)
        service.client = mock_client
        
        # Test data
        updates = [
            {"id": 12345, "sale_price": 99.99},
            {"id": 12346, "sale_price": 89.99},
            {"id": 12347, "sale_price": 79.99}
        ]
        
        # Test
        result = await service.bulk_update_prices(updates, batch_size=2)
        
        # Assertions
        assert result['total'] == 3
        assert result['successful'] == 3
        assert result['failed'] == 0
        assert len(result['errors']) == 0
    
    @pytest.mark.asyncio
    async def test_bulk_update_with_failures(self, service, mock_client):
        """Test bulk updates with some failures."""
        # Mock mixed responses
        responses = [
            {'isError': False, 'messages': [], 'results': []},
            {'isError': True, 'messages': [{'text': 'Error'}], 'results': []},
            {'isError': False, 'messages': [], 'results': []}
        ]
        mock_client.post = AsyncMock(side_effect=responses)
        service.client = mock_client
        
        # Test data
        updates = [
            {"id": 12345, "sale_price": 99.99},
            {"id": 12346, "sale_price": 89.99},
            {"id": 12347, "sale_price": 79.99}
        ]
        
        # Test
        result = await service.bulk_update_prices(updates, batch_size=1)
        
        # Assertions
        assert result['total'] == 3
        assert result['successful'] == 2
        assert result['failed'] == 1
        assert len(result['errors']) == 1
    
    def test_invalid_status_value(self, service):
        """Test that invalid status values raise exception."""
        with pytest.raises(ValueError):
            # Status must be 0, 1, or 2
            service.update_offer_status.__wrapped__(service, 12345, 5)
    
    def test_update_price_and_stock_requires_at_least_one(self, service):
        """Test that update_price_and_stock requires at least one parameter."""
        with pytest.raises(ValueError):
            service.update_offer_price_and_stock.__wrapped__(
                service,
                product_id=12345,
                sale_price=None,
                stock=None
            )


class TestResponseValidation:
    """Test response validation logic."""
    
    def test_validate_response_success(self):
        """Test validation of successful response."""
        from app.core.emag_validator import validate_emag_response
        
        response = {
            'isError': False,
            'messages': [],
            'results': []
        }
        
        result = validate_emag_response(response, "/offer/save", "test")
        assert result == response
    
    def test_validate_response_missing_isError(self):
        """Test validation fails for missing isError."""
        from app.core.emag_validator import validate_emag_response
        
        response = {
            'messages': [],
            'results': []
        }
        
        with pytest.raises(ValueError):
            validate_emag_response(response, "/offer/save", "test")
    
    def test_validate_response_documentation_error(self):
        """Test validation allows documentation errors."""
        from app.core.emag_validator import validate_emag_response
        
        response = {
            'isError': True,
            'messages': [{'text': 'Documentation validation error'}],
            'results': []
        }
        
        # Should not raise exception
        result = validate_emag_response(response, "/offer/save", "test")
        assert result == response
    
    def test_validate_response_real_error(self):
        """Test validation raises exception for real errors."""
        from app.core.emag_validator import validate_emag_response
        from app.core.exceptions import ServiceError
        
        response = {
            'isError': True,
            'messages': [{'text': 'Invalid product ID'}],
            'results': []
        }
        
        with pytest.raises(ServiceError):
            validate_emag_response(response, "/offer/save", "test")
