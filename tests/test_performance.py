"""Performance and load testing."""

import asyncio
import time

import pytest

# Import the functions we want to benchmark
from app.core.security import get_password_hash, verify_password, create_access_token


class TestPerformance:
    """Performance and load testing."""

    @pytest.mark.benchmark
    def test_password_hashing_benchmark(self, benchmark):
        """Benchmark password hashing performance."""
        password = "SecureTestPassword123!"

        # Benchmark the password hashing function
        result = benchmark(get_password_hash, password)

        # Ensure the result is valid
        assert result is not None
        assert len(result) > 0
        assert verify_password(password, result)

    @pytest.mark.benchmark
    def test_jwt_token_creation_benchmark(self, benchmark):
        """Benchmark JWT token creation performance."""
        # Benchmark the JWT token creation
        result = benchmark(create_access_token, subject="test_user_123")

        # Ensure the result is valid
        assert result is not None
        assert len(result) > 0
        assert isinstance(result, str)
        assert len(result.split('.')) == 3  # JWT has 3 parts

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_response_time_under_100ms(self, test_client):
        """Test that API responses are under 100ms."""
        start_time = time.time()

        response = await test_client.get("/health")

        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds

        assert response.status_code == 200
        assert response_time < 100, f"Response time too slow: {response_time}ms"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_requests(self, test_client):
        """Test handling of concurrent requests."""

        async def make_request():
            return await test_client.get("/health")

        # Make multiple concurrent requests
        num_requests = 10
        tasks = [make_request() for _ in range(num_requests)]

        start_time = time.time()
        responses = await asyncio.gather(*tasks)
        end_time = time.time()

        total_time = end_time - start_time

        # All requests should succeed
        assert all(r.status_code == 200 for r in responses)

        # Should handle concurrent requests efficiently
        avg_time_per_request = total_time / num_requests
        assert (
            avg_time_per_request < 0.1
        ), f"Too slow handling concurrent requests: {avg_time_per_request}s per request"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_memory_usage(self, test_client):
        """Test memory usage during operations."""
        import os

        import psutil

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform operations
        for _ in range(100):
            response = await test_client.get("/health")
            assert response.status_code == 200

        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Memory increase should be reasonable
        memory_increase = final_memory - initial_memory
        assert (
            memory_increase < 50
        ), f"Memory usage increased too much: {memory_increase}MB"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_database_query_performance(self, test_db_session):
        """Test database query performance."""
        # This would test actual database query performance
        # Would need to set up test data first

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_api_rate_limiting(self, test_client):
        """Test API rate limiting."""
        # Make many requests in quick succession
        num_requests = 150  # More than the rate limit
        tasks = [test_client.get("/health") for _ in range(num_requests)]

        start_time = time.time()
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        # Should complete quickly even with rate limiting
        total_time = end_time - start_time
        assert total_time < 10, f"Rate limiting caused excessive delay: {total_time}s"

        # Should have some rate-limited responses
        status_codes = [
            getattr(r, "status_code", None) if not isinstance(r, Exception) else None
            for r in responses
        ]
        rate_limited_count = status_codes.count(429)  # 429 = Too Many Requests

        assert rate_limited_count > 0, "Should have some rate-limited requests"


class TestResourceUsage:
    """Test resource usage patterns."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_cpu_usage(self, test_client):
        """Test CPU usage during operations."""
        import os

        import psutil

        # Get initial CPU usage
        process = psutil.Process(os.getpid())
        process.cpu_percent()

        # Perform CPU-intensive operations
        for _ in range(100):
            response = await test_client.get("/health")
            assert response.status_code == 200

        # CPU usage should not be excessive
        final_cpu = process.cpu_percent()
        assert final_cpu < 80, f"CPU usage too high: {final_cpu}%"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_file_descriptor_usage(self, test_client):
        """Test file descriptor usage."""
        import os

        import psutil

        # Get initial file descriptor count
        process = psutil.Process(os.getpid())
        initial_fds = process.num_fds()

        # Perform operations that might open files
        for _ in range(50):
            response = await test_client.get("/health")
            assert response.status_code == 200

        # File descriptor count should not grow excessively
        final_fds = process.num_fds()
        fd_increase = final_fds - initial_fds

        assert (
            fd_increase < 20
        ), f"File descriptor leak detected: {fd_increase} additional FDs"
