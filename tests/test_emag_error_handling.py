"""Tests for eMAG error handling and retry logic.

This module tests the comprehensive error handling, retry mechanisms,
and exponential backoff with jitter implemented for eMAG API compliance.
"""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from app.services.emag.emag_integration_service import (
    EmagApiClient,
    EmagApiConfig,
    EmagApiEnvironment,
    EmagApiError,
)


class TestEmagRetryLogic:
    """Test cases for retry logic and exponential backoff."""

    @pytest.fixture
    def api_config(self):
        """Create test API configuration."""
        return EmagApiConfig(
            environment=EmagApiEnvironment.SANDBOX,
            api_username="test_user",
            api_password="test_pass",
            max_retries=3,
            retry_delay=0.1,  # Fast for testing
        )

    @pytest.fixture
    async def api_client(self, api_config):
        """Create test API client."""
        client = EmagApiClient(
            username=api_config.api_username,
            password=api_config.api_password,
            base_url=api_config.base_url,
            timeout=api_config.api_timeout,
            max_retries=api_config.max_retries,
        )
        await client.start()
        yield client
        await client.close()

    @pytest.mark.asyncio
    async def test_successful_request_no_retry(self, api_client):
        """Test successful request doesn't trigger retries."""
        success_response = {
            "isError": False,
            "messages": [],
            "data": {"products": []},
        }

        with patch.object(api_client._session, "request") as mock_request:
            mock_response = AsyncMock()
            mock_response.json.return_value = success_response
            mock_response.status = 200
            mock_request.return_value.__aenter__.return_value = mock_response

            result = await api_client._request("GET", "/test")

            assert result == success_response
            assert mock_request.call_count == 1  # Only one attempt

    @pytest.mark.asyncio
    async def test_rate_limit_retry_with_backoff(self, api_client):
        """Test rate limit retry with exponential backoff."""
        success_response = {
            "isError": False,
            "messages": [],
            "data": {"products": []},
        }

        rate_limit_response = {
            "isError": True,
            "messages": ["Rate limit exceeded"],
            "data": None,
        }

        call_count = 0

        def mock_request_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = AsyncMock()
            if call_count <= 2:  # First two calls fail with rate limit
                mock_response.status = 429
                mock_response.json.return_value = rate_limit_response
            else:  # Third call succeeds
                mock_response.status = 200
                mock_response.json.return_value = success_response
            return mock_response

        with patch.object(
            api_client._session, "request", side_effect=mock_request_side_effect
        ):
            with patch("asyncio.sleep") as mock_sleep:
                asyncio.get_event_loop().time()
                result = await api_client._request("GET", "/test")
                asyncio.get_event_loop().time()

                assert result == success_response
                assert call_count == 3  # Initial + 2 retries

                # Verify exponential backoff delays
                sleep_calls = mock_sleep.call_args_list
                assert len(sleep_calls) == 2  # Two retry delays

                # First retry: 2^0 * retry_delay + jitter ≈ 0.1 + jitter
                first_delay = sleep_calls[0][0][0]
                assert 0.1 <= first_delay <= 0.2  # retry_delay + jitter

                # Second retry: 2^1 * retry_delay + jitter ≈ 0.2 + jitter
                second_delay = sleep_calls[1][0][0]
                assert 0.2 <= second_delay <= 0.3

    @pytest.mark.asyncio
    async def test_auth_retry_on_401(self, api_client):
        """Test authentication retry on 401 errors."""
        success_response = {
            "isError": False,
            "messages": [],
            "data": {"products": []},
        }

        auth_error_response = {
            "isError": True,
            "messages": ["Authentication failed"],
            "data": None,
        }

        call_count = 0

        def mock_request_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = AsyncMock()
            if call_count == 1:  # First call fails with auth error
                mock_response.status = 401
                mock_response.json.return_value = auth_error_response
            else:  # Second call succeeds after re-auth
                mock_response.status = 200
                mock_response.json.return_value = success_response
            return mock_response

        with patch.object(
            api_client._session, "request", side_effect=mock_request_side_effect
        ):
            with patch.object(api_client, "authenticate") as mock_auth:
                result = await api_client._request("GET", "/test")

                assert result == success_response
                assert call_count == 2  # Initial + 1 auth retry
                mock_auth.assert_called_once()

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, api_client):
        """Test behavior when max retries are exceeded."""
        error_response = {
            "isError": True,
            "messages": ["Persistent rate limit"],
            "data": None,
        }

        with patch.object(api_client._session, "request") as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 429
            mock_response.json.return_value = error_response
            mock_request.return_value.__aenter__.return_value = mock_response

            with patch("asyncio.sleep"):  # Prevent actual delays
                with pytest.raises(EmagApiError) as exc_info:
                    await api_client._request("GET", "/test")

                assert "Rate limit exceeded" in str(exc_info.value)
                assert mock_request.call_count == 4  # Initial + 3 retries

    @pytest.mark.asyncio
    async def test_client_error_retry(self, api_client):
        """Test retry on aiohttp.ClientError."""
        success_response = {
            "isError": False,
            "messages": [],
            "data": {"products": []},
        }

        call_count = 0

        def mock_request_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise aiohttp.ClientError("Network timeout")
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = success_response
            return mock_response

        with patch.object(
            api_client._session, "request", side_effect=mock_request_side_effect
        ):
            with patch("asyncio.sleep") as mock_sleep:
                result = await api_client._request("GET", "/test")

                assert result == success_response
                assert call_count == 2  # Initial + 1 retry
                mock_sleep.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_retry_on_4xx_errors(self, api_client):
        """Test that 4xx errors (except 401/429) don't trigger retries."""
        error_response = {
            "isError": True,
            "messages": ["Bad request"],
            "data": None,
        }

        with patch.object(api_client._session, "request") as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 400
            mock_response.json.return_value = error_response
            mock_request.return_value.__aenter__.return_value = mock_response

            with pytest.raises(EmagApiError) as exc_info:
                await api_client._request("GET", "/test")

            assert "Bad request" in str(exc_info.value)
            assert mock_request.call_count == 1  # No retries for 400

    @pytest.mark.asyncio
    async def test_json_decode_error_handling(self, api_client):
        """Test handling of malformed JSON responses."""
        with patch.object(api_client._session, "request") as mock_request:
            mock_response = AsyncMock()
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_response.status = 200
            mock_request.return_value.__aenter__.return_value = mock_response

            with pytest.raises(EmagApiError):
                await api_client._request("GET", "/test")


