"""Tests for rate limiting functionality."""

import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core.rate_limiting import (
    EXCLUDED_PATHS,
    RATE_LIMITS,
    get_rate_limit_key_for_path,
    init_rate_limiter,
    should_rate_limit,
)


# Mock Redis for testing
@pytest.fixture(autouse=True)
def mock_redis():
    with patch("fastapi_limiter.FastAPILimiter.redis") as mock_redis:
        mock_redis.ping.return_value = True
        yield mock_redis


# Initialize test client
@pytest.fixture
def test_client():
    # Create a fresh app instance for each test to avoid middleware conflicts
    test_app = FastAPI()

    # Add test endpoints with different rate limits
    @test_app.get("/api/v1/test/default")
    async def test_default():
        return {"message": "Default rate limited endpoint"}

    @test_app.get("/api/v1/test/auth")
    async def test_auth():
        return {"message": "Auth rate limited endpoint"}

    @test_app.get("/api/v1/test/read")
    async def test_read():
        return {"message": "Read rate limited endpoint"}

    # Add a health endpoint that should be excluded
    @test_app.get("/health/live")
    async def health_check():
        return {"status": "ok"}

    @test_app.get("/health/ready")
    async def health_ready():
        return {"status": "ready"}

    @test_app.get("/health/startup")
    async def health_startup():
        return {"status": "started"}

    # Initialize rate limiter with test app
    init_rate_limiter(test_app)

    with TestClient(test_app) as client:
        yield client


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_should_rate_limit_excluded_paths(self):
        """Test that excluded paths are not rate limited."""
        mock_request = MagicMock(spec=Request)

        for path in EXCLUDED_PATHS:
            mock_request.url.path = path
            assert (
                should_rate_limit(mock_request, rate_limit_health=False) is False
            ), f"Path {path} should be excluded from rate limiting"

    def test_health_endpoints_not_rate_limited(self, test_client):
        """Test that health endpoints are not rate limited."""
        # Make multiple requests to health endpoint (more than default rate limit)
        for _ in range(20):
            response = test_client.get("/health/live")
            assert response.status_code == 200
            assert "X-RateLimit-Limit" not in response.headers
            assert "X-RateLimit-Remaining" not in response.headers

    def test_default_rate_limit_applied(self, test_client):
        """Test that default rate limit is applied to non-excluded paths."""
        # Get the default rate limit values
        default_limit, window_seconds = RATE_LIMITS["default"]

        # Make requests up to the limit
        for i in range(default_limit):
            response = test_client.get("/api/v1/test/default")
            assert response.status_code == 200
            assert int(response.headers["X-RateLimit-Limit"]) == default_limit
            assert (
                int(response.headers["X-RateLimit-Remaining"]) == default_limit - i - 1
            )

        # Next request should be rate limited
        response = test_client.get("/api/v1/test/default")
        assert response.status_code == 429  # Too Many Requests
        assert "Retry-After" in response.headers

    def test_path_specific_rate_limits(self, test_client):
        """Test that path-specific rate limits are applied correctly."""
        # Test auth rate limit
        auth_limit, _ = RATE_LIMITS["auth"]
        for i in range(auth_limit):
            response = test_client.get("/api/v1/test/auth")
            assert response.status_code == 200
            assert int(response.headers["X-RateLimit-Limit"]) == auth_limit
            assert int(response.headers["X-RateLimit-Remaining"]) == auth_limit - i - 1

        # Next request should be rate limited
        response = test_client.get("/api/v1/test/auth")
        assert response.status_code == 429

    def test_rate_limit_reset(self, test_client, monkeypatch):
        """Test that rate limits reset after the time window."""
        # Make requests up to the limit
        default_limit, window_seconds = RATE_LIMITS["default"]

        for _ in range(default_limit):
            test_client.get("/api/v1/test/default")

        # Next request should be rate limited
        response = test_client.get("/api/v1/test/default")
        assert response.status_code == 429

        # Fast-forward time to after the rate limit window
        with patch("time.time") as mock_time:
            mock_time.return_value = time.time() + window_seconds + 1
            response = test_client.get("/api/v1/test/default")
            assert response.status_code == 200

    def test_get_rate_limit_key_for_path(self):
        """Test that the correct rate limit key is returned for different paths."""
        # Test path that matches a specific rate limit
        assert get_rate_limit_key_for_path("/api/v1/auth/login") == "auth"
        assert get_rate_limit_key_for_path("/api/v1/products/123") == "read"

        # Test path that should use default rate limit
        assert get_rate_limit_key_for_path("/api/v1/unknown/endpoint") == "default"

    @pytest.mark.asyncio
    async def test_health_endpoints_exempt_from_rate_limiting(self, test_client):
        """Verify that health endpoints are explicitly exempt from rate limiting."""
        # List of health endpoints to test
        health_endpoints = ["/health/live", "/health/ready", "/health/startup"]

        # Test each health endpoint with multiple rapid requests
        for endpoint in health_endpoints:
            # Make several requests in quick succession
            responses = [test_client.get(endpoint) for _ in range(5)]

            # All responses should be successful (200 OK)
            for response in responses:
                assert (
                    response.status_code == 200
                ), f"Endpoint {endpoint} returned {response.status_code}. Response: {response.text}"
                # Verify no rate limit headers are present
                assert "X-RateLimit-Limit" not in response.headers
                assert "X-RateLimit-Remaining" not in response.headers


# Run the tests
if __name__ == "__main__":
    pytest.main()
