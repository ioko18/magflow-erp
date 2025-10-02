"""
Comprehensive tests for eMAG integration enhancements.

Tests all new features implemented from EMAG_INTEGRATION_RECOMMENDATIONS.md:
- Order validation
- Cancellation reasons
- Rate limiting
- Error handling
- Monitoring
- Backup service
"""

import pytest
import asyncio
from unittest.mock import AsyncMock

from app.services.order_validation import (
    validate_order_data,
    validate_order_cancellation,
    validate_bulk_order_update
)
from app.core.emag_constants import CANCELLATION_REASONS, get_cancellation_reason_text
from app.core.emag_errors import (
    EmagApiError,
    RateLimitError,
    AuthenticationError,
    ValidationError,
    retry_with_backoff
)
from app.core.emag_rate_limiter import EmagRateLimiter, TokenBucket


class TestOrderValidation:
    """Test order validation functionality."""
    
    def test_valid_order(self):
        """Test validation of a valid order."""
        valid_order = {
            "id": 12345,
            "status": 1,
            "payment_mode_id": 1,
            "products": [
                {
                    "id": 1,
                    "quantity": 2,
                    "sale_price": 99.99,
                    "status": 1
                }
            ],
            "customer": {
                "name": "John Doe",
                "phone1": "0712345678",
                "email": "john@example.com"
            }
        }
        
        errors = validate_order_data(valid_order)
        assert len(errors) == 0, f"Valid order should have no errors, got: {errors}"
    
    def test_missing_required_fields(self):
        """Test validation with missing required fields."""
        invalid_order = {"id": 12345}
        errors = validate_order_data(invalid_order)
        
        assert len(errors) > 0, "Order with missing fields should have errors"
        assert any("status" in error for error in errors)
        assert any("payment_mode_id" in error for error in errors)
        assert any("products" in error for error in errors)
    
    def test_invalid_status(self):
        """Test validation with invalid status."""
        order = {
            "id": 12345,
            "status": 99,  # Invalid status
            "payment_mode_id": 1,
            "products": [{"id": 1, "quantity": 1, "sale_price": 10, "status": 1}],
            "customer": {"name": "Test", "phone1": "123", "email": "test@test.com"}
        }
        
        errors = validate_order_data(order)
        assert any("status" in error.lower() for error in errors)
    
    def test_invalid_product(self):
        """Test validation with invalid product data."""
        order = {
            "id": 12345,
            "status": 1,
            "payment_mode_id": 1,
            "products": [
                {
                    "id": 1,
                    "quantity": -1,  # Invalid quantity
                    "sale_price": 99.99,
                    "status": 1
                }
            ],
            "customer": {"name": "Test", "phone1": "123", "email": "test@test.com"}
        }
        
        errors = validate_order_data(order)
        assert any("quantity" in error.lower() for error in errors)
    
    def test_cancellation_validation(self):
        """Test order cancellation validation."""
        # Valid cancellation
        errors = validate_order_cancellation("12345", 1)
        assert len(errors) == 0
        
        # Invalid cancellation reason
        errors = validate_order_cancellation("12345", 999)
        assert len(errors) > 0
        assert any("cancellation reason" in error.lower() for error in errors)
    
    def test_bulk_validation(self):
        """Test bulk order validation."""
        orders = [
            {"id": 1, "status": 0, "cancellation_reason": 1},
            {"id": 2, "status": 99},  # Invalid status
        ]
        
        results = validate_bulk_order_update(orders)
        assert "2" in results  # Order 2 should have errors
        assert "1" not in results  # Order 1 should be valid


class TestCancellationReasons:
    """Test cancellation reasons functionality."""
    
    def test_all_reasons_exist(self):
        """Test that all cancellation reasons are defined."""
        expected_codes = [1, 2, 3, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39]
        
        for code in expected_codes:
            assert code in CANCELLATION_REASONS, f"Cancellation reason {code} not found"
            assert isinstance(CANCELLATION_REASONS[code], str)
            assert len(CANCELLATION_REASONS[code]) > 0
    
    def test_get_reason_text(self):
        """Test getting cancellation reason text."""
        text = get_cancellation_reason_text(1)
        assert text == "Lipsă stoc"
        
        # Unknown code
        text = get_cancellation_reason_text(999)
        assert "Unknown" in text or "code: 999" in text


