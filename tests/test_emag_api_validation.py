"""Tests for eMAG API response validation.

This module tests the API response validation functionality,
ensuring compliance with eMAG API v4.4.8 requirements.
"""

import json
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from app.services.emag_integration_service import (
    EmagApiClient,
    EmagApiConfig,
    EmagApiError,
)


class TestEmagApiResponseValidation:
    """Test cases for eMAG API response validation."""

    @pytest.fixture
    def api_config(self):
        """Create test API configuration."""
        return EmagApiConfig(
            environment="sandbox",
            api_username="test_user",
            api_password="test_pass",
        )

    @pytest.fixture
    def api_client(self, api_config):
        """Create test API client."""
        client = EmagApiClient(api_config)
        # Mock the session to avoid actual HTTP calls
        client.session = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_valid_response_no_error(self, api_client):
        """Test handling of valid response with isError: false."""
        mock_response_data = {
            "isError": False,
            "messages": [],
            "data": {"products": []},
        }

        with patch.object(api_client.session, "request") as mock_request:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_response_data
            mock_response.status = 200
            mock_request.return_value.__aenter__.return_value = mock_response

            result = await api_client._make_request("GET", "/test")

            assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_response_with_error(self, api_client):
        """Test handling of response with isError: true."""
        error_messages = ["Invalid product ID", "Product not found"]
        mock_response_data = {
            "isError": True,
            "messages": error_messages,
            "data": None,
        }

        with patch.object(api_client.session, "request") as mock_request:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_response_data
            mock_response.status = 200
            mock_request.return_value.__aenter__.return_value = mock_response

            with pytest.raises(EmagApiError) as exc_info:
                await api_client._make_request("GET", "/test")

            assert "Invalid product ID" in str(exc_info.value)
            assert exc_info.value.status_code == 200
            assert exc_info.value.details == mock_response_data

    @pytest.mark.asyncio
    async def test_response_missing_iserror_field(self, api_client):
        """Test handling of response missing required isError field."""
        mock_response_data = {
            "data": {"products": []},
            "status": "success",
            # Missing isError field
        }

        with patch.object(api_client.session, "request") as mock_request:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_response_data
            mock_response.status = 200
            mock_request.return_value.__aenter__.return_value = mock_response

            with pytest.raises(EmagApiError) as exc_info:
                await api_client._make_request("GET", "/test")

            assert "missing 'isError' field" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_http_error_handling(self, api_client):
        """Test handling of HTTP errors."""
        mock_response_data = {
            "isError": True,
            "messages": ["Internal server error"],
            "data": None,
        }

        with patch.object(api_client.session, "request") as mock_request:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_response_data
            mock_response.status = 500
            mock_request.return_value.__aenter__.return_value = mock_response

            with pytest.raises(EmagApiError) as exc_info:
                await api_client._make_request("GET", "/test")

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_rate_limit_retry(self, api_client):
        """Test rate limit handling with retry."""
        # First call returns 429 (rate limit)
        rate_limit_response = {
            "isError": True,
            "messages": ["Rate limit exceeded"],
            "data": None,
        }

        # Second call succeeds
        success_response = {
            "isError": False,
            "messages": [],
            "data": {"products": []},
        }

        call_count = 0

        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = AsyncMock()
            if call_count == 1:
                mock_response.status = 429
                mock_response.json.return_value = rate_limit_response
            else:
                mock_response.status = 200
                mock_response.json.return_value = success_response
            return mock_response

        with patch.object(api_client.session, "request", side_effect=mock_request):
            with patch("asyncio.sleep") as mock_sleep:
                result = await api_client._make_request("GET", "/test")

                assert result == success_response
                assert call_count == 2  # One retry
                mock_sleep.assert_called_once()

    @pytest.mark.asyncio
    async def test_auth_retry(self, api_client):
        """Test authentication retry on 401."""
        # First call returns 401
        auth_error_response = {
            "isError": True,
            "messages": ["Authentication failed"],
            "data": None,
        }

        # Second call succeeds
        success_response = {
            "isError": False,
            "messages": [],
            "data": {"products": []},
        }

        call_count = 0

        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = AsyncMock()
            if call_count == 1:
                mock_response.status = 401
                mock_response.json.return_value = auth_error_response
            else:
                mock_response.status = 200
                mock_response.json.return_value = success_response
            return mock_response

        with patch.object(api_client.session, "request", side_effect=mock_request):
            with patch.object(api_client, "authenticate") as mock_auth:
                result = await api_client._make_request("GET", "/test")

                assert result == success_response
                assert call_count == 2
                mock_auth.assert_called_once()

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, api_client):
        """Test behavior when max retries are exceeded."""
        error_response = {
            "isError": True,
            "messages": ["Rate limit exceeded"],
            "data": None,
        }

        with patch.object(api_client.session, "request") as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 429
            mock_response.json.return_value = error_response
            mock_request.return_value.__aenter__.return_value = mock_response

            with patch("asyncio.sleep"):  # Prevent actual sleeping
                with pytest.raises(EmagApiError) as exc_info:
                    await api_client._make_request("GET", "/test")

                assert "Rate limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_client_error_retry(self, api_client):
        """Test retry on aiohttp.ClientError."""
        success_response = {
            "isError": False,
            "messages": [],
            "data": {"products": []},
        }

        call_count = 0

        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise aiohttp.ClientError("Network error")
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = success_response
            return mock_response

        with patch.object(api_client.session, "request", side_effect=mock_request):
            with patch("asyncio.sleep") as mock_sleep:
                result = await api_client._make_request("GET", "/test")

                assert result == success_response
                assert call_count == 2
                assert mock_sleep.call_count == 1

    @pytest.mark.asyncio
    async def test_json_decode_error(self, api_client):
        """Test handling of invalid JSON responses."""
        with patch.object(api_client.session, "request") as mock_request:
            mock_response = AsyncMock()
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_response.status = 200
            mock_request.return_value.__aenter__.return_value = mock_response

            with pytest.raises(EmagApiError):
                await api_client._make_request("GET", "/test")

    @pytest.mark.asyncio
    async def test_empty_messages_array(self, api_client):
        """Test handling when messages array is empty."""
        mock_response_data = {
            "isError": True,
            "messages": [],  # Empty messages
            "data": None,
        }

        with patch.object(api_client.session, "request") as mock_request:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_response_data
            mock_response.status = 200
            mock_request.return_value.__aenter__.return_value = mock_response

            with pytest.raises(EmagApiError) as exc_info:
                await api_client._make_request("GET", "/test")

            assert "Unknown error" in str(exc_info.value)


