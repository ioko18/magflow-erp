"""Unit tests for JWKS health check functionality."""

import os

import pytest
from app.api.health import JWKSHealthCheck, check_jwks_health


@pytest.fixture(autouse=True)
def mock_environment(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("JWKS_URL", "http://test-jwks/.well-known/jwks.json")


@pytest.mark.asyncio
async def test_check_jwks_health_success():
    """Test successful JWKS health check."""
    # Call the function under test
    result = await check_jwks_health()

    # Verify the result matches the expected structure
    assert isinstance(result, JWKSHealthCheck)
    assert result.ok is True
    assert result.url == "http://test-jwks/.well-known/jwks.json"
    assert result.error is None
    assert result.response_time_ms is None


@pytest.mark.asyncio
async def test_check_jwks_health_no_url():
    """Test JWKS health check with no URL configured."""
    # Remove the JWKS_URL environment variable
    os.environ.pop("JWKS_URL", None)
    
    # Call the function under test
    result = await check_jwks_health()
    
    # Should still return OK with default URL
    assert result.ok is True
    assert result.url == "http://localhost/.well-known/jwks.json"
