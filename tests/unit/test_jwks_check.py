"""Unit tests for JWKS health check functionality."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def mock_settings():
    with patch("app.api.v1.endpoints.health.settings") as mock:
        mock.AUTH_SERVICE_URL = "http://auth-service"
        yield mock


@pytest.fixture
def mock_httpx():
    with patch("app.api.v1.endpoints.health.httpx") as mock:
        mock.Timeout.return_value = "timeout_obj"
        yield mock


@pytest.fixture
def mock_time():
    with patch("app.api.v1.endpoints.health.time") as mock:
        mock.monotonic.return_value = 1000.0
        yield mock


@pytest.mark.asyncio
async def test_check_jwks_success(mock_time, mock_httpx, mock_settings):
    """Test successful JWKS health check."""
    from app.api.v1.endpoints.health import _ready_state, check_jwks

    # Reset the ready state for this test
    _ready_state["jwks_ready"] = False

    # Create a mock response
    mock_response = AsyncMock()
    mock_response.status_code = 200

    # Create a mock client
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = mock_response

    # Setup the mocks
    mock_httpx.AsyncClient.return_value = mock_client

    # Call the function under test
    result = await check_jwks()

    # Verify the result matches the actual implementation
    assert result["status"] == "healthy"
    assert result["message"] == "JWKS endpoint is accessible"
    assert result["check_type"] == "jwks"
    assert "timestamp" in result
    assert "metadata" in result
    assert result["metadata"]["url"] == "http://auth-service/.well-known/jwks.json"
    assert result["metadata"]["status_code"] == 200
    assert "response_time_ms" in result["metadata"]

    # Verify timestamp is in ISO format
    datetime.fromisoformat(result["timestamp"])

    # Verify the client was created with the correct timeout
    mock_httpx.Timeout.assert_called_once_with(2.0, connect=1.0)
    mock_httpx.AsyncClient.assert_called_once_with(timeout="timeout_obj")

    # Verify the client was called with the correct URL
    mock_client.get.assert_awaited_once_with(
        "http://auth-service/.well-known/jwks.json",
    )

    # Verify the ready state was updated
    assert _ready_state["jwks_ready"] is True