class TestEmagApiErrorHandling:
    """Test cases for EmagApiError class."""

    def test_error_initialization(self):
        """Test EmagApiError initialization."""
        error = EmagApiError("Test error", 400, {"details": "test"})

        assert str(error) == "Test error"
        assert error.status_code == 400
        assert error.details == {"details": "test"}

    def test_error_without_details(self):
        """Test EmagApiError without details."""
        error = EmagApiError("Test error", 500)

        assert str(error) == "Test error"
        assert error.status_code == 500
        assert error.details == {}

    def test_error_inheritance(self):
        """Test that EmagApiError inherits from Exception."""
        error = EmagApiError("Test error")

        assert isinstance(error, Exception)


class TestEmagApiIntegrationValidation:
    """Integration tests for API validation."""

    @pytest.mark.asyncio
    async def test_end_to_end_validation(self):
        """Test end-to-end API validation flow."""
        config = EmagApiConfig(
            environment="sandbox",
            api_username="test",
            api_password="test",
        )

        client = EmagApiClient(config)
        client.session = AsyncMock()  # Mock the session to prevent real HTTP calls

        # Mock the entire flow
        with patch.object(client.session, "request") as mock_request:
            # Successful response
            success_data = {
                "isError": False,
                "messages": [],
                "data": {"products": [{"id": "1", "name": "Test Product"}]},
            }

            mock_response = AsyncMock()
            mock_response.json.return_value = success_data
            mock_response.status = 200
            mock_request.return_value.__aenter__.return_value = mock_response

            result = await client._make_request("GET", "/products")

            assert result == success_data
            # Verify rate limiter was called for "other" resource type
            # This would be tested in integration with rate limiter
