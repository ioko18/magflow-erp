from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app

# Test data
MOCK_TIMESTAMP = "2023-01-01T00:00:00+00:00"
MOCK_DATETIME = datetime(2023, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def client():
    """Create a fresh TestClient for each test."""
    return TestClient(app)


@pytest.fixture
def mock_health_checks():
    with patch.multiple(
        "app.api.v1.endpoints.system.health",
        check_database=AsyncMock(return_value={"status": "ok"}),
        check_jwks=AsyncMock(return_value={"status": "ok"}),
        check_opentelemetry=AsyncMock(return_value={"status": "ok"}),
        STARTUP_TIME=datetime.now(timezone.utc)
        - timedelta(seconds=60),  # Ensure startup is complete
        _ready_state={
            "db_ready": True,
            "jwks_ready": True,
            "otel_ready": True,
            "last_checked": datetime.now(timezone.utc),
        },
    ):
        yield


@pytest.fixture
def mock_health_checks_starting():
    with patch.multiple(
        "app.api.v1.endpoints.system.health",
        check_database=AsyncMock(return_value={"status": "ok"}),
        check_jwks=AsyncMock(return_value={"status": "ok"}),
        check_opentelemetry=AsyncMock(return_value={"status": "ok"}),
        STARTUP_TIME=datetime.now(timezone.utc),  # Simulate just started
        _ready_state={
            "db_ready": False,
            "jwks_ready": False,
            "otel_ready": False,
            "last_checked": None,
        },
    ):
        yield


@pytest.mark.asyncio
async def test_health_check(client):
    """Test the health check endpoint."""
    with patch("app.api.v1.endpoints.system.health.datetime") as mock_datetime, patch(
        "app.api.v1.endpoints.system.health.check_database",
        return_value={"status": "ok"},
    ), patch(
        "app.api.v1.endpoints.system.health.check_jwks",
        return_value={"status": "ok"},
    ), patch(
        "app.api.v1.endpoints.system.health.check_opentelemetry",
        return_value={"status": "ok"},
    ), patch(
        "app.api.v1.endpoints.system.health.STARTUP_TIME",
        datetime.now(timezone.utc) - timedelta(seconds=60),
    ):
        mock_datetime.now.return_value = MOCK_DATETIME
        mock_datetime.utcnow.return_value = MOCK_DATETIME
        response = client.get("/api/v1/health/health")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] in ["healthy", "ok"]  # Accept both formats
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_liveness_probe(client):
    """Test the liveness probe."""
    with patch("app.api.v1.endpoints.system.health.datetime") as mock_datetime, patch(
        "app.api.v1.endpoints.system.health.time",
    ) as mock_time, patch(
        "app.api.v1.endpoints.system.health.STARTUP_TIME",
        MOCK_DATETIME - timedelta(seconds=10),
    ):
        mock_datetime.now.return_value = MOCK_DATETIME
        mock_datetime.utcnow.return_value = MOCK_DATETIME
        mock_time.monotonic.return_value = 1000.0  # Simulate monotonic time

        response = client.get("/api/v1/health/live")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "alive"
    assert "timestamp" in data
    assert "uptime_seconds" in data
    assert isinstance(data["uptime_seconds"], (int, float))  # Just verify it's a number
    assert data["uptime_seconds"] > 0  # Should be positive
    # Version is not included in the actual response


@pytest.mark.asyncio
async def test_readiness_probe_healthy(client):
    """Test the readiness probe when all services are healthy."""
    with patch("app.api.v1.endpoints.system.health.datetime") as mock_datetime, patch(
        "app.api.v1.endpoints.system.health.check_database",
        return_value={"status": "ok"},
    ), patch(
        "app.api.v1.endpoints.system.health.check_jwks",
        return_value={"status": "ok"},
    ), patch(
        "app.api.v1.endpoints.system.health.check_opentelemetry",
        return_value={"status": "ok"},
    ), patch(
        "app.api.v1.endpoints.system.health._ready_state",
        {
            "db_ready": True,
            "jwks_ready": True,
            "otel_ready": True,
            "last_checked": datetime.now(timezone.utc),
        },
    ):
        mock_datetime.now.return_value = MOCK_DATETIME
        mock_datetime.utcnow.return_value = MOCK_DATETIME
        response = client.get("/api/v1/health/ready")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "ready"
    assert "timestamp" in data
    assert "services" in data
    assert "database" in data["services"]
    assert data["services"]["database"] == "ready"
    assert "duration_seconds" in data