class TestEmagErrorClassification:
    """Test cases for error classification and handling."""

    @pytest.fixture
    def api_client(self):
        """Create test API client."""
        config = EmagApiConfig(
            environment=EmagApiEnvironment.SANDBOX,
            api_username="test",
            api_password="test",
        )
        return EmagApiClient(config)

    @pytest.mark.asyncio
    async def test_rate_limit_error_classification(self, api_client):
        """Test that 429 errors are properly classified as retryable."""
        error_response = {
            "isError": True,
            "messages": ["API rate limit exceeded"],
            "data": None,
        }

        with patch.object(api_client._session, "request") as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 429
            mock_response.json.return_value = error_response
            mock_request.return_value.__aenter__.return_value = mock_response

            # Should trigger retry logic
            with patch("asyncio.sleep"):
                with pytest.raises(EmagApiError) as exc_info:
                    await api_client._request("GET", "/test")

                assert "API rate limit exceeded" in str(exc_info.value)
                # Verify it went through retry attempts
                assert mock_request.call_count > 1

    @pytest.mark.asyncio
    async def test_auth_error_classification(self, api_client):
        """Test that 401 errors trigger re-authentication."""
        error_response = {
            "isError": True,
            "messages": ["Invalid credentials"],
            "data": None,
        }

        success_response = {
            "isError": False,
            "messages": [],
            "data": {"products": []},
        }

        call_count = 0

        def mock_request_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = AsyncMock()
            if call_count == 1:
                mock_response.status = 401
                mock_response.json.return_value = error_response
            else:
                mock_response.status = 200
                mock_response.json.return_value = success_response
            return mock_response

        with patch.object(
            api_client._session, "request", side_effect=mock_request_side_effect
        ):
            with patch.object(api_client, "authenticate") as mock_auth:
                result = await api_client._request("GET", "/test")

                assert result == success_response
                mock_auth.assert_called_once()

    @pytest.mark.asyncio
    async def test_business_logic_errors(self, api_client):
        """Test handling of business logic errors (non-retryable)."""
        error_cases = [
            (400, "Bad Request", "Invalid product data"),
            (403, "Forbidden", "Insufficient permissions"),
            (404, "Not Found", "Product not found"),
            (422, "Unprocessable Entity", "Validation failed"),
        ]

        for status_code, title, message in error_cases:
            error_response = {
                "isError": True,
                "messages": [message],
                "data": None,
            }

            with patch.object(api_client._session, "request") as mock_request:
                mock_response = AsyncMock()
                mock_response.status = status_code
                mock_response.json.return_value = error_response
                mock_request.return_value.__aenter__.return_value = mock_response

                with pytest.raises(EmagApiError) as exc_info:
                    await api_client._request("GET", "/test")

                assert message in str(exc_info.value)
                assert mock_request.call_count == 1  # No retries for 4xx errors


