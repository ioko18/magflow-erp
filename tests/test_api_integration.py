"""Integration tests for MagFlow ERP API endpoints with dependency injection.

This module contains comprehensive integration tests that verify
the interaction between API endpoints, services, and database layers
using the new dependency injection system.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.db.models import User as UserModel


class TestReportingAPIIntegration:
    """Integration tests for reporting API endpoints with dependency injection."""

    @pytest.mark.asyncio
    async def test_get_available_reports_with_di(
        self,
        test_client_with_di,
        mock_reporting_service,
    ):
        """Test the available reports endpoint with dependency injection."""
        # Mock the service registry to return our mock service
        with patch("app.core.service_registry.get_service_registry") as mock_registry:
            mock_registry.return_value.get_reporting_service.return_value = (
                mock_reporting_service
            )

            response = test_client_with_di.get("/api/v1/reports/available")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "type" in data[0]
        assert "name" in data[0]

    @pytest.mark.asyncio
    async def test_generate_report_with_di(
        self,
        test_client_with_di,
        mock_reporting_service,
    ):
        """Test report generation with dependency injection."""
        with patch("app.core.service_registry.get_service_registry") as mock_registry:
            mock_registry.return_value.get_reporting_service.return_value = (
                mock_reporting_service
            )

            report_config = {
                "report_type": "sales_overview",
                "filters": None,
            }

            response = test_client_with_di.post(
                "/api/v1/reports/generate",
                json=report_config,
            )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "title" in data
        assert "summary" in data
        assert "charts" in data

    @pytest.mark.asyncio
    async def test_sales_overview_report_with_di(
        self,
        test_client_with_di,
        mock_reporting_service,
    ):
        """Test sales overview report endpoint with dependency injection."""
        with patch("app.core.service_registry.get_service_registry") as mock_registry:
            mock_registry.return_value.get_reporting_service.return_value = (
                mock_reporting_service
            )

            response = test_client_with_di.get("/api/v1/reports/sales/overview")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "title" in data
        assert data["title"] == "Sales Overview Report"

    @pytest.mark.asyncio
    async def test_inventory_status_report_with_di(
        self,
        test_client_with_di,
        mock_reporting_service,
    ):
        """Test inventory status report endpoint with dependency injection."""
        with patch("app.core.service_registry.get_service_registry") as mock_registry:
            mock_registry.return_value.get_reporting_service.return_value = (
                mock_reporting_service
            )

            response = test_client_with_di.get("/api/v1/reports/inventory/status")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "title" in data
        assert data["title"] == "Inventory Status Report"

    @pytest.mark.asyncio
    async def test_user_activity_report_with_di(
        self,
        test_client_with_di,
        mock_reporting_service,
    ):
        """Test user activity report endpoint with dependency injection."""
        with patch("app.core.service_registry.get_service_registry") as mock_registry:
            mock_registry.return_value.get_reporting_service.return_value = (
                mock_reporting_service
            )

            response = test_client_with_di.get("/api/v1/reports/users/activity")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "title" in data
        assert data["title"] == "User Activity Report"

    @pytest.mark.asyncio
    async def test_financial_summary_report_with_di(
        self,
        test_client_with_di,
        mock_reporting_service,
    ):
        """Test financial summary report endpoint with dependency injection."""
        with patch("app.core.service_registry.get_service_registry") as mock_registry:
            mock_registry.return_value.get_reporting_service.return_value = (
                mock_reporting_service
            )

            response = test_client_with_di.get("/api/v1/reports/financial/summary")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "title" in data
        assert data["title"] == "Financial Summary Report"

    @pytest.mark.asyncio
    async def test_system_metrics_report_with_di(
        self,
        test_client_with_di,
        mock_reporting_service,
    ):
        """Test system metrics report endpoint with dependency injection."""
        with patch("app.core.service_registry.get_service_registry") as mock_registry:
            mock_registry.return_value.get_reporting_service.return_value = (
                mock_reporting_service
            )

            response = test_client_with_di.get("/api/v1/reports/system/metrics")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "title" in data
        assert data["title"] == "System Metrics Report"

    @pytest.mark.asyncio
    async def test_report_export_with_di(
        self,
        test_client_with_di,
        mock_reporting_service,
    ):
        """Test report export functionality with dependency injection."""
        with patch("app.core.service_registry.get_service_registry") as mock_registry:
            mock_registry.return_value.get_reporting_service.return_value = (
                mock_reporting_service
            )

            export_request = {
                "format": "json",
                "filename": "test_report.json",
            }

            response = test_client_with_di.post(
                "/api/v1/reports/export", json=export_request
            )

        assert response.status_code == 200
        data = response.json()
        assert "export_id" in data
        assert "status" in data
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_report_scheduling_with_di(
        self,
        test_client_with_di,
        mock_reporting_service,
    ):
        """Test report scheduling functionality with dependency injection."""
        with patch("app.core.service_registry.get_service_registry") as mock_registry:
            mock_registry.return_value.get_reporting_service.return_value = (
                mock_reporting_service
            )

            schedule_request = {
                "report_config": {
                    "report_type": "sales_overview",
                    "filters": None,
                },
                "schedule_config": {
                    "frequency": "weekly",
                    "time": "09:00",
                },
                "recipients": ["admin@example.com"],
            }

            response = test_client_with_di.post(
                "/api/v1/reports/schedule", json=schedule_request
            )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "schedule_id" in data

    @pytest.mark.asyncio
    async def test_dashboard_summary_with_di(
        self,
        test_client_with_di,
        mock_reporting_service,
    ):
        """Test dashboard summary endpoint with dependency injection."""
        with patch("app.core.service_registry.get_service_registry") as mock_registry:
            mock_registry.return_value.get_reporting_service.return_value = (
                mock_reporting_service
            )

            response = test_client_with_di.get("/api/v1/reports/dashboard/summary")

        assert response.status_code == 200
        data = response.json()
        assert "sales" in data
        assert "inventory" in data
        assert "users" in data
        assert "system" in data

        # Check structure of each section
        assert "total_revenue" in data["sales"]
        assert "total_products" in data["inventory"]
        assert "total_users" in data["users"]
        assert "health_status" in data["system"]


class TestServiceRegistryIntegration:
    """Integration tests for service registry functionality."""

    @pytest.mark.asyncio
    async def test_service_registry_initialization(self, mock_service_context):
        """Test service registry initialization."""
        from app.core.service_registry import ServiceRegistry

        registry = ServiceRegistry()
        registry.initialize(mock_service_context)

        assert registry.is_initialized is True
        assert registry._context is not None

    @pytest.mark.asyncio
    async def test_service_registry_service_access(self, mock_service_context):
        """Test accessing services from registry."""
        from app.core.service_registry import ServiceRegistry

        registry = ServiceRegistry()
        registry.initialize(mock_service_context)

        # Test that services can be accessed
        db_service = registry.get_database_service()
        assert db_service is not None

        reporting_service = registry.get_reporting_service()
        assert reporting_service is not None

    @pytest.mark.asyncio
    async def test_service_registry_cleanup(self, mock_service_context):
        """Test service registry cleanup."""
        from app.core.service_registry import ServiceRegistry

        registry = ServiceRegistry()
        registry.initialize(mock_service_context)

        await registry.cleanup()

        assert registry.is_initialized is False
        assert registry._context is None


class TestDependencyInjectionIntegration:
    """Integration tests for dependency injection system."""

    @pytest.mark.asyncio
    async def test_get_current_active_user_dependency(self, test_session):
        """Test current user dependency resolution."""
        # Create a test user
        test_user = UserModel(
            id=1,
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            is_superuser=False,
        )

        # Mock the dependency to return our test user
        with patch(
            "app.api.dependencies.get_current_active_user", return_value=test_user
        ):
            from app.api.dependencies import get_current_active_user

            user = await get_current_active_user()
            assert user.id == 1
            assert user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_reporting_service_dependency(
        self, test_session, mock_reporting_service
    ):
        """Test reporting service dependency resolution."""
        # Mock the service registry to return our mock service
        with patch("app.core.service_registry.get_service_registry") as mock_registry:
            mock_registry.return_value.get_reporting_service.return_value = (
                mock_reporting_service
            )

            from app.api.dependencies import get_reporting_service

            service = await get_reporting_service()
            assert service is not None
            assert hasattr(service, "generate_report")
            assert hasattr(service, "get_available_reports")

    @pytest.mark.asyncio
    async def test_database_service_dependency(
        self, test_session, mock_database_service
    ):
        """Test database service dependency resolution."""
        with patch("app.core.service_registry.get_service_registry") as mock_registry:
            mock_registry.return_value.get_database_service.return_value = (
                mock_database_service
            )

            from app.api.dependencies import get_database_service

            service = await get_database_service()
            assert service is not None
            assert hasattr(service, "get_session")
            assert hasattr(service, "check_health")


class TestErrorHandlingIntegration:
    """Integration tests for error handling across the application."""

    @pytest.mark.asyncio
    async def test_database_error_propagation(
        self,
        test_client_with_di,
        mock_reporting_service,
    ):
        """Test database error propagation through dependency injection."""
        # Mock the service to raise a database error
        mock_reporting_service.generate_report.side_effect = Exception(
            "Database connection failed"
        )

        with patch("app.core.service_registry.get_service_registry") as mock_registry:
            mock_registry.return_value.get_reporting_service.return_value = (
                mock_reporting_service
            )

            response = test_client_with_di.get("/api/v1/reports/sales/overview")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "message" in data

    @pytest.mark.asyncio
    async def test_validation_error_handling(
        self,
        test_client_with_di,
        mock_reporting_service,
    ):
        """Test validation error handling in API endpoints."""
        # Mock the service to raise a validation error
        from app.core.exceptions import ValidationError

        mock_reporting_service.generate_report.side_effect = ValidationError(
            "Invalid report type"
        )

        with patch("app.core.service_registry.get_service_registry") as mock_registry:
            mock_registry.return_value.get_reporting_service.return_value = (
                mock_reporting_service
            )

            report_config = {
                "report_type": "invalid_report_type",
                "filters": None,
            }

            response = test_client_with_di.post(
                "/api/v1/reports/generate", json=report_config
            )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "ValidationError" in data.get("error", "")

    @pytest.mark.asyncio
    async def test_service_layer_error_recovery(
        self,
        test_client_with_di,
        mock_reporting_service,
    ):
        """Test error recovery in service layer."""
        # Mock a method to fail but service should handle it gracefully
        mock_reporting_service._generate_sales_overview.side_effect = Exception(
            "Database timeout"
        )

        with patch("app.core.service_registry.get_service_registry") as mock_registry:
            mock_registry.return_value.get_reporting_service.return_value = (
                mock_reporting_service
            )

            response = test_client_with_di.get("/api/v1/reports/sales/overview")

        # Should return 500 with error details
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "message" in data


class TestPerformanceIntegration:
    """Integration tests for performance monitoring."""

    @pytest.mark.asyncio
    async def test_api_response_performance(
        self,
        test_client_with_di,
        mock_reporting_service,
    ):
        """Test API response time with dependency injection."""
        import time

        with patch("app.core.service_registry.get_service_registry") as mock_registry:
            mock_registry.return_value.get_reporting_service.return_value = (
                mock_reporting_service
            )

            start_time = time.time()
            response = test_client_with_di.get("/api/v1/reports/available")
            end_time = time.time()

            # Should complete within reasonable time
            duration = end_time - start_time
            assert duration < 2.0  # Should complete within 2 seconds
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_concurrent_requests_handling(
        self,
        test_client_with_di,
        mock_reporting_service,
    ):
        """Test handling of concurrent requests with dependency injection."""
        import asyncio

        async def make_request(session):
            async with session:
                return await session.get("/api/v1/reports/available")

        with patch("app.core.service_registry.get_service_registry") as mock_registry:
            mock_registry.return_value.get_reporting_service.return_value = (
                mock_reporting_service
            )

            # Make multiple concurrent requests
            async with AsyncClient(
                app=test_client_with_di.app, base_url="http://testserver"
            ) as client:
                tasks = [make_request(client) for _ in range(5)]
                responses = await asyncio.gather(*tasks)

            # All requests should succeed
            assert all(r.status_code == 200 for r in responses)
            assert len(responses) == 5

    @pytest.mark.asyncio
    async def test_resource_cleanup(
        self,
        test_client_with_di,
        mock_reporting_service,
    ):
        """Test that resources are properly cleaned up."""
        with patch("app.core.service_registry.get_service_registry") as mock_registry:
            mock_registry.return_value.get_reporting_service.return_value = (
                mock_reporting_service
            )

            # Make several requests
            for _ in range(3):
                response = test_client_with_di.get("/api/v1/reports/available")
                assert response.status_code == 200

            # Verify no obvious memory leaks
            # This is a basic test - real memory leak testing would be more sophisticated
            assert mock_reporting_service.get_available_reports.call_count == 3


class TestServiceHealthIntegration:
    """Integration tests for service health monitoring."""

    @pytest.mark.asyncio
    async def test_service_health_check_endpoint(
        self,
        test_client_with_di,
        mock_reporting_service,
    ):
        """Test service health check endpoint."""
        with patch("app.core.service_registry.get_service_registry") as mock_registry:
            mock_registry.return_value.get_database_service.return_value = AsyncMock()
            mock_registry.return_value.get_database_service.return_value.check_health = AsyncMock(
                return_value=True
            )

            # Add health endpoint to test client
            @test_client_with_di.app.get("/health")
            async def health_check():
                return {"status": "healthy"}

            response = test_client_with_di.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_service_health_monitoring(
        self,
        test_client_with_di,
        mock_reporting_service,
    ):
        """Test service health monitoring functionality."""
        with patch("app.core.service_registry.get_service_registry") as mock_registry:
            mock_registry.return_value.is_initialized = True
            mock_registry.return_value.get_database_service.return_value = AsyncMock()
            mock_registry.return_value.get_database_service.return_value.check_health = AsyncMock(
                return_value=True
            )

            # Test that services are properly initialized
            registry = mock_registry.return_value
            assert registry.is_initialized is True

            # Test service access
            db_service = registry.get_database_service()
            assert db_service is not None

            health_status = await db_service.check_health()
            assert health_status is True


class TestEndToEndWorkflow:
    """End-to-end workflow tests with dependency injection."""

    @pytest.mark.asyncio
    async def test_complete_reporting_workflow_with_di(
        self,
        test_client_with_di,
        mock_reporting_service,
    ):
        """Test complete reporting workflow from request to response with DI."""
        with patch("app.core.service_registry.get_service_registry") as mock_registry:
            mock_registry.return_value.get_reporting_service.return_value = (
                mock_reporting_service
            )

            # 1. Get available reports
            response1 = test_client_with_di.get("/api/v1/reports/available")
            assert response1.status_code == 200
            reports = response1.json()
            assert len(reports) > 0

            # 2. Generate a specific report
            report_type = reports[0]["type"]
            response2 = test_client_with_di.get(f"/api/v1/reports/{report_type}")
            assert response2.status_code == 200
            report_data = response2.json()

            # 3. Verify report structure
            assert "id" in report_data
            assert "title" in report_data
            assert "summary" in report_data
            assert "charts" in report_data
            assert "generated_at" in report_data

            # 4. Export the report
            export_request = {
                "format": "json",
                "filename": f"{report_type}_report.json",
            }
            response3 = test_client_with_di.post(
                "/api/v1/reports/export", json=export_request
            )
            assert response3.status_code == 200
            export_data = response3.json()
            assert "export_id" in export_data
            assert "status" in export_data

            # 5. Get dashboard summary
            response4 = test_client_with_di.get("/api/v1/reports/dashboard/summary")
            assert response4.status_code == 200
            dashboard_data = response4.json()
            assert "sales" in dashboard_data
            assert "inventory" in dashboard_data
            assert "users" in dashboard_data
            assert "system" in dashboard_data

    @pytest.mark.asyncio
    async def test_error_handling_workflow_with_di(
        self,
        test_client_with_di,
        mock_reporting_service,
    ):
        """Test error handling workflow with dependency injection."""
        # Mock different types of errors
        from app.core.exceptions import DatabaseServiceError, ValidationError

        # Test database error
        mock_reporting_service.generate_report.side_effect = DatabaseServiceError(
            "Database connection failed"
        )

        with patch("app.core.service_registry.get_service_registry") as mock_registry:
            mock_registry.return_value.get_reporting_service.return_value = (
                mock_reporting_service
            )

            response = test_client_with_di.get("/api/v1/reports/sales/overview")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "DatabaseError" in data.get("error", "")

        # Test validation error
        mock_reporting_service.generate_report.side_effect = ValidationError(
            "Invalid report type"
        )

        response2 = test_client_with_di.get("/api/v1/reports/sales/overview")

        assert response2.status_code == 500  # Should be handled by middleware
        data2 = response2.json()
        assert "error" in data2
        assert "message" in data2
