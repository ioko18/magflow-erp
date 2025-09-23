"""Tests for eMAG integration rate limiting functionality.

This module tests the EmagRateLimiter class and its rate limiting behavior
according to eMAG API v4.4.8 specifications.
"""

import asyncio
import time
from unittest.mock import patch

import pytest

from app.services.emag_integration_service import EmagRateLimiter


class TestEmagRateLimiter:
    """Test cases for EmagRateLimiter class."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a test rate limiter instance."""
        return EmagRateLimiter(
            orders_rps=12,
            other_rps=3,
            jitter_max=0.1,  # Minimal jitter for testing
        )

    def test_initialization(self, rate_limiter):
        """Test rate limiter initialization."""
        assert rate_limiter.orders_rps == 12
        assert rate_limiter.other_rps == 3
        assert rate_limiter.jitter_max == 0.1
        assert hasattr(rate_limiter, "_last_request_times")
        assert hasattr(rate_limiter, "_request_counts")
        assert hasattr(rate_limiter, "_windows")

    @pytest.mark.asyncio
    async def test_orders_rate_limiting(self, rate_limiter):
        """Test rate limiting for orders endpoints."""
        start_time = time.time()

        # Should allow 12 requests immediately
        for i in range(12):
            await rate_limiter.acquire("orders")
            assert time.time() - start_time < 0.1  # Should be fast

        # 13th request should be delayed
        delay_start = time.time()
        await rate_limiter.acquire("orders")
        delay_duration = time.time() - delay_start

        # Should be delayed by approximately 1 second minus jitter
        assert delay_duration >= 0.9  # At least 0.9 seconds
        assert delay_duration <= 1.2  # At most 1.2 seconds (with jitter)

    @pytest.mark.asyncio
    async def test_other_rate_limiting(self, rate_limiter):
        """Test rate limiting for other endpoints."""
        start_time = time.time()

        # Should allow 3 requests immediately
        for i in range(3):
            await rate_limiter.acquire("other")
            assert time.time() - start_time < 0.1

        # 4th request should be delayed
        delay_start = time.time()
        await rate_limiter.acquire("other")
        delay_duration = time.time() - delay_start

        # Should be delayed by approximately 1 second minus jitter
        assert delay_duration >= 0.9
        assert delay_duration <= 1.2

    @pytest.mark.asyncio
    async def test_independent_resource_types(self, rate_limiter):
        """Test that different resource types are rate limited independently."""
        # Fill up orders rate limit
        for i in range(12):
            await rate_limiter.acquire("orders")

        # Other requests should still be allowed
        start_time = time.time()
        for i in range(3):
            await rate_limiter.acquire("other")
            assert time.time() - start_time < 0.1

    @pytest.mark.asyncio
    async def test_window_reset(self, rate_limiter):
        """Test that rate limit windows reset after the time period."""
        # Fill up the rate limit
        for i in range(3):
            await rate_limiter.acquire("other")

        # Wait for window to reset (just over 1 second)
        await asyncio.sleep(1.1)

        # Should allow requests again
        start_time = time.time()
        for i in range(3):
            await rate_limiter.acquire("other")
            assert time.time() - start_time < 0.1

    @pytest.mark.asyncio
    async def test_jitter_effect(self, rate_limiter):
        """Test that jitter is applied to prevent thundering herd."""
        # Mock random.uniform to return a known value
        with patch("random.uniform", return_value=0.05):
            # Fill up rate limit
            for i in range(3):
                await rate_limiter.acquire("other")

            # Next request should include jitter
            delay_start = time.time()
            await rate_limiter.acquire("other")
            delay_duration = time.time() - delay_start

            # Should include jitter (0.05 in this case)
            assert delay_duration >= 0.95  # 1.0 - 0.05 jitter
            assert delay_duration <= 1.15

    @pytest.mark.asyncio
    async def test_default_resource_type(self, rate_limiter):
        """Test that default resource type is 'other'."""
        # Should work without specifying resource type
        start_time = time.time()
        for i in range(3):
            await rate_limiter.acquire()  # No resource_type specified
            assert time.time() - start_time < 0.1

        # 4th request should be delayed
        delay_start = time.time()
        await rate_limiter.acquire()
        delay_duration = time.time() - delay_start

        assert delay_duration >= 0.9
        assert delay_duration <= 1.2

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, rate_limiter):
        """Test rate limiting with concurrent requests."""

        async def make_request(resource_type):
            return await rate_limiter.acquire(resource_type)

        # Launch multiple concurrent requests
        tasks = [make_request("other") for _ in range(6)]
        start_time = time.time()

        await asyncio.gather(*tasks)

        total_time = time.time() - start_time
        # Should take at least 1 second (1 window of 3 requests, then wait for next window)
        assert total_time >= 1.0
        assert total_time <= 2.0  # Allow some margin for jitter

    def test_custom_rates(self):
        """Test rate limiter with custom rates."""
        custom_limiter = EmagRateLimiter(orders_rps=5, other_rps=2)

        assert custom_limiter.orders_rps == 5
        assert custom_limiter.other_rps == 2


class TestEmagRateLimiterIntegration:
    """Integration tests for rate limiter with API client."""

    @pytest.mark.asyncio
    async def test_rate_limiter_integration(self):
        """Test rate limiter integration with API client."""
        from app.services.emag_integration_service import EmagApiClient, EmagApiConfig

        config = EmagApiConfig(
            environment="sandbox",
            api_username="test",
            api_password="test",
            orders_rate_rps=12,
            other_rate_rps=3,
        )

        client = EmagApiClient(config)

        # Verify rate limiter is properly configured
        assert client.rate_limiter.orders_rps == 12
        assert client.rate_limiter.other_rps == 3

    @pytest.mark.asyncio
    async def test_resource_type_detection(self):
        """Test that API client properly detects resource types."""
        from app.services.emag_integration_service import EmagApiClient, EmagApiConfig

        config = EmagApiConfig(
            environment="sandbox",
            api_username="test",
            api_password="test",
        )

        client = EmagApiClient(config)

        # Test order endpoints
        assert client._get_resource_type("/order/read") == "orders"
        assert client._get_resource_type("/order/save") == "orders"
        assert client._get_resource_type("/order/count") == "orders"
        assert client._get_resource_type("/order/acknowledge") == "orders"
        assert client._get_resource_type("/order/unlock-courier") == "orders"

        # Test other endpoints
        assert client._get_resource_type("/products") == "other"
        assert client._get_resource_type("/categories") == "other"
        assert client._get_resource_type("/product_offers") == "other"
        assert client._get_resource_type("/inventory/bulk") == "other"