class TestEmagErrorRecoveryScenarios:
    """Test cases for error recovery scenarios."""

    @pytest.fixture
    def api_client(self):
        """Create test API client with short timeouts for testing."""
        config = EmagApiConfig(
            environment=EmagApiEnvironment.SANDBOX,
            api_username="test",
            api_password="test",
            max_retries=2,
            retry_delay=0.01,  # Very short for testing
        )
        return EmagApiClient(config)

    @pytest.mark.asyncio
    async def test_temporary_network_issues(self, api_client):
        """Test recovery from temporary network issues."""
        success_response = {
            "isError": False,
            "messages": [],
            "data": {"status": "ok"},
        }

        # Simulate: ClientError -> ClientError -> Success
        call_count = 0

        def mock_request_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise aiohttp.ClientError(f"Temporary network error {call_count}")
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = success_response
            return mock_response

        with patch.object(
            api_client._session, "request", side_effect=mock_request_side_effect
        ):
            with patch("asyncio.sleep") as mock_sleep:
                result = await api_client._request("GET", "/health")

                assert result == success_response
                assert call_count == 3  # 2 failures + 1 success
                assert mock_sleep.call_count == 2  # 2 retry delays

    @pytest.mark.asyncio
    async def test_partial_success_with_warnings(self, api_client):
        """Test handling responses with warnings but successful data."""
        response_with_warnings = {
            "isError": False,  # Not an error, but has warnings
            "messages": ["Some products had validation warnings"],
            "data": {
                "products": [
                    {"id": "1", "name": "Product 1", "warnings": []},
                    {"id": "2", "name": "Product 2", "warnings": ["Low stock"]},
                ],
                "total_count": 2,
            },
        }

        with patch.object(api_client._session, "request") as mock_request:
            mock_response = AsyncMock()
            mock_response.json.return_value = response_with_warnings
            mock_response.status = 200
            mock_request.return_value.__aenter__.return_value = mock_response

            result = await api_client._request("GET", "/products")

            assert result == response_with_warnings
            assert result["data"]["total_count"] == 2
            assert len(result["data"]["products"]) == 2

    @pytest.mark.asyncio
    async def test_corrupted_response_recovery(self, api_client):
        """Test recovery from corrupted responses."""
        success_response = {
            "isError": False,
            "messages": [],
            "data": {"recovered": True},
        }

        # Simulate: Corrupted JSON -> Success
        call_count = 0

        def mock_request_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = AsyncMock()
            if call_count == 1:
                mock_response.json.side_effect = json.JSONDecodeError(
                    "Corrupted", "", 0
                )
            else:
                mock_response.status = 200
                mock_response.json.return_value = success_response
            return mock_response

        with patch.object(
            api_client._session, "request", side_effect=mock_request_side_effect
        ):
            with patch("asyncio.sleep"):
                result = await api_client._request("GET", "/test")

                assert result == success_response
                assert call_count == 2

    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self, api_client):
        """Test circuit breaker behavior for persistent failures."""
        # This would typically be implemented at a higher level,
        # but we can test the foundation here

        error_response = {
            "isError": True,
            "messages": ["Service temporarily unavailable"],
            "data": None,
        }

        # Simulate persistent 503 errors
        with patch.object(api_client._session, "request") as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 503
            mock_response.json.return_value = error_response
            mock_request.return_value.__aenter__.return_value = mock_response

            with patch("asyncio.sleep"):
                with pytest.raises(EmagApiError) as exc_info:
                    await api_client._request("GET", "/test")

                assert "Service temporarily unavailable" in str(exc_info.value)
                # Verify all retry attempts were made
                assert mock_request.call_count == api_client.config.max_retries + 1


class TestEmagErrorMetricsAndLogging:
    """Test cases for error metrics and logging."""

    @pytest.fixture
    def api_client(self):
        """Create test API client."""
        config = EmagApiConfig(
            environment=EmagApiEnvironment.SANDBOX,
            api_username="test",
            api_password="test",
        )
        return EmagApiClient(config)

    @pytest.mark.asyncio
    async def test_error_logging_includes_context(self, api_client):
        """Test that errors include sufficient context for debugging."""
        error_response = {
            "isError": True,
            "messages": ["Product validation failed"],
            "data": {"field_errors": ["name", "price"]},
        }

        with patch.object(api_client._session, "request") as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 422
            mock_response.json.return_value = error_response
            mock_request.return_value.__aenter__.return_value = mock_response

            with pytest.raises(EmagApiError) as exc_info:
                await api_client._request("POST", "/products")

            error = exc_info.value
            assert error.status_code == 422
            assert error.details == error_response

            # Verify error message includes API context
            assert "Product validation failed" in str(error)

    @pytest.mark.asyncio
    async def test_request_metrics_tracking(self, api_client):
        """Test that request metrics are properly tracked."""
        success_response = {
            "isError": False,
            "messages": [],
            "data": {"products": []},
        }

        with patch.object(api_client._session, "request") as mock_request:
            mock_response = AsyncMock()
            mock_response.json.return_value = success_response
            mock_response.status = 200
            mock_request.return_value.__aenter__.return_value = mock_response

            initial_count = api_client._request_count
            await api_client._request("GET", "/products")

            # Verify request count was incremented
            assert api_client._request_count == initial_count + 1
