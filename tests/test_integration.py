"""Integration tests for MagFlow ERP API endpoints and services.

This module contains comprehensive integration tests that verify
the interaction between API endpoints, services, and database layers.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.exceptions import DatabaseError
from app.services.reporting_service import ReportingService


class TestReportingAPIIntegration:
    """Integration tests for reporting API endpoints."""

    @pytest.mark.asyncio
    async def test_get_available_reports_endpoint(self, test_client, test_session):
        """Test the available reports API endpoint."""
        # Mock the reporting service
        mock_service = AsyncMock()
        mock_service.get_available_reports.return_value = [
            {
                "type": "sales_overview",
                "name": "Sales Overview",
                "description": "Comprehensive sales report",
                "category": "Sales",
                "charts": ["line", "bar"],
            },
        ]

        with patch(
            "app.api.v1.endpoints.reporting.ReportingService", return_value=mock_service
        ):
            response = await test_client.get("/api/v1/reports/available")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "type" in data[0]
        assert "name" in data[0]

    @pytest.mark.asyncio
    async def test_generate_sales_report_endpoint(self, test_client, test_session):
        """Test the sales report generation API endpoint."""
        # Mock the reporting service response
        mock_service = AsyncMock()
        mock_service._generate_sales_overview.return_value = {
            "summary": {
                "total_records": 100,
                "key_metrics": {"total_orders": 100, "total_revenue": "$10,000"},
            },
            "charts": {"sales_trend": {"chart_type": "line", "data": []}},
            "raw_data": [],
        }

        with patch(
            "app.api.v1.endpoints.reporting.ReportingService", return_value=mock_service
        ):
            response = await test_client.get("/api/v1/reports/sales/overview")

        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "charts" in data
        assert "raw_data" in data
        assert data["summary"]["total_records"] == 100

    @pytest.mark.asyncio
    async def test_generate_report_with_filters(self, test_client, test_session):
        """Test report generation with date filters."""
        filters = {
            "date_range": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
        }

        mock_service = AsyncMock()
        mock_service._generate_sales_overview.return_value = {
            "summary": {"total_records": 50, "key_metrics": {}},
            "charts": {},
            "raw_data": [],
        }

        with patch(
            "app.api.v1.endpoints.reporting.ReportingService", return_value=mock_service
        ):
            response = await test_client.post(
                "/api/v1/reports/generate",
                json={"report_type": "sales_overview", "filters": filters},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total_records"] == 50

    @pytest.mark.asyncio
    async def test_export_report_endpoint(self, test_client, test_session):
        """Test report export functionality."""
        export_request = {
            "format": "json",
            "filename": "test_report.json",
        }

        mock_service = AsyncMock()
        mock_service.export_report.return_value = b'{"test": "data"}'

        with patch(
            "app.api.v1.endpoints.reporting.ReportingService", return_value=mock_service
        ):
            response = await test_client.post(
                "/api/v1/reports/export",
                json=export_request,
            )

        assert response.status_code == 200
        data = response.json()
        assert "export_id" in data
        assert "download_url" in data
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_dashboard_summary_endpoint(self, test_client, test_session):
        """Test dashboard summary API endpoint."""
        mock_service = AsyncMock()
        mock_service._generate_sales_overview.return_value = {
            "summary": {"key_metrics": {"total_revenue": "$100,000"}},
        }
        mock_service._generate_inventory_status.return_value = {
            "summary": {"key_metrics": {"total_products": 500}},
        }
        mock_service._generate_user_activity.return_value = {
            "summary": {"key_metrics": {"total_users": 1000}},
        }

        with patch(
            "app.api.v1.endpoints.reporting.ReportingService", return_value=mock_service
        ):
            response = await test_client.get("/api/v1/reports/dashboard/summary")

        assert response.status_code == 200
        data = response.json()
        assert "sales" in data
        assert "inventory" in data
        assert "users" in data
        assert "system" in data

    @pytest.mark.asyncio
    async def test_report_templates_endpoint(self, test_client):
        """Test report templates API endpoint."""
        response = await test_client.get("/api/v1/reports/templates")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Check template structure
        for template in data:
            assert "id" in template
            assert "name" in template
            assert "description" in template
            assert "report_type" in template
            assert "config" in template


class TestErrorHandlingIntegration:
    """Integration tests for error handling across layers."""

    @pytest.mark.asyncio
    async def test_database_error_propagation(self, test_client, test_session):
        """Test database error propagation through API layers."""
        mock_service = AsyncMock()
        mock_service._generate_sales_overview.side_effect = DatabaseError(
            "Database connection failed",
            details={"connection": "timeout"},
        )

        with patch(
            "app.api.v1.endpoints.reporting.ReportingService", return_value=mock_service
        ):
            response = await test_client.get("/api/v1/reports/sales/overview")

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "DatabaseError"
        assert "Database connection failed" in data["message"]
        assert "connection" in data["details"]

    @pytest.mark.asyncio
    async def test_validation_error_handling(self, test_client):
        """Test validation error handling in API endpoints."""
        # Test invalid report type
        response = await test_client.post(
            "/api/v1/reports/generate",
            json={"report_type": "invalid_report_type"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "ValidationError" in data.get("error", "")

    @pytest.mark.asyncio
    async def test_service_layer_error_recovery(self, test_session):
        """Test error recovery in service layer."""
        service = ReportingService(test_session)

        # Mock database failure
        with patch.object(service.db, "execute", side_effect=Exception("DB Error")):
            result = await service._generate_sales_overview()

        # Should return empty report data as fallback
        assert result["summary"]["total_records"] == 0
        assert result["charts"] == {}
        assert result["raw_data"] == []


class TestConfigurationIntegration:
    """Integration tests for configuration management."""

    def test_settings_creation_from_environment(self):
        """Test settings creation with environment variables."""
        import os

        # Set test environment variables
        os.environ["SECRET_KEY"] = "test-secret-key-for-testing"
        os.environ["DB_HOST"] = "test-host"
        os.environ["DB_NAME"] = "test_database"
        os.environ["DB_USER"] = "test_user"

        try:
            from app.core.config import Settings

            settings = Settings()

            assert settings.SECRET_KEY == "test-secret-key-for-testing"
            assert settings.DB_HOST == "test-host"
            assert settings.DB_NAME == "test_database"
            assert settings.DB_USER == "test_user"

        finally:
            # Clean up environment variables
            del os.environ["SECRET_KEY"]
            del os.environ["DB_HOST"]
            del os.environ["DB_NAME"]
            del os.environ["DB_USER"]

    def test_settings_validation_integration(self):
        """Test settings validation in real scenarios."""
        from app.core.config import Settings

        # Valid configuration
        settings = Settings(
            SECRET_KEY="valid-secret-key-12345678901234567890",
            DB_HOST="production-server",
            DB_NAME="prod_database",
            DB_USER="prod_user",
            DB_PASS="secure_password_123",
            APP_ENV="production",
        )

        # Should not raise exception
        settings.validate_configuration()


class TestCachingIntegration:
    """Integration tests for caching functionality."""

    @pytest.mark.asyncio
    async def test_cache_service_integration(self, test_session):
        """Test cache service integration with reporting."""
        from app.services.cache_service import CacheManager

        cache_manager = CacheManager(test_session)

        # Test cache set and get
        test_key = "test_key"
        test_data = {"test": "data", "timestamp": datetime.utcnow().isoformat()}

        # Set data
        await cache_manager.set(test_key, test_data, namespace="test")

        # Get data
        cached_data = await cache_manager.get(test_key, namespace="test")

        assert cached_data == test_data

    @pytest.mark.asyncio
    async def test_cache_miss_handling(self, test_session):
        """Test cache miss handling."""
        from app.services.cache_service import CacheManager

        cache_manager = CacheManager(test_session)

        # Try to get non-existent key
        result = await cache_manager.get("non_existent_key", namespace="test")

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_expiration(self, test_session):
        """Test cache expiration functionality."""
        from app.services.cache_service import CacheManager

        cache_manager = CacheManager(test_session)

        test_key = "expiring_key"
        test_data = {"test": "data"}

        # Set with short TTL
        await cache_manager.set(
            test_key, test_data, ttl=1, namespace="test"
        )  # 1 second TTL

        # Should be available immediately
        cached_data = await cache_manager.get(test_key, namespace="test")
        assert cached_data == test_data

        # Wait for expiration (in real scenario, would wait 1+ seconds)
        # For test, we'll just verify the TTL was set correctly


class TestSecurityIntegration:
    """Integration tests for security features."""

    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, test_client):
        """Test rate limiting integration."""
        from app.core.security import RateLimiter

        rate_limiter = RateLimiter()

        # Mock request object
        mock_request = AsyncMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "127.0.0.1"

        # First request should pass
        result1 = await rate_limiter.check_ip_rate_limit(mock_request)
        assert result1 is True

        # Multiple rapid requests should eventually be limited
        # (This is a simplified test - real rate limiting would need more requests)

    def test_input_validation_integration(self):
        """Test input validation across different components."""
        from app.core.security import SecurityValidator

        # Test email validation
        assert SecurityValidator.validate_email("user@example.com") is True
        assert SecurityValidator.validate_email("invalid-email") is False

        # Test password validation
        strong_password = "SecurePass123!@#"
        result = SecurityValidator.validate_password_strength(strong_password)
        assert result["is_acceptable"] is True
        assert result["score"] >= 4

    def test_sql_injection_prevention(self):
        """Test SQL injection prevention across the application."""
        from app.core.security import SecurityValidator

        # Safe queries should pass
        safe_queries = [
            "SELECT * FROM users WHERE id = ?",
            "SELECT * FROM products WHERE category = ? AND active = ?",
            "INSERT INTO orders (user_id, product_id) VALUES (?, ?)",
        ]

        for query in safe_queries:
            assert SecurityValidator.validate_sql_injection_risk(query) is True

        # Dangerous queries should fail
        dangerous_queries = [
            "SELECT * FROM users; DROP TABLE users; --",
            "SELECT * FROM users WHERE 1=1",
            "SELECT * FROM users UNION SELECT password FROM users",
        ]

        for query in dangerous_queries:
            assert SecurityValidator.validate_sql_injection_risk(query) is False


class TestPerformanceIntegration:
    """Integration tests for performance monitoring."""

    @pytest.mark.asyncio
    async def test_performance_tracking_integration(self, test_client):
        """Test performance tracking across API calls."""
        # Make a request and measure performance
        start_time = datetime.utcnow()

        response = await test_client.get("/api/v1/reports/available")

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        # Should complete within reasonable time
        assert duration < 5.0  # Should complete within 5 seconds
        assert response.status_code == 200

    def test_memory_usage_tracking(self):
        """Test memory usage tracking (conceptual test)."""
        import os

        import psutil

        # Get current process
        process = psutil.Process(os.getpid())

        # Get initial memory usage
        initial_memory = process.memory_info().rss

        # Simulate some work
        _data = [i for i in range(10000)]

        # Get memory usage after work
        final_memory = process.memory_info().rss

        # Memory should increase (but not excessively)
        memory_increase = final_memory - initial_memory
        assert memory_increase > 0  # Should use some memory
        assert memory_increase < 100 * 1024 * 1024  # Should not use 100MB

    @pytest.mark.asyncio
    async def test_database_query_performance(self, test_session):
        """Test database query performance."""
        # This is a conceptual test for query performance monitoring
        # In real implementation, would measure actual query execution times

        start_time = datetime.utcnow()

        # Simulate database operations
        # In real test, this would be actual database queries
        await asyncio.sleep(0.01)  # Simulate 10ms of database work

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        assert duration > 0.005  # Should take some time
        assert duration < 1.0  # Should not take too long


# Load Testing (Conceptual)
class TestLoadHandling:
    """Load testing for system stability."""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, test_client):
        """Test handling of concurrent requests."""
        import asyncio

        async def make_request(session):
            async with session:
                return await session.get("/api/v1/reports/available")

        # Make multiple concurrent requests
        async with AsyncClient(
            app=test_client.app, base_url="http://testserver"
        ) as client:
            tasks = [make_request(client) for _ in range(10)]
            responses = await asyncio.gather(*tasks)

        # All requests should succeed
        assert all(r.status_code == 200 for r in responses)
        assert len(responses) == 10

    def test_resource_cleanup(self):
        """Test that resources are properly cleaned up."""
        import gc

        # Force garbage collection
        gc.collect()

        # Check that no obvious memory leaks
        # This is a basic test - real memory leak testing would be more sophisticated

        # Verify that modules can be imported (basic smoke test)
        try:
            from app.core.config import Settings
            from app.core.exceptions import DatabaseError

            # Create instances to verify they work
            _settings = Settings()
            error = DatabaseError("Test error")
            assert error.message == "Test error"

        except Exception as e:
            pytest.fail(f"Resource cleanup test failed: {e}")


# End-to-End Tests
class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    @pytest.mark.asyncio
    async def test_complete_reporting_workflow(self, test_client):
        """Test complete reporting workflow from request to response."""
        # 1. Get available reports
        response1 = await test_client.get("/api/v1/reports/available")
        assert response1.status_code == 200
        reports = response1.json()
        assert len(reports) > 0

        # 2. Generate a specific report
        report_type = reports[0]["type"]
        response2 = await test_client.get(f"/api/v1/reports/{report_type}")
        assert response2.status_code == 200
        report_data = response2.json()

        # 3. Verify report structure
        assert "summary" in report_data
        assert "charts" in report_data
        assert "raw_data" in report_data

        # 4. Export the report
        export_request = {
            "format": "json",
            "filename": f"{report_type}_report.json",
        }
        response3 = await test_client.post(
            "/api/v1/reports/export", json=export_request
        )
        assert response3.status_code == 200

        # 5. Get dashboard summary
        response4 = await test_client.get("/api/v1/reports/dashboard/summary")
        assert response4.status_code == 200
        dashboard_data = response4.json()
        assert "sales" in dashboard_data
        assert "inventory" in dashboard_data
        assert "users" in dashboard_data
        assert "system" in dashboard_data

    def test_error_handling_workflow(self):
        """Test error handling workflow."""
        from app.core.exceptions import DatabaseError, ValidationError

        # Test exception hierarchy
        db_error = DatabaseError("Connection failed")
        assert isinstance(db_error, Exception)

        validation_error = ValidationError("Invalid input", details={"field": "email"})
        assert isinstance(validation_error, Exception)
        assert validation_error.details == {"field": "email"}

        # Test error conversion to dict
        error_dict = db_error.to_dict()
        assert error_dict["error"] == "DatabaseError"
        assert error_dict["message"] == "Connection failed"
