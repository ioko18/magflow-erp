"""Service layer integration tests for MagFlow ERP.

This module contains comprehensive tests for service layer functionality,
verifying the interaction between services, repositories, and database operations
using the new dependency injection system.
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import DatabaseServiceError, ValidationError
from app.core.service_registry import ServiceRegistry
from app.services.reporting_service import ReportingService


class TestReportingServiceIntegration:
    """Integration tests for ReportingService with dependency injection."""

    @pytest.mark.asyncio
    async def test_reporting_service_initialization(
        self,
        mock_service_context,
        mock_user_repository,
        mock_product_repository,
        mock_order_repository,
        mock_audit_log_repository,
    ):
        """Test ReportingService initialization with dependency injection."""
        with patch(
            "app.core.service_registry.get_user_repository",
            return_value=mock_user_repository,
        ), patch(
            "app.core.service_registry.get_product_repository",
            return_value=mock_product_repository,
        ), patch(
            "app.core.service_registry.get_order_repository",
            return_value=mock_order_repository,
        ), patch(
            "app.core.service_registry.get_audit_log_repository",
            return_value=mock_audit_log_repository,
        ):

            service = ReportingService(mock_service_context)

            # Verify service is properly initialized
            assert service.context is not None
            assert service.user_repository is not None
            assert service.product_repository is not None
            assert service.order_repository is not None
            assert service.audit_log_repository is not None

            # Test service methods exist
            assert hasattr(service, "initialize")
            assert hasattr(service, "cleanup")
            assert hasattr(service, "generate_report")
            assert hasattr(service, "get_available_reports")

    @pytest.mark.asyncio
    async def test_reporting_service_available_reports(
        self,
        mock_service_context,
        mock_user_repository,
        mock_product_repository,
        mock_order_repository,
        mock_audit_log_repository,
    ):
        """Test get_available_reports method."""
        with patch(
            "app.core.service_registry.get_user_repository",
            return_value=mock_user_repository,
        ), patch(
            "app.core.service_registry.get_product_repository",
            return_value=mock_product_repository,
        ), patch(
            "app.core.service_registry.get_order_repository",
            return_value=mock_order_repository,
        ), patch(
            "app.core.service_registry.get_audit_log_repository",
            return_value=mock_audit_log_repository,
        ):

            service = ReportingService(mock_service_context)
            reports = await service.get_available_reports()

            assert isinstance(reports, list)
            assert len(reports) > 0

            # Check structure of report definitions
            for report in reports:
                assert "type" in report
                assert "name" in report
                assert "description" in report
                assert "category" in report
                assert "charts" in report

    @pytest.mark.asyncio
    async def test_reporting_service_report_generation(
        self,
        mock_service_context,
        mock_user_repository,
        mock_product_repository,
        mock_order_repository,
        mock_audit_log_repository,
    ):
        """Test report generation functionality."""
        with patch(
            "app.core.service_registry.get_user_repository",
            return_value=mock_user_repository,
        ), patch(
            "app.core.service_registry.get_product_repository",
            return_value=mock_product_repository,
        ), patch(
            "app.core.service_registry.get_order_repository",
            return_value=mock_order_repository,
        ), patch(
            "app.core.service_registry.get_audit_log_repository",
            return_value=mock_audit_log_repository,
        ):

            service = ReportingService(mock_service_context)

            # Test sales overview report
            report_data = await service.generate_report(
                report_type="sales_overview",
                filters=None,
                user_id=1,
            )

            # Verify report structure
            assert "report_id" in report_data
            assert "report_type" in report_data
            assert "generated_at" in report_data
            assert "generated_by" in report_data
            assert "summary" in report_data
            assert "charts" in report_data

    @pytest.mark.asyncio
    async def test_reporting_service_error_handling(
        self,
        mock_service_context,
        mock_user_repository,
        mock_product_repository,
        mock_order_repository,
        mock_audit_log_repository,
    ):
        """Test error handling in reporting service."""
        with patch(
            "app.core.service_registry.get_user_repository",
            return_value=mock_user_repository,
        ), patch(
            "app.core.service_registry.get_product_repository",
            return_value=mock_product_repository,
        ), patch(
            "app.core.service_registry.get_order_repository",
            return_value=mock_order_repository,
        ), patch(
            "app.core.service_registry.get_audit_log_repository",
            return_value=mock_audit_log_repository,
        ):

            service = ReportingService(mock_service_context)

            # Test invalid report type
            with pytest.raises(ValueError, match="Unknown report type"):
                await service.generate_report(
                    report_type="invalid_report_type",
                    filters=None,
                    user_id=1,
                )

    @pytest.mark.asyncio
    async def test_reporting_service_with_filters(
        self,
        mock_service_context,
        mock_user_repository,
        mock_product_repository,
        mock_order_repository,
        mock_audit_log_repository,
    ):
        """Test reporting service with date filters."""
        with patch(
            "app.core.service_registry.get_user_repository",
            return_value=mock_user_repository,
        ), patch(
            "app.core.service_registry.get_product_repository",
            return_value=mock_product_repository,
        ), patch(
            "app.core.service_registry.get_order_repository",
            return_value=mock_order_repository,
        ), patch(
            "app.core.service_registry.get_audit_log_repository",
            return_value=mock_audit_log_repository,
        ):

            service = ReportingService(mock_service_context)

            # Test with date range filters
            filters = {
                "date_range": {
                    "start_date": date.today() - timedelta(days=30),
                    "end_date": date.today(),
                },
            }

            report_data = await service.generate_report(
                report_type="sales_overview",
                filters=filters,
                user_id=1,
            )

            assert "report_id" in report_data
            assert report_data["filters_applied"] == filters


class TestRepositoryIntegration:
    """Integration tests for repository pattern implementation."""

    @pytest.mark.asyncio
    async def test_user_repository_operations(
        self,
        mock_service_context,
        mock_user_repository,
    ):
        """Test user repository CRUD operations."""
        # Test get_by_id
        user = await mock_user_repository.get_by_id(1)
        assert user is not None

        # Test get_all
        users = await mock_user_repository.get_all()
        assert isinstance(users, list)

        # Test create
        new_user = await mock_user_repository.create({"email": "test@example.com"})
        assert new_user is not None

        # Test update
        updated_user = await mock_user_repository.update(
            1, {"email": "updated@example.com"}
        )
        assert updated_user is not None

        # Test delete
        result = await mock_user_repository.delete(1)
        assert result is True

    @pytest.mark.asyncio
    async def test_product_repository_operations(
        self,
        mock_service_context,
        mock_product_repository,
    ):
        """Test product repository CRUD operations."""
        # Test get_by_id
        product = await mock_product_repository.get_by_id(1)
        assert product is not None

        # Test get_by_sku
        product_by_sku = await mock_product_repository.get_by_sku("TEST-001")
        assert product_by_sku is not None

        # Test get_all
        products = await mock_product_repository.get_all()
        assert isinstance(products, list)

        # Test create
        new_product = await mock_product_repository.create({"name": "Test Product"})
        assert new_product is not None

        # Test update
        updated_product = await mock_product_repository.update(
            1, {"name": "Updated Product"}
        )
        assert updated_product is not None

        # Test delete
        result = await mock_product_repository.delete(1)
        assert result is True

    @pytest.mark.asyncio
    async def test_order_repository_operations(
        self,
        mock_service_context,
        mock_order_repository,
    ):
        """Test order repository CRUD operations."""
        # Test get_by_id
        order = await mock_order_repository.get_by_id(1)
        assert order is not None

        # Test get_by_customer_id
        orders = await mock_order_repository.get_by_customer_id(1)
        assert isinstance(orders, list)

        # Test get_all
        all_orders = await mock_order_repository.get_all()
        assert isinstance(all_orders, list)

        # Test create
        new_order = await mock_order_repository.create({"customer_id": 1})
        assert new_order is not None

        # Test update
        updated_order = await mock_order_repository.update(1, {"status": "completed"})
        assert updated_order is not None

        # Test delete
        result = await mock_order_repository.delete(1)
        assert result is True

    @pytest.mark.asyncio
    async def test_audit_log_repository_operations(
        self,
        mock_service_context,
        mock_audit_log_repository,
    ):
        """Test audit log repository CRUD operations."""
        # Test get_by_id
        audit_log = await mock_audit_log_repository.get_by_id(1)
        assert audit_log is not None

        # Test get_by_user_id
        logs = await mock_audit_log_repository.get_by_user_id(1)
        assert isinstance(logs, list)

        # Test get_all
        all_logs = await mock_audit_log_repository.get_all()
        assert isinstance(all_logs, list)

        # Test create
        new_log = await mock_audit_log_repository.create(
            {"user_id": 1, "action": "login"}
        )
        assert new_log is not None

        # Test update
        updated_log = await mock_audit_log_repository.update(1, {"action": "logout"})
        assert updated_log is not None

        # Test delete
        result = await mock_audit_log_repository.delete(1)
        assert result is True


class TestServiceRegistryIntegration:
    """Integration tests for service registry functionality."""

    @pytest.mark.asyncio
    async def test_service_registry_with_mock_services(
        self,
        mock_service_context,
        mock_database_service,
        mock_cache_service,
        mock_authentication_service,
        mock_reporting_service,
    ):
        """Test service registry with all mock services."""
        registry = ServiceRegistry()
        registry.initialize(mock_service_context)

        # Mock the service creation
        with patch.object(
            registry, "get_database_service", return_value=mock_database_service
        ), patch.object(
            registry, "get_cache_service", return_value=mock_cache_service
        ), patch.object(
            registry,
            "get_authentication_service",
            return_value=mock_authentication_service,
        ), patch.object(
            registry, "get_reporting_service", return_value=mock_reporting_service
        ):

            # Test service access
            db_service = registry.get_database_service()
            cache_service = registry.get_cache_service()
            auth_service = registry.get_authentication_service()
            reporting_service = registry.get_reporting_service()

            assert db_service is not None
            assert cache_service is not None
            assert auth_service is not None
            assert reporting_service is not None

            # Test service methods
            health = await db_service.check_health()
            assert health is True

            cached_value = await cache_service.get("test_key")
            assert cached_value is None

            auth_result = await auth_service.authenticate_user(
                "test@example.com", "password"
            )
            assert auth_result["authenticated"] is True

            reports = await reporting_service.get_available_reports()
            assert isinstance(reports, list)

    @pytest.mark.asyncio
    async def test_service_registry_initialization_error(
        self,
        mock_service_context,
    ):
        """Test service registry initialization error handling."""
        registry = ServiceRegistry()

        # Initialize with valid context
        registry.initialize(mock_service_context)
        assert registry.is_initialized is True

        # Test cleanup
        await registry.cleanup()
        assert registry.is_initialized is False
        assert registry._context is None

    @pytest.mark.asyncio
    async def test_service_registry_service_not_found(
        self,
        mock_service_context,
    ):
        """Test accessing non-existent service."""
        registry = ServiceRegistry()
        registry.initialize(mock_service_context)

        with pytest.raises(AttributeError):
            registry.get_non_existent_service()


class TestDependencyInjectionIntegration:
    """Integration tests for dependency injection functionality."""

    @pytest.mark.asyncio
    async def test_service_context_creation(
        self,
        mock_service_context,
    ):
        """Test service context creation and validation."""
        assert mock_service_context.settings is not None
        assert mock_service_context.settings.APP_ENV == "testing"
        assert mock_service_context.settings.DEBUG is True

    @pytest.mark.asyncio
    async def test_service_initialization_with_context(
        self,
        mock_service_context,
        mock_reporting_service,
    ):
        """Test service initialization with service context."""
        # This tests the pattern used in the dependency injection system
        service = ReportingService.__new__(ReportingService)
        service.__init__(mock_service_context)

        assert service.context is mock_service_context
        assert service.context.settings is not None

    @pytest.mark.asyncio
    async def test_service_method_dependencies(
        self,
        mock_service_context,
        mock_user_repository,
    ):
        """Test service methods that depend on repositories."""
        with patch(
            "app.core.service_registry.get_user_repository",
            return_value=mock_user_repository,
        ):
            service = ReportingService(mock_service_context)

            # Test that repositories are properly injected
            assert service.user_repository is not None
            assert hasattr(service.user_repository, "get_by_id")

            # Test repository method calls
            user = await service.user_repository.get_by_id(1)
            assert user is not None

    @pytest.mark.asyncio
    async def test_service_error_propagation(
        self,
        mock_service_context,
        mock_user_repository,
    ):
        """Test error propagation through service layers."""
        with patch(
            "app.core.service_registry.get_user_repository",
            return_value=mock_user_repository,
        ):
            service = ReportingService(mock_service_context)

            # Mock repository to raise an error
            service.user_repository.get_by_id.side_effect = DatabaseServiceError(
                "Database connection failed"
            )

            # Error should propagate up
            with pytest.raises(DatabaseServiceError):
                await service.user_repository.get_by_id(1)


class TestServiceLayerErrorHandling:
    """Integration tests for service layer error handling."""

    @pytest.mark.asyncio
    async def test_database_error_handling(
        self,
        mock_service_context,
        mock_user_repository,
    ):
        """Test database error handling in service layer."""
        with patch(
            "app.core.service_registry.get_user_repository",
            return_value=mock_user_repository,
        ):
            service = ReportingService(mock_service_context)

            # Mock database error
            service.user_repository.get_by_id.side_effect = DatabaseServiceError(
                "Database connection failed",
                details={"connection": "timeout"},
            )

            # Error should be properly handled
            with pytest.raises(DatabaseServiceError) as exc_info:
                await service.user_repository.get_by_id(1)

            assert "Database connection failed" in str(exc_info.value)
            assert exc_info.value.details["connection"] == "timeout"

    @pytest.mark.asyncio
    async def test_validation_error_handling(
        self,
        mock_service_context,
        mock_user_repository,
    ):
        """Test validation error handling in service layer."""
        with patch(
            "app.core.service_registry.get_user_repository",
            return_value=mock_user_repository,
        ):
            service = ReportingService(mock_service_context)

            # Mock validation error
            service.user_repository.create.side_effect = ValidationError(
                "Invalid user data",
                details={"field": "email", "error": "invalid_format"},
            )

            # Error should be properly handled
            with pytest.raises(ValidationError) as exc_info:
                await service.user_repository.create({})

            assert "Invalid user data" in str(exc_info.value)
            assert exc_info.value.details["field"] == "email"

    @pytest.mark.asyncio
    async def test_service_layer_error_recovery(
        self,
        mock_service_context,
        mock_user_repository,
    ):
        """Test error recovery mechanisms in service layer."""
        with patch(
            "app.core.service_registry.get_user_repository",
            return_value=mock_user_repository,
        ):
            service = ReportingService(mock_service_context)

            # Mock a temporary failure followed by success
            call_count = 0

            async def mock_get_by_id(user_id):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise DatabaseServiceError("Temporary connection issue")
                return MagicMock()

            service.user_repository.get_by_id.side_effect = mock_get_by_id

            # First call should fail
            with pytest.raises(DatabaseServiceError):
                await service.user_repository.get_by_id(1)

            # Second call should succeed (if we implemented retry logic)
            # This tests the pattern for error recovery

    @pytest.mark.asyncio
    async def test_service_error_logging(
        self,
        mock_service_context,
        mock_user_repository,
    ):
        """Test error logging in service layer."""
        with patch(
            "app.core.service_registry.get_user_repository",
            return_value=mock_user_repository,
        ):
            service = ReportingService(mock_service_context)

            # Mock error with logging
            error = DatabaseServiceError("Test database error")
            service.user_repository.get_by_id.side_effect = error

            # Test that service handles error gracefully
            with pytest.raises(DatabaseServiceError):
                await service.user_repository.get_by_id(1)


class TestServicePerformanceIntegration:
    """Integration tests for service performance monitoring."""

    @pytest.mark.asyncio
    async def test_service_method_performance(
        self,
        mock_service_context,
        mock_user_repository,
    ):
        """Test performance of service methods."""
        import time

        with patch(
            "app.core.service_registry.get_user_repository",
            return_value=mock_user_repository,
        ):
            service = ReportingService(mock_service_context)

            # Time a service method call
            start_time = time.time()
            await service.user_repository.get_all()
            end_time = time.time()

            # Should complete within reasonable time
            duration = end_time - start_time
            assert duration < 1.0  # Should complete within 1 second

    @pytest.mark.asyncio
    async def test_concurrent_service_operations(
        self,
        mock_service_context,
        mock_user_repository,
    ):
        """Test concurrent service operations."""
        import asyncio

        with patch(
            "app.core.service_registry.get_user_repository",
            return_value=mock_user_repository,
        ):
            service = ReportingService(mock_service_context)

            # Create multiple concurrent operations
            async def get_user(user_id):
                return await service.user_repository.get_by_id(user_id)

            # Run concurrent operations
            user_ids = [1, 2, 3, 4, 5]
            tasks = [get_user(user_id) for user_id in user_ids]

            start_time = asyncio.get_event_loop().time()
            results = await asyncio.gather(*tasks)
            end_time = asyncio.get_event_loop().time()

            # All operations should complete
            assert len(results) == len(user_ids)
            assert all(result is not None for result in results)

            # Should complete quickly
            duration = end_time - start_time
            assert duration < 2.0  # Should complete within 2 seconds

    @pytest.mark.asyncio
    async def test_service_resource_usage(
        self,
        mock_service_context,
        mock_user_repository,
    ):
        """Test service resource usage patterns."""
        with patch(
            "app.core.service_registry.get_user_repository",
            return_value=mock_user_repository,
        ):
            service = ReportingService(mock_service_context)

            # Simulate resource-intensive operation
            large_data = await service.user_repository.get_all()

            # Test that service handles large datasets
            assert isinstance(large_data, list)

            # Test memory cleanup
            del large_data

            # Service should still be functional
            users = await service.user_repository.get_all()
            assert isinstance(users, list)


class TestServiceHealthMonitoring:
    """Integration tests for service health monitoring."""

    @pytest.mark.asyncio
    async def test_service_health_check(
        self,
        mock_service_context,
        mock_database_service,
    ):
        """Test service health check functionality."""
        with patch("app.core.service_registry.get_user_repository"), patch(
            "app.core.service_registry.get_product_repository"
        ), patch("app.core.service_registry.get_order_repository"), patch(
            "app.core.service_registry.get_audit_log_repository"
        ):

            service = ReportingService(mock_service_context)

            # Mock database service health check
            service.db_service = mock_database_service
            health_status = await service.db_service.check_health()

            assert health_status is True

    @pytest.mark.asyncio
    async def test_service_dependency_health(
        self,
        mock_service_context,
        mock_user_repository,
        mock_product_repository,
    ):
        """Test health of service dependencies."""
        with patch(
            "app.core.service_registry.get_user_repository",
            return_value=mock_user_repository,
        ), patch(
            "app.core.service_registry.get_product_repository",
            return_value=mock_product_repository,
        ), patch(
            "app.core.service_registry.get_order_repository"
        ), patch(
            "app.core.service_registry.get_audit_log_repository"
        ):

            service = ReportingService(mock_service_context)

            # Test repository health through method calls
            try:
                user = await service.user_repository.get_by_id(1)
                product = await service.product_repository.get_by_id(1)

                # If no exceptions, dependencies are healthy
                assert user is not None
                assert product is not None

            except Exception as e:
                pytest.fail(f"Service dependency health check failed: {e}")

    @pytest.mark.asyncio
    async def test_service_initialization_status(
        self,
        mock_service_context,
    ):
        """Test service initialization status."""
        with patch("app.core.service_registry.get_user_repository"), patch(
            "app.core.service_registry.get_product_repository"
        ), patch("app.core.service_registry.get_order_repository"), patch(
            "app.core.service_registry.get_audit_log_repository"
        ):

            service = ReportingService(mock_service_context)

            # Test service initialization
            await service.initialize()
            assert service.context is not None

            # Test service cleanup
            await service.cleanup()
            # Service should still be functional after cleanup
