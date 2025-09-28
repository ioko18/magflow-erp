"""Basic test file to verify the test setup is working correctly."""
import pytest
from fastapi import status
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_check():
    """Test that the test framework is working."""
    assert 1 + 1 == 2

@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    """Test the health check endpoint."""
    response = await async_client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}
