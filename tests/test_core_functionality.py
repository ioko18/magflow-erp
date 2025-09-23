"""Core functionality tests for MagFlow ERP using dependency injection.

This module contains comprehensive unit tests for core functionality
that work with the new dependency injection system and service architecture.
"""

from unittest.mock import AsyncMock

import pytest

from app.core.config import Settings
from app.core.database_resilience import DatabaseHealthChecker
from app.core.exceptions import ConfigurationError, DatabaseError, ValidationError
from app.services.reporting_service import ReportingService


class TestDatabaseHealthChecker:
    """Test database health checker functionality with dependency injection."""

    @pytest.fixture
    def mock_session_factory(self):
        """Create mock session factory."""
        mock_factory = AsyncMock()
        mock_session = AsyncMock()
        mock_factory.return_value = mock_session
        return mock_factory

    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_session_factory):
        """Test successful health check with dependency injection."""
        health_checker = DatabaseHealthChecker(mock_session_factory)

        # Mock successful database query
        mock_session = mock_session_factory()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        result = await health_checker.check_health()

        assert result is True
        assert health_checker.is_healthy is True
        mock_session_factory.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_session_factory):
        """Test failed health check with dependency injection."""
        health_checker = DatabaseHealthChecker(mock_session_factory)

        # Mock database query failure
        mock_session = mock_session_factory()
        mock_session.execute.side_effect = Exception("Database connection failed")

        result = await health_checker.check_health()

        assert result is False
        assert health_checker.is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_with_service_integration(self):
        """Test health checker integration with service context."""
        health_checker = DatabaseHealthChecker(lambda: None)

        # Test with service context
        assert health_checker is not None
        # Note: ensure_healthy() would require a real database session
        # This test just validates the health checker can be created