class TestErrorHandling:
    """Test error handling functionality."""
    
    def test_emag_api_error(self):
        """Test EmagApiError creation."""
        error = EmagApiError("Test error", code="TEST_ERROR", status_code=400)
        
        assert error.message == "Test error"
        assert error.code == "TEST_ERROR"
        assert error.status_code == 400
        assert "Test error" in str(error)
    
    def test_rate_limit_error(self):
        """Test RateLimitError creation."""
        error = RateLimitError(remaining_seconds=60)
        
        assert error.remaining_seconds == 60
        assert error.status_code == 429
        assert "60" in error.message
    
    def test_authentication_error(self):
        """Test AuthenticationError creation."""
        error = AuthenticationError("Invalid credentials")
        
        assert error.status_code == 401
        assert "Invalid credentials" in error.message
    
    def test_validation_error(self):
        """Test ValidationError creation."""
        validation_errors = ["Field 1 is required", "Field 2 is invalid"]
        error = ValidationError("Validation failed", validation_errors=validation_errors)
        
        assert error.status_code == 400
        assert error.validation_errors == validation_errors
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_success(self):
        """Test retry logic with successful call."""
        call_count = 0
        
        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await retry_with_backoff(successful_func, max_retries=3)
        
        assert result == "success"
        assert call_count == 1  # Should succeed on first try
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_eventual_success(self):
        """Test retry logic with eventual success."""
        call_count = 0
        
        async def eventually_successful_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RateLimitError(remaining_seconds=1)
            return "success"
        
        result = await retry_with_backoff(eventually_successful_func, max_retries=3, base_delay=0.1)
        
        assert result == "success"
        assert call_count == 3  # Should succeed on third try
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff_failure(self):
        """Test retry logic with all retries failing."""
        call_count = 0
        
        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise RateLimitError(remaining_seconds=1)
        
        with pytest.raises(RateLimitError):
            await retry_with_backoff(failing_func, max_retries=2, base_delay=0.1)
        
        assert call_count == 3  # Initial + 2 retries


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    @pytest.mark.asyncio
    async def test_token_bucket_acquire(self):
        """Test token bucket acquire."""
        bucket = TokenBucket(rate=10, capacity=10)
        
        # Should be able to acquire tokens
        result = await bucket.acquire(tokens=5)
        assert result is True
        
        # Check available tokens decreased
        available = bucket.get_available_tokens()
        assert available < 10
    
    @pytest.mark.asyncio
    async def test_token_bucket_refill(self):
        """Test token bucket refill over time."""
        bucket = TokenBucket(rate=10, capacity=10)
        
        # Acquire all tokens
        await bucket.acquire(tokens=10)
        
        # Wait for refill
        await asyncio.sleep(0.5)
        
        # Should have some tokens available
        available = bucket.get_available_tokens()
        assert available > 0
    
    @pytest.mark.asyncio
    async def test_rate_limiter_orders(self):
        """Test rate limiter for orders."""
        limiter = EmagRateLimiter()
        
        # Should be able to acquire for orders
        await limiter.acquire("orders", timeout=1.0)
        
        # Check stats
        stats = await limiter.get_stats()
        assert stats["orders_requests"] > 0
    
    @pytest.mark.asyncio
    async def test_rate_limiter_other(self):
        """Test rate limiter for other operations."""
        limiter = EmagRateLimiter()
        
        # Should be able to acquire for other operations
        await limiter.acquire("other", timeout=1.0)
        
        # Check stats
        stats = await limiter.get_stats()
        assert stats["other_requests"] > 0
    
    @pytest.mark.asyncio
    async def test_rate_limiter_usage_percentage(self):
        """Test rate limiter usage percentage calculation."""
        limiter = EmagRateLimiter()
        
        # Get initial usage
        usage = limiter.get_usage_percentage("orders")
        assert 0.0 <= usage <= 1.0


class TestMonitoring:
    """Test monitoring functionality."""
    
    @pytest.mark.asyncio
    async def test_metrics_collector(self):
        """Test metrics collector."""
        from app.services.emag_monitoring import MetricsCollector
        
        collector = MetricsCollector(window_size=60)
        
        # Record some requests
        await collector.record_request(response_time=100.0, success=True)
        await collector.record_request(response_time=200.0, success=True)
        await collector.record_request(response_time=150.0, success=False)
        
        # Get metrics
        metrics = await collector.get_metrics()
        
        assert metrics["total_requests"] == 3
        assert metrics["total_errors"] == 1
        assert metrics["error_rate"] > 0
        assert metrics["average_response_time"] > 0


class TestBackupService:
    """Test backup service functionality."""
    
    @pytest.mark.asyncio
    async def test_list_backups(self):
        """Test listing backups."""
        from app.services.backup_service import BackupService
        
        mock_session = AsyncMock()
        service = BackupService(mock_session, backup_dir="backups")
        
        # List backups (should not fail even if directory is empty)
        backups = await service.list_backups()
        
        assert isinstance(backups, list)
    
    @pytest.mark.asyncio
    async def test_cleanup_old_backups(self):
        """Test cleanup of old backups."""
        from app.services.backup_service import BackupService
        
        mock_session = AsyncMock()
        service = BackupService(mock_session, backup_dir="backups")
        
        # Cleanup (should not fail even if no backups exist)
        result = await service.cleanup_old_backups(days=30)
        
        assert result["success"] is True
        assert "deleted_count" in result


def test_imports():
    """Test that all new modules can be imported."""
    # This test ensures all modules are syntactically correct
    from app.core import emag_constants
    from app.core import emag_errors
    from app.core import emag_rate_limiter
    from app.services import order_validation
    from app.services import emag_monitoring
    from app.services import backup_service
    
    assert emag_constants is not None
    assert emag_errors is not None
    assert emag_rate_limiter is not None
    assert order_validation is not None
    assert emag_monitoring is not None
    assert backup_service is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
