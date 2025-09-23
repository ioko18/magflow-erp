"""Test edge cases for health check endpoints."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthEdgeCases:
    """Test edge cases for health check endpoints."""

    def test_live_endpoint(self):
        """Test that the live endpoint returns 200."""
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "uptime_seconds" in data

    def test_ready_endpoint(self):
        """Test that the ready endpoint returns proper response format."""
        response = client.get("/api/v1/health/ready")
        assert response.status_code in (200, 503)  # 503 if dependencies are down
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "services" in data
        assert "duration_seconds" in data

    def test_invalid_health_endpoint(self):
        """Test that invalid health endpoints return 404."""
        response = client.get("/api/v1/health/invalid")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self):
        """Test that health checks can handle concurrent requests."""

        async def make_request():
            response = client.get("/api/v1/health/live")
            return response.status_code

        # Make 5 concurrent requests
        tasks = [make_request() for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # All requests should succeed
        assert all(status == 200 for status in results)
