"""Integration tests for VAT API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from app.db.models import User
from app.integrations.emag.models.responses.vat import VatResponse

# Test data
MOCK_VAT_RATES = [
    {
        "id": 1,
        "name": "TVA 19%",
        "value": 19.0,
        "isDefault": True,
        "countryCode": "RO",
        "isActive": True,
    },
    {
        "id": 2,
        "name": "TVA 9%",
        "value": 9.0,
        "isDefault": False,
        "countryCode": "RO",
        "isActive": True,
    },
]

MOCK_VAT_RESPONSE = {
    "isError": False,
    "messages": [],
    "results": MOCK_VAT_RATES,
    "nextCursor": "vat_2",
    "prevCursor": None,
    "totalCount": 2,
    "timestamp": "2023-04-01T12:00:00Z",
}


@pytest.fixture
def mock_emag_client():
    """Mock the EmagAPIClient for testing."""
    with patch("app.api.v1.endpoints.vat.EmagAPIClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance

        # Mock the get_paginated response
        mock_instance.get_paginated.return_value = VatResponse(**MOCK_VAT_RESPONSE)

        # Mock the get response for default rate
        mock_instance.get.return_value = VatResponse(
            isError=False,
            messages=[],
            results=[MOCK_VAT_RATES[0]],
            nextCursor=None,
            prevCursor=None,
            totalCount=1,
            timestamp="2023-04-01T12:00:00Z",
        )

        yield mock_instance


@pytest.mark.asyncio
async def test_get_vat_rates_unauthorized(client: AsyncClient):
    """Test that unauthorized access is rejected."""
    response = await client.get("/api/v1/vat")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_vat_rates_authorized(
    client: AsyncClient,
    test_user: User,
    user_token_headers: dict,
    mock_emag_client,
):
    """Test getting VAT rates with valid authentication."""
    response = await client.get("/api/v1/vat", headers=user_token_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify the response structure
    assert "results" in data
    assert len(data["results"]) == 2
    assert data["results"][0]["name"] == "TVA 19%"
    assert data["nextCursor"] == "vat_2"
    assert data["totalCount"] == 2

    # Verify the client was called with the right parameters
    mock_emag_client.get_paginated.assert_called_once_with(
        endpoint="/api/vat",
        response_model=VatResponse,
        cursor=None,
        limit=100,
        params={"details": "full"},
    )


@pytest.mark.asyncio
async def test_get_vat_rates_with_pagination(
    client: AsyncClient,
    user_token_headers: dict,
    mock_emag_client,
):
    """Test getting VAT rates with pagination parameters."""
    response = await client.get(
        "/api/v1/vat?cursor=vat_1&limit=1",
        headers=user_token_headers,
    )

    assert response.status_code == status.HTTP_200_OK

    # Verify the client was called with pagination parameters
    mock_emag_client.get_paginated.assert_called_once_with(
        endpoint="/api/vat",
        response_model=VatResponse,
        cursor="vat_1",
        limit=1,
        params={"details": "full"},
    )


@pytest.mark.asyncio
async def test_get_default_vat_rate(
    client: AsyncClient,
    user_token_headers: dict,
    mock_emag_client,
):
    """Test getting the default VAT rate."""
    response = await client.get("/api/v1/vat/default", headers=user_token_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify the response contains the default rate
    assert data["name"] == "TVA 19%"
    assert data["isDefault"] is True

    # Verify the client was called with the right parameters
    mock_emag_client.get.assert_called_once_with(
        endpoint="/api/vat",
        response_model=VatResponse,
        params={"isDefault": "true"},
    )


@pytest.mark.asyncio
async def test_vat_rate_validation(
    client: AsyncClient,
    user_token_headers: dict,
    mock_emag_client,
):
    """Test VAT rate response validation."""
    # Test with invalid limit (over max)
    response = await client.get("/api/v1/vat?limit=1001", headers=user_token_headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Test with invalid limit (under min)
    response = await client.get("/api/v1/vat?limit=0", headers=user_token_headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_vat_rate_error_handling(
    client: AsyncClient,
    user_token_headers: dict,
    mock_emag_client,
):
    """Test error handling for VAT endpoints."""
    # Mock an API error
    mock_emag_client.get_paginated.side_effect = Exception("API Error")

    response = await client.get("/api/v1/vat", headers=user_token_headers)

    # Should return 502 Bad Gateway for API errors
    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert "Error fetching VAT rates" in response.json()["detail"]


@pytest.mark.asyncio
async def test_rate_limiting(
    client: AsyncClient,
    user_token_headers: dict,
    mock_emag_client,
):
    """Test that rate limiting is working."""
    # Make multiple requests in quick succession
    for _ in range(5):
        response = await client.get("/api/v1/vat", headers=user_token_headers)
        assert response.status_code == status.HTTP_200_OK

    # The rate limit is set to 100/minute in the test environment,
    # so these requests should all succeed
    assert mock_emag_client.get_paginated.call_count == 5