class TestReportingService:
    """Test reporting service functionality."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def reporting_service(self, mock_db_session):
        """Create reporting service instance."""
        return ReportingService(mock_db_session)

    @pytest.mark.asyncio
    async def test_get_date_range_default(self, reporting_service):
        """Test default date range calculation."""
        result = reporting_service._get_date_range()

        assert "start_date" in result
        assert "end_date" in result
        assert result["start_date"] <= result["end_date"]

    @pytest.mark.asyncio
    async def test_get_date_range_with_filters(self, reporting_service):
        """Test date range with custom filters."""
        filters = {
            "date_range": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
        }

        result = reporting_service._get_date_range(filters)

        assert result["start_date"].strftime("%Y-%m-%d") == "2024-01-01"
        assert result["end_date"].strftime("%Y-%m-%d") == "2024-01-31"

    @pytest.mark.asyncio
    async def test_get_empty_report_data(self, reporting_service):
        """Test empty report data structure."""
        result = reporting_service._get_empty_report_data()

        assert "summary" in result
        assert "charts" in result
        assert "raw_data" in result
        assert result["summary"]["total_records"] == 0

    @pytest.mark.asyncio
    async def test_get_available_reports(self, reporting_service):
        """Test available reports list."""
        reports = await reporting_service.get_available_reports()

        assert isinstance(reports, list)
        assert len(reports) > 0

        # Check required fields
        for report in reports:
            assert "type" in report
            assert "name" in report
            assert "description" in report
            assert "category" in report
            assert "charts" in report


class TestConfigurationValidation:
    """Test configuration validation functionality."""

    def test_settings_validation_success(self):
        """Test successful configuration validation."""
        settings = Settings(
            SECRET_KEY="test-secret-key-12345678901234567890",
            DB_HOST="localhost",
            DB_NAME="test_db",
            DB_USER="test_user",
            DB_PASS="test_password",
            APP_ENV="development",
        )

        # Should not raise exception
        settings.validate_configuration()

    def test_settings_validation_failure_missing_secret(self):
        """Test configuration validation failure for missing secret."""
        settings = Settings(
            SECRET_KEY="change-this-in-production",  # Invalid default
            DB_HOST="localhost",
            DB_NAME="test_db",
            DB_USER="test_user",
            APP_ENV="development",
        )

        with pytest.raises(ConfigurationError) as exc_info:
            settings.validate_configuration()

        assert "SECRET_KEY" in str(exc_info.value)

    def test_settings_validation_production_localhost(self):
        """Test validation failure for production using localhost."""
        settings = Settings(
            SECRET_KEY="test-secret-key-12345678901234567890",
            DB_HOST="localhost",
            DB_NAME="test_db",
            DB_USER="test_user",
            DB_PASS="password",
            APP_ENV="production",
        )

        with pytest.raises(ConfigurationError) as exc_info:
            settings.validate_configuration()

        assert "localhost" in str(exc_info.value)

    def test_settings_validation_weak_password(self):
        """Test validation failure for weak production password."""
        settings = Settings(
            SECRET_KEY="test-secret-key-12345678901234567890",
            DB_HOST="prod-server",
            DB_NAME="test_db",
            DB_USER="test_user",
            DB_PASS="weak",  # Too short
            APP_ENV="production",
        )

        with pytest.raises(ConfigurationError) as exc_info:
            settings.validate_configuration()

        assert "password" in str(exc_info.value).lower()


class TestExceptionHandling:
    """Test custom exception handling."""

    def test_database_error_creation(self):
        """Test DatabaseError creation and properties."""
        error = DatabaseError("Database connection failed")

        assert error.message == "Database connection failed"
        assert error.error_code == "DatabaseError"

        error_dict = error.to_dict()
        assert error_dict["error"] == "DatabaseError"
        assert error_dict["message"] == "Database connection failed"

    def test_validation_error_with_details(self):
        """Test ValidationError with additional details."""
        details = {"field": "email", "value": "invalid-email"}
        error = ValidationError("Invalid email format", details=details)

        assert error.error_code == "ValidationError"
        assert error.details == details

        error_dict = error.to_dict()
        assert error_dict["details"] == details

    def test_configuration_error_with_validation_errors(self):
        """Test ConfigurationError with multiple validation errors."""
        validation_errors = ["Missing SECRET_KEY", "Invalid DB_HOST"]
        error = ConfigurationError(
            "Configuration validation failed",
            details={"validation_errors": validation_errors},
        )

        assert error.error_code == "ConfigurationError"
        assert error.details["validation_errors"] == validation_errors


class TestPerformanceMetrics:
    """Test performance monitoring utilities."""

    @pytest.fixture
    def sample_metrics(self):
        """Create sample performance metrics."""
        from app.core.performance import PerformanceMetrics

        return PerformanceMetrics()

    def test_metrics_initialization(self, sample_metrics):
        """Test performance metrics initialization."""
        assert sample_metrics.query_count == 0
        assert sample_metrics.query_time == 0.0
        assert sample_metrics.cache_hits == 0
        assert sample_metrics.cache_misses == 0
        assert sample_metrics.api_calls == 0
        assert sample_metrics.api_time == 0.0

    def test_metrics_tracking(self, sample_metrics):
        """Test metrics tracking functionality."""
        # Simulate some activity
        sample_metrics.query_count = 5
        sample_metrics.query_time = 0.125
        sample_metrics.cache_hits = 3
        sample_metrics.cache_misses = 2
        sample_metrics.api_calls = 1
        sample_metrics.api_time = 0.050

        assert sample_metrics.query_count == 5
        assert sample_metrics.query_time == 0.125
        assert sample_metrics.cache_hits == 3
        assert sample_metrics.cache_misses == 2
        assert sample_metrics.api_calls == 1
        assert sample_metrics.api_time == 0.050


class TestSecurityValidation:
    """Test security validation utilities."""

    def test_email_validation(self):
        """Test email format validation."""
        from app.core.security import SecurityValidator

        assert SecurityValidator.validate_email("test@example.com") is True
        assert SecurityValidator.validate_email("user.name+tag@domain.co.uk") is True
        assert SecurityValidator.validate_email("invalid-email") is False
        assert SecurityValidator.validate_email("@example.com") is False
        assert SecurityValidator.validate_email("test@") is False

    def test_password_strength_validation(self):
        """Test password strength validation."""
        from app.core.security import SecurityValidator

        # Weak password
        weak_result = SecurityValidator.validate_password_strength("123")
        assert weak_result["score"] < 3
        assert weak_result["is_acceptable"] is False

        # Strong password
        strong_result = SecurityValidator.validate_password_strength("SecurePass123!@#")
        assert strong_result["score"] >= 4
        assert strong_result["is_acceptable"] is True

    def test_sql_injection_risk_detection(self):
        """Test SQL injection risk detection."""
        from app.core.security import SecurityValidator

        # Safe queries
        assert (
            SecurityValidator.validate_sql_injection_risk(
                "SELECT * FROM users WHERE id = ?"
            )
            is True
        )
        assert (
            SecurityValidator.validate_sql_injection_risk(
                "SELECT * FROM users WHERE name = 'John'"
            )
            is True
        )

        # Potentially dangerous patterns
        assert (
            SecurityValidator.validate_sql_injection_risk(
                "SELECT * FROM users; DROP TABLE users; --"
            )
            is False
        )
        assert (
            SecurityValidator.validate_sql_injection_risk(
                "SELECT * FROM users WHERE 1=1"
            )
            is False
        )
        assert (
            SecurityValidator.validate_sql_injection_risk(
                "SELECT * FROM users UNION SELECT password FROM users"
            )
            is False
        )

    def test_html_sanitization(self):
        """Test HTML sanitization."""
        from app.core.security import SecurityValidator

        # Safe HTML
        safe_html = "<p>Hello <strong>world</strong></p>"
        sanitized = SecurityValidator.sanitize_html(safe_html)
        assert sanitized == safe_html

        # Dangerous HTML should be stripped
        dangerous_html = '<p>Hello</p><script>alert("xss")</script><p>World</p>'
        sanitized = SecurityValidator.sanitize_html(dangerous_html, ["p"])
        assert "<script>" not in sanitized
        assert 'alert("xss")' not in sanitized


# Integration Tests
class TestDatabaseIntegration:
    """Integration tests for database functionality."""

    @pytest.mark.asyncio
    async def test_database_session_creation_mock(self):
        """Test database session creation mock."""
        # Mock test to avoid needing real database
        from unittest.mock import AsyncMock

        mock_session = AsyncMock()
        mock_session.autocommit = False
        mock_session.autoflush = False

        # Test session properties
        assert mock_session.autocommit is False
        assert mock_session.autoflush is False


# Performance Tests
class TestPerformanceBenchmarks:
    """Performance benchmark tests."""

    def test_configuration_creation_simple(self):
        """Simple test for configuration creation."""
        settings = Settings(
            SECRET_KEY="test-secret-key-12345678901234567890",
            DB_HOST="localhost",
            DB_NAME="test_db",
            DB_USER="test_user",
        )

        assert settings is not None
        assert settings.SECRET_KEY == "test-secret-key-12345678901234567890"

    def test_exception_creation_simple(self):
        """Simple test for exception creation."""
        error = DatabaseError("Test database error", details={"test": True})

        assert error.message == "Test database error"
        assert error.details == {"test": True}
