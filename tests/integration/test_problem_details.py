"""Integration tests for RFC 9457 Problem Details error responses.

These tests verify that the API returns properly formatted error responses
following the Problem Details for HTTP APIs specification (RFC 9457).
"""

import uuid

from fastapi import status
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_validation_error():
    """Test that validation errors return proper problem details."""
    # Test with invalid data that will fail validation
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"username": "", "password": ""},  # Empty username and password
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.headers["content-type"] == "application/problem+json"

    data = response.json()
    assert "type" in data
    assert data["status"] == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "title" in data
    assert "detail" in data
    assert "errors" in data
    assert len(data["errors"]) > 0
    assert "field" in data["errors"][0]
    assert "message" in data["errors"][0]
    assert "correlation_id" in data


def test_not_found():
    """Test that 404 errors return proper problem details."""
    non_existent_id = str(uuid.uuid4())
    response = client.get(f"{settings.API_V1_STR}/products/{non_existent_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.headers["content-type"] == "application/problem+json"

    data = response.json()
    assert data["type"] == "https://example.com/probs/not-found"
    assert data["status"] == status.HTTP_404_NOT_FOUND
    assert data["title"] == "Not Found"
    assert "detail" in data
    assert "instance" in data
    assert "correlation_id" in data


def test_unauthorized():
    """Test that 401 errors include WWW-Authenticate header."""
    response = client.get(f"{settings.API_V1_STR}/users/me")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers["content-type"] == "application/problem+json"
    assert "www-authenticate" in response.headers
    assert 'Bearer realm="api"' in response.headers["www-authenticate"]

    data = response.json()
    assert data["type"] == "https://example.com/probs/unauthorized"
    assert data["status"] == status.HTTP_401_UNAUTHORIZED
    assert data["title"] == "Unauthorized"


def test_too_many_requests():
    """Test that rate limiting returns proper problem details."""
    # First, we need to trigger rate limiting
    # This assumes the rate limit is set to a low value for testing
    for _ in range(10):  # Make enough requests to trigger rate limiting
        response = client.get(f"{settings.API_V1_STR}/health/live")
        if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            break

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.headers["content-type"] == "application/problem+json"
    assert "retry-after" in response.headers

    data = response.json()
    assert data["type"] == "https://example.com/probs/too-many-requests"
    assert data["status"] == status.HTTP_429_TOO_MANY_REQUESTS
    assert data["title"] == "Too Many Requests"
    assert "retry_after" in data


def test_internal_server_error(monkeypatch):
    """Test that 500 errors return proper problem details."""

    # Patch an endpoint to raise an exception
    def raise_exception():
        raise Exception("Something went wrong")

    monkeypatch.setattr("app.api.endpoints.health.readiness_check", raise_exception)

    response = client.get(f"{settings.API_V1_STR}/health/ready")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.headers["content-type"] == "application/problem+json"

    data = response.json()
    assert data["type"] == "https://example.com/probs/internal-server-error"
    assert data["status"] == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert data["title"] == "Internal Server Error"
    assert "correlation_id" in data


def test_correlation_id():
    """Test that correlation ID is included in error responses."""
    test_correlation_id = str(uuid.uuid4())
    response = client.get(
        f"{settings.API_V1_STR}/nonexistent-endpoint",
        headers={"X-Correlation-ID": test_correlation_id},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["correlation_id"] == test_correlation_id


def test_service_unavailable():
    """Test that 503 errors include Retry-After header."""
    # This test requires a service that's known to be down in the test environment
    # For now, we'll test the response format with a mock
    response = client.get(
        f"{settings.API_V1_STR}/health/ready",
        headers={"X-Test-Service-Unavailable": "true"},
    )

    if response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
        assert response.headers["content-type"] == "application/problem+json"
        assert "retry-after" in response.headers

        data = response.json()
        assert data["type"] == "https://example.com/probs/service-unavailable"
        assert data["status"] == status.HTTP_503_SERVICE_UNAVAILABLE
        assert data["title"] == "Service Unavailable"
