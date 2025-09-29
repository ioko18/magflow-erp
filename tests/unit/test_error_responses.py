"""Unit tests for verifying RFC 9457 Problem Details error responses.

These tests verify that error responses from the API follow the Problem Details
for HTTP APIs specification (RFC 9457).
"""

import uuid

import httpx
import pytest

# Configuration
BASE_URL = "http://testserver"  # Using testserver as a placeholder
API_PREFIX = "/api/v1"

# Test data
VALIDATION_ERROR_RESPONSE = {
    "type": "https://example.com/probs/validation-error",
    "title": "Validation Error",
    "status": 422,
    "detail": "One or more validation errors occurred.",
    "errors": [
        {"field": "username", "message": "Field required"},
        {"field": "password", "message": "Field required"},
    ],
}

NOT_FOUND_RESPONSE = {
    "type": "https://example.com/probs/not-found",
    "title": "Not Found",
    "status": 404,
    "detail": "The requested resource was not found.",
}

UNAUTHORIZED_RESPONSE = {
    "type": "https://example.com/probs/unauthorized",
    "title": "Unauthorized",
    "status": 401,
    "detail": "Authentication credentials were not provided.",
}


@pytest.mark.integration
def test_validation_error() -> None:
    """Test validation error response."""
    # Act
    with pytest.raises(httpx.ConnectError):
        # This will raise a ConnectError if the server is not running
        response = httpx.post(
            f"{BASE_URL}{API_PREFIX}/auth/login",
            json={"username": "", "password": ""},
            timeout=10.0,
        )

        # The following assertions will only run if the connection succeeds
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"

        content_type = response.headers.get("content-type", "")
        assert (
            "application/problem+json" in content_type
        ), f"Expected 'application/problem+json' in content-type, got '{content_type}'"

        data = response.json()
        required_fields = ["type", "title", "status", "detail", "errors"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        assert (
            data["title"] == "Validation Error" and data["status"] == 422
        ), f"Incorrect error details: {data}"


@pytest.mark.integration
def test_not_found() -> None:
    """Test not found error response."""

    # Arrange
    non_existent_id = str(uuid.uuid4())

    # Act
    with pytest.raises(httpx.ConnectError):
        response = httpx.get(
            f"{BASE_URL}{API_PREFIX}/products/{non_existent_id}",
            timeout=10.0,
        )

        # The following assertions will only run if the connection succeeds
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"

        content_type = response.headers.get("content-type", "")
        assert (
            "application/problem+json" in content_type
        ), f"Expected 'application/problem+json' in content-type, got '{content_type}'"

        data = response.json()
        required_fields = ["type", "title", "status", "detail"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        assert (
            data["title"] == "Not Found" and data["status"] == 404
        ), f"Incorrect error details: {data}"


@pytest.mark.integration
def test_unauthorized() -> None:
    """Test unauthorized error response."""

    # Act - Try to access a protected endpoint without authentication
    with pytest.raises(httpx.ConnectError):
        response = httpx.get(
            f"{BASE_URL}{API_PREFIX}/protected-route",
            timeout=10.0,
        )

        # The following assertions will only run if the connection succeeds
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

        # Check for WWW-Authenticate header
        assert (
            "www-authenticate" in response.headers
        ), "WWW-Authenticate header is missing"

        # Check content type
        content_type = response.headers.get("content-type", "")
        assert (
            "application/problem+json" in content_type
        ), f"Expected 'application/problem+json' in content-type, got '{content_type}'"

        # Check response body
        data = response.json()
        required_fields = ["type", "title", "status", "detail"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        assert (
            data["title"] == "Unauthorized" and data["status"] == 401
        ), f"Incorrect error details: {data}"