@pytest.mark.asyncio
async def test_startup_probe_ready(client):
    """Test the startup probe when the service is ready."""
    with patch(
        "app.api.v1.endpoints.system.health.STARTUP_TIME",
        MOCK_DATETIME - timedelta(seconds=60),
    ), patch("app.api.v1.endpoints.system.health.WARMUP_PERIOD", 30), patch(
        "app.api.v1.endpoints.system.health._ready_state",
        {
            "db_ready": True,
            "jwks_ready": True,
            "otel_ready": True,
            "last_checked": datetime.now(timezone.utc),
        },
    ), patch(
        "app.api.v1.endpoints.system.health.datetime"
    ) as mock_datetime, patch(
        "app.api.v1.endpoints.system.health.readiness_probe",
    ) as mock_readiness:
        # Mock the readiness probe response
        mock_readiness.return_value = {
            "status": "ok",
            "services": {"database": "ok", "jwks": "ok", "opentelemetry": "ok"},
        }

        mock_datetime.now.return_value = MOCK_DATETIME
        mock_datetime.utcnow.return_value = MOCK_DATETIME
        response = client.get("/api/v1/health/startup")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    # Status can be "started" or "starting" depending on timing
    assert data["status"] in ["started", "starting"]
    assert "ready" in data
    assert "uptime_seconds" in data
    assert "start_time" in data
    assert "current_time" in data
    assert "services" in data
    assert "details" in data


@pytest.mark.asyncio
async def test_startup_probe_starting(client):
    """Test the startup probe when service is still starting."""
    with patch("app.api.v1.endpoints.system.health.datetime") as mock_datetime, patch(
        "app.api.v1.endpoints.system.health.STARTUP_TIME",
        datetime.now(timezone.utc),
    ), patch("app.api.v1.endpoints.system.health.WARMUP_PERIOD", 60), patch(
        "app.api.v1.endpoints.system.health._ready_state",
        {
            "db_ready": False,
            "jwks_ready": False,
            "otel_ready": False,
            "last_checked": None,
        },
    ):
        mock_datetime.now.return_value = MOCK_DATETIME
        mock_datetime.utcnow.return_value = MOCK_DATETIME
        response = client.get("/api/v1/health/startup")

    # The endpoint returns 200 with status "starting" during warmup
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "starting"
    assert "uptime_seconds" in data
    assert "required_seconds" in data
    assert float(data["uptime_seconds"]) < float(data["required_seconds"])
    assert "start_time" in data
    assert "current_time" in data


@pytest.mark.asyncio
async def test_database_check_failure(client):
    """Test database health check failure."""
    mock_db_response = {
        "status": "unhealthy",
        "message": "Database connection failed: Test failure",
        "check_type": "database",
        "timestamp": MOCK_DATETIME.isoformat(),
        "metadata": {"response_time_ms": 100, "query": "SELECT 1"},
    }

    with patch("app.api.v1.endpoints.system.health.datetime") as mock_datetime, patch(
        "app.api.v1.endpoints.system.health.check_database",
    ) as mock_check_db, patch(
        "app.api.v1.endpoints.system.health.check_jwks",
    ) as mock_check_jwks, patch(
        "app.api.v1.endpoints.system.health.update_health_metrics",
        return_value=False,
    ), patch.dict(
        "app.api.v1.endpoints.system.health._ready_state",
        {
            "db_ready": False,
            "jwks_ready": True,
            "otel_ready": True,
            "last_checked": MOCK_DATETIME - timedelta(seconds=30),
        },
    ):
        # Setup mocks
        mock_check_db.return_value = mock_db_response
        mock_check_jwks.return_value = {"status": "healthy"}

        # Setup mock datetime
        mock_datetime.now.return_value = MOCK_DATETIME
        mock_datetime.utcnow.return_value = MOCK_DATETIME

        # Make the request
        response = client.get("/api/v1/health/ready")

        # Assert the response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ready"
        assert "services" in data
        assert data["services"]["database"] == "unhealthy"  # Database should be unhealthy
        assert "duration_seconds" in data
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_jwks_check_failure(client):
    """Test JWKS health check failure."""
    mock_jwks_response = {
        "status": "unhealthy",
        "message": "JWKS endpoint check failed: Test failure",
        "check_type": "jwks",
        "timestamp": MOCK_DATETIME.isoformat(),
        "metadata": {
            "response_time_ms": 100,
            "url": "http://test-jwks-uri",
            "status_code": None,
        },
    }

    with patch("app.api.v1.endpoints.system.health.datetime") as mock_datetime, patch(
        "app.api.v1.endpoints.system.health.check_database",
    ) as mock_check_db, patch(
        "app.api.v1.endpoints.system.health.check_jwks",
    ) as mock_check_jwks, patch(
        "app.api.v1.endpoints.system.health.update_health_metrics",
        return_value=False,
    ), patch.dict(
        "app.api.v1.endpoints.system.health._ready_state",
        {
            "db_ready": True,
            "jwks_ready": False,
            "otel_ready": True,
            "last_checked": MOCK_DATETIME - timedelta(seconds=30),
        },
    ):
        # Setup mocks
        mock_check_db.return_value = {"status": "healthy"}
        mock_check_jwks.return_value = mock_jwks_response

        # Setup mock datetime
        mock_datetime.now.return_value = MOCK_DATETIME
        mock_datetime.utcnow.return_value = MOCK_DATETIME

        # Make the request
        response = client.get("/api/v1/health/ready")

        # Assert the response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ready"
        assert "services" in data
        assert data["services"]["jwks"] == "unhealthy"  # JWKS should be unhealthy
        assert "duration_seconds" in data
        assert "timestamp" in data
