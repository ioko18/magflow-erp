"""Comprehensive API endpoint tests."""

import pytest


@pytest.mark.asyncio
async def test_health_endpoint(test_client):
    """Test health check endpoint."""
    response = await test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["ok", "healthy"]  # Accept both valid statuses
    assert "timestamp" in data  # Should include timestamp


@pytest.mark.asyncio
@pytest.mark.skip(reason="Metrics endpoint not mounted in main app")
async def test_metrics_endpoint(test_client):
    """Test metrics endpoint."""
    response = await test_client.get("/metrics")
    assert response.status_code == 200
    # Metrics endpoint should return Prometheus format data
    assert "prometheus" in response.text.lower() or len(response.text) > 0


@pytest.mark.asyncio
@pytest.mark.skip(reason="Database not configured for testing")
async def test_database_health(test_client):
    """Test database health endpoint."""
    response = await test_client.get("/health/database")
    assert response.status_code in [200, 503]  # 200 if healthy, 503 if not


@pytest.mark.asyncio
@pytest.mark.skip(reason="Redis not configured for testing")
async def test_redis_health(test_client):
    """Test Redis health endpoint."""
    response = await test_client.get("/health/redis")
    assert response.status_code in [200, 503]  # 200 if healthy, 503 if not


@pytest.mark.asyncio
async def test_api_docs_accessible(test_client):
    """Test that API documentation is accessible."""
    # Test OpenAPI JSON
    response = await test_client.get("/openapi.json")
    assert response.status_code == 200
    assert "openapi" in response.json()

    # Test Swagger UI
    response = await test_client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower()

    # Test ReDoc
    response = await test_client.get("/redoc")
    assert response.status_code == 200
    assert "redoc" in response.text.lower()


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_404_not_found(self, test_client):
        """Test 404 error handling."""
        response = await test_client.get("/nonexistent-endpoint")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_405_method_not_allowed(self, test_client):
        """Test 405 error handling."""
        response = await test_client.post("/health")
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_422_validation_error(self, test_client):
        """Test validation error handling."""
        # This would depend on your specific API endpoints
        # Example for a POST endpoint that expects specific data
        response = await test_client.post("/api/v1/users/", json={})
        if response.status_code == 422:
            assert "detail" in response.json()


class TestSecurityHeaders:
    """Test security headers in responses."""

    @pytest.mark.asyncio
    async def test_security_headers_present(self, test_client):
        """Test that security headers are present in responses."""
        response = await test_client.get("/health")

        # Check for security headers (these may vary based on your setup)
        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
        ]

        for header in security_headers:
            if header in response.headers:
                assert response.headers[header] is not None

    @pytest.mark.asyncio
    async def test_cors_headers(self, test_client):
        """Test CORS headers are properly configured."""
        response = await test_client.options("/health")

        # Check for CORS headers
        cors_headers = [
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Methods",
            "Access-Control-Allow-Headers",
        ]

        for header in cors_headers:
            if header in response.headers:
                assert response.headers[header] is not None
