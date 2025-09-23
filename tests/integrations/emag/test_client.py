"""Tests for the eMAG API client."""

from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.emag.client import EmagAPIClient
from app.integrations.emag.config import EmagAccountType
from app.integrations.emag.exceptions import (
    EmagAPIError,
    EmagAuthError,
    EmagError,
    EmagRateLimitError,
)


@pytest.fixture
def mock_session():
    """Create a mock aiohttp.ClientSession."""
    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session_class.return_value = mock_session
        yield mock_session


@pytest.fixture
def emag_client():
    """Create an EmagAPIClient instance for testing."""
    return EmagAPIClient(account_type=EmagAccountType.MAIN)


@pytest.mark.asyncio
async def test_get_auth_token(emag_client, mock_session):
    """Test authentication token generation."""
    # Set test credentials
    emag_client.account_config.username = "test_user"
    emag_client.account_config.password = "test_pass"

    # Get auth token
    token = await emag_client._get_auth_token()

    # Verify the token is a base64 encoded string of "test_user:test_pass"
    import base64

    expected = base64.b64encode(b"test_user:test_pass").decode("utf-8")
    assert token == expected

    # Verify token is cached
    assert emag_client._auth_token == expected


@pytest.mark.asyncio
async def test_make_request_success(emag_client, mock_session):
    """Test successful API request."""
    # Mock response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"isError": False, "results": "success"}
    mock_response.headers = {}

    # Configure mock session
    mock_session.request.return_value.__aenter__.return_value = mock_response

    # Make request
    result = await emag_client._make_request(
        "GET",
        "/test",
        response_model=dict,
        is_order_endpoint=False,
    )

    # Verify result
    assert result == {"isError": False, "results": "success"}

    # Verify request was made with correct parameters
    mock_session.request.assert_called_once()
    args, kwargs = mock_session.request.call_args
    assert args[0] == "GET"
    assert args[1].endswith("/test")
    assert kwargs["headers"]["X-Client-Id"] == emag_client.account_config.username


@pytest.mark.asyncio
async def test_make_request_auth_error(emag_client, mock_session):
    """Test authentication error handling."""
    # Mock 401 response
    mock_response = AsyncMock()
    mock_response.status = 401
    mock_response.text.return_value = "Unauthorized"
    mock_session.request.return_value.__aenter__.return_value = mock_response

    # Make request and expect auth error
    with pytest.raises(EmagAuthError):
        await emag_client._make_request("GET", "/test")

    # Verify auth token was cleared
    assert emag_client._auth_token is None


@pytest.mark.asyncio
async def test_make_request_rate_limit(emag_client, mock_session):
    """Test rate limit error handling."""
    # Mock 429 response
    mock_response = AsyncMock()
    mock_response.status = 429
    mock_response.headers = {"Retry-After": "5"}
    mock_session.request.return_value.__aenter__.return_value = mock_response

    # Make request and expect rate limit error
    with pytest.raises(EmagRateLimitError):
        await emag_client._make_request("GET", "/test")


@pytest.mark.asyncio
async def test_make_request_api_error(emag_client, mock_session):
    """Test API error handling."""
    # Mock error response with JSON body
    mock_response = AsyncMock()
    mock_response.status = 400
    mock_response.json.return_value = {"isError": True, "messages": ["Invalid request"]}
    mock_session.request.return_value.__aenter__.return_value = mock_response

    # Make request and expect API error
    with pytest.raises(EmagAPIError) as exc_info:
        await emag_client._make_request("GET", "/test")

    # Verify error details
    assert exc_info.value.status_code == 400
    assert "Invalid request" in str(exc_info.value)


@pytest.mark.asyncio
async def test_convenience_methods(emag_client, mock_session):
    """Test convenience methods (get, post, put, delete)."""
    # Mock response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"status": "success"}
    mock_response.headers = {}
    mock_session.request.return_value.__aenter__.return_value = mock_response

    # Test GET
    await emag_client.get("/test")
    args, _ = mock_session.request.call_args
    assert args[0] == "GET"

    # Test POST
    await emag_client.post("/test", data={"key": "value"})
    args, kwargs = mock_session.request.call_args
    assert args[0] == "POST"
    assert kwargs["json"] == {"key": "value"}

    # Test PUT
    await emag_client.put("/test/1", data={"key": "updated"})
    args, kwargs = mock_session.request.call_args
    assert args[0] == "PUT"
    assert kwargs["json"] == {"key": "updated"}

    # Test DELETE
    await emag_client.delete("/test/1")
    args, _ = mock_session.request.call_args
    assert args[0] == "DELETE"


@pytest.mark.asyncio
async def test_circuit_breaker(emag_client, mock_session):
    """Test that the circuit breaker is triggered after multiple failures."""
    # Mock a failing request
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.text.return_value = "Internal Server Error"
    mock_session.request.return_value.__aenter__.return_value = mock_response

    # Make several failing requests
    for _ in range(3):
        with pytest.raises(EmagAPIError):
            await emag_client._make_request("GET", "/test")

    # The circuit breaker should now be open
    with pytest.raises(EmagError) as exc_info:
        await emag_client._make_request("GET", "/test")

    assert "temporarily unavailable" in str(exc_info.value).lower()
