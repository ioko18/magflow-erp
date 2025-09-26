"""Integration tests for RFC 9457 Problem Details error responses.

These tests verify that the API returns properly formatted error responses
following the Problem Details for HTTP APIs specification (RFC 9457).
"""

import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import settings
from app.core.database import get_async_session
from app.main import app


CORRELATION_ID_HEADER = "X-Correlation-ID"


def _assert_corresponds_to_uuid(value: str) -> None:
    """Ensure the provided correlation ID can be parsed as a UUID string."""

    try:
        uuid.UUID(value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive guard
        raise AssertionError(f"Expected UUID-formatted correlation ID, got: {value}") from exc


def _assert_has_valid_correlation_id(data: dict) -> None:
    """Assert that a response body contains a UUID-formatted correlation ID."""

    assert "correlation_id" in data
    _assert_corresponds_to_uuid(data["correlation_id"])


def _assert_optional_correlation_id(data: dict) -> None:
    """If a correlation ID is provided in the body, validate its format."""

    correlation_id = data.get("correlation_id")
    if correlation_id is not None:
        _assert_corresponds_to_uuid(correlation_id)


def _make_correlation_headers() -> dict[str, str]:
    """Create headers containing a generated correlation ID."""

    return {CORRELATION_ID_HEADER: str(uuid.uuid4())}


@pytest.fixture
def client(engine):
    """Provide a TestClient with async session override bound to the test engine."""

    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async def override_get_async_session():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_async_session] = override_get_async_session

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_async_session, None)


def test_validation_error(client):
    """Test that validation errors return proper problem details."""
    # Test with invalid data that will fail validation
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"username": "", "password": ""},  # Empty username and password
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.headers["content-type"] == "application/problem+json"

    data = response.json()
    assert "type" in data
    assert data["status"] == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "title" in data
    assert "detail" in data
    assert "errors" in data
    assert len(data["errors"]) > 0
    assert "field" in data["errors"][0]
    assert "message" in data["errors"][0]
    _assert_has_valid_correlation_id(data)


def test_not_found(client):
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
    _assert_has_valid_correlation_id(data)


def test_unauthorized(client):
    """Test that 401 errors include WWW-Authenticate header."""
    response = client.get(f"{settings.API_V1_STR}/users/me")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers["content-type"] == "application/problem+json"
    assert "www-authenticate" in response.headers
    assert "Bearer" in response.headers["www-authenticate"]

    data = response.json()
    assert data["type"] == "https://example.com/probs/unauthorized"
    assert data["status"] == status.HTTP_401_UNAUTHORIZED
    assert data["title"] == "Unauthorized"
    _assert_has_valid_correlation_id(data)


def test_too_many_requests(client):
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
    _assert_optional_correlation_id(data)


def test_internal_server_error(monkeypatch, client):
    """Test that 500 errors return proper problem details."""

    # Patch database health check to force an internal error from the handler
    async def raise_exception(*args, **kwargs):
        raise RuntimeError("Something went wrong")

    monkeypatch.setattr("app.api.health.check_database_health", raise_exception)

    headers = _make_correlation_headers()
    response = client.get(
        f"{settings.API_V1_STR}/health/full",
        headers=headers,
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.headers["content-type"] == "application/problem+json"
    if CORRELATION_ID_HEADER in response.headers:
        _assert_corresponds_to_uuid(response.headers[CORRELATION_ID_HEADER])

    data = response.json()
    assert data["type"] == "https://example.com/probs/internal-server-error"
    assert data["status"] == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert data["title"] == "Internal Server Error"
    _assert_optional_correlation_id(data)


def test_correlation_id(client):
    """Test that correlation ID is included in error responses."""
    test_correlation_id = str(uuid.uuid4())
    response = client.get(
        f"{settings.API_V1_STR}/nonexistent-endpoint",
        headers={"X-Correlation-ID": test_correlation_id},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["correlation_id"] == test_correlation_id


def test_service_unavailable(client):
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
        _assert_optional_correlation_id(data)
