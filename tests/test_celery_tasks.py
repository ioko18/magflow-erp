"""Tests for Celery tasks functionality."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from app.services.tasks.sample import add, echo, slow


class TestCeleryTasks:
    """Test suite for Celery tasks."""

    def test_echo_task_sync(self):
        """Test echo task synchronously."""
        result = echo("test message")
        assert result == "echo: test message"

    def test_add_task_sync(self):
        """Test add task synchronously."""
        result = add(2, 3)
        assert result == 5

    def test_slow_task_sync(self):
        """Test slow task synchronously."""
        result = slow(0.1)
        assert result == "slept 0.1s"

    def test_echo_task_with_special_characters(self):
        """Test echo task with special characters."""
        test_message = "Hello, 世界! 🌍 @#$%^&*()"
        result = echo(test_message)
        assert result == f"echo: {test_message}"

    def test_add_task_negative_numbers(self):
        """Test add task with negative numbers."""
        result = add(-5, 8)
        assert result == 3

    def test_add_task_zero_values(self):
        """Test add task with zero values."""
        result = add(0, 0)
        assert result == 0

    def test_slow_task_zero_seconds(self):
        """Test slow task with zero seconds."""
        result = slow(0)
        assert result == "slept 0s"

    def test_slow_task_long_duration(self):
        """Test slow task with longer duration."""
        result = slow(2)
        assert result == "slept 2s"


class TestCeleryTasksAsync:
    """Test suite for async Celery tasks functionality."""

    @pytest.mark.asyncio
    async def test_echo_task_async(self):
        """Test echo task asynchronously."""
        # This would normally use echo.delay(), but for unit testing
        # we'll test the function directly
        result = await asyncio.get_event_loop().run_in_executor(
            None, echo, "async test"
        )
        assert result == "echo: async test"

    @pytest.mark.asyncio
    async def test_add_task_async(self):
        """Test add task asynchronously."""
        result = await asyncio.get_event_loop().run_in_executor(None, add, 10, 15)
        assert result == 25

    @pytest.mark.asyncio
    async def test_slow_task_async(self):
        """Test slow task asynchronously."""
        start_time = asyncio.get_event_loop().time()
        result = await asyncio.get_event_loop().run_in_executor(None, slow, 0.5)
        end_time = asyncio.get_event_loop().time()
        assert result == "slept 0.5s"
        assert end_time - start_time >= 0.5


class TestCeleryTasksIntegration:
    """Integration tests for Celery tasks with mocking."""

    def test_celery_task_result_mocked(self):
        """Test Celery task result handling with mocking."""
        with patch("app.services.tasks.sample.echo.delay") as mock_delay:
            mock_task = MagicMock()
            mock_task.id = "test-task-123"
            mock_task.get.return_value = "echo: mocked result"
            mock_delay.return_value = mock_task

            # Simulate calling the task
            task = echo.delay("test message")
            result = task.get()

            assert result == "echo: mocked result"
            assert task.id == "test-task-123"
            mock_delay.assert_called_once_with("test message")

    def test_celery_task_exception_handling(self):
        """Test Celery task exception handling."""
        with patch("app.services.tasks.sample.echo.delay") as mock_delay:
            mock_task = MagicMock()
            mock_task.id = "failing-task-456"
            mock_task.get.side_effect = Exception("Task failed")
            mock_delay.return_value = mock_task

            task = echo.delay("failing message")
            with pytest.raises(Exception, match="Task failed"):
                task.get()

    def test_celery_task_timeout_handling(self):
        """Test Celery task timeout handling."""
        with patch("app.services.tasks.sample.slow.delay") as mock_delay:
            mock_task = MagicMock()
            mock_task.id = "slow-task-789"
            # Simulate a timeout by not returning
            mock_task.get.side_effect = TimeoutError("Task timed out")
            mock_delay.return_value = mock_task

            task = slow.delay(10)
            with pytest.raises(TimeoutError, match="Task timed out"):
                task.get()


class TestCeleryReadinessEndpoint:
    """Test suite for Celery readiness endpoint."""

    @pytest.mark.asyncio
    async def test_readiness_endpoint_success(self, client: AsyncClient):
        """Test Celery readiness endpoint when worker is ready."""
        # Mock successful task execution
        with patch("app.services.tasks.sample.echo.delay") as mock_delay:
            mock_task = MagicMock()
            mock_task.id = "readiness-test-123"
            mock_task.get.return_value = "echo: worker-readiness-test"
            mock_delay.return_value = mock_task

            response = await client.get("/api/v1/tasks/ready")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
            assert data["message"] == "Celery worker is responsive"
            assert data["test_result"] == "echo: worker-readiness-test"
            assert "task_id" in data
            assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_readiness_endpoint_timeout(self, client: AsyncClient):
        """Test Celery readiness endpoint when worker times out."""
        with patch("app.services.tasks.sample.echo.delay") as mock_delay:
            mock_task = MagicMock()
            mock_task.id = "timeout-test-456"
            mock_task.get.side_effect = asyncio.TimeoutError("Timeout")
            mock_delay.return_value = mock_task

            response = await client.get("/api/v1/tasks/ready")

            assert response.status_code == 503
        data = response.json()
        assert data.get("detail", {}).get("status") == "unready"
        assert "not responding within timeout" in data.get("detail", {}).get("message", "")

    @pytest.mark.asyncio
    async def test_readiness_endpoint_exception(self, client: AsyncClient):
        """Test Celery readiness endpoint when worker throws exception."""
        with patch("app.services.tasks.sample.echo.delay") as mock_delay:
            mock_task = MagicMock()
            mock_task.id = "error-test-789"
            mock_task.get.side_effect = Exception("Worker error")
            mock_delay.return_value = mock_task

            response = await client.get("/api/v1/tasks/ready")

            assert response.status_code == 503
        data = response.json()
        assert data.get("detail", {}).get("status") == "unready"
        assert "Worker error" in data.get("detail", {}).get("message", "")

    @pytest.mark.asyncio
    async def test_readiness_endpoint_no_worker(self, client: AsyncClient):
        """Test Celery readiness endpoint when no worker is available."""
        with patch("app.services.tasks.sample.echo.delay") as mock_delay:
            mock_delay.side_effect = Exception("No worker available")

            response = await client.get("/api/v1/tasks/ready")

            assert response.status_code == 503
        data = response.json()
        assert data.get("detail", {}).get("status") == "unready"
        assert "No worker available" in data.get("detail", {}).get("message", "")


class TestCeleryTaskPerformance:
    """Performance tests for Celery tasks."""

    def test_echo_task_performance(self, benchmark):
        """Benchmark echo task performance."""
        result = benchmark(echo, "performance test")
        assert result == "echo: performance test"

    def test_add_task_performance(self, benchmark):
        """Benchmark add task performance."""
        result = benchmark(add, 1000, 2000)
        assert result == 3000

    def test_multiple_tasks_concurrent(self):
        """Test concurrent execution of multiple tasks."""
        import concurrent.futures

        def run_task(task_func, *args):
            return task_func(*args)

        tasks = [
            (echo, "concurrent test 1"),
            (add, 10, 20),
            (echo, "concurrent test 2"),
            (add, 5, 15),
        ]

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda t: run_task(*t), tasks))

        expected = ["echo: concurrent test 1", 30, "echo: concurrent test 2", 20]
        assert results == expected


class TestCeleryTaskEdgeCases:
    """Test edge cases for Celery tasks."""

    def test_echo_task_empty_string(self):
        """Test echo task with empty string."""
        result = echo("")
        assert result == "echo: "

    def test_echo_task_none_input(self):
        """Test echo task with None input (should fail gracefully)."""
        with pytest.raises(TypeError):
            echo(None)

    def test_add_task_large_numbers(self):
        """Test add task with large numbers."""
        result = add(2**30, 2**30)
        assert result == 2**31

    def test_slow_task_negative_seconds(self):
        """Test slow task with negative seconds."""
        result = slow(-1)
        assert result == "slept -1s"

    def test_slow_task_float_seconds(self):
        """Test slow task with float seconds."""
        result = slow(1.5)
        assert result == "slept 1.5s"

    def test_slow_task_very_large_seconds(self):
        """Test slow task with very large seconds (should be capped)."""
        result = slow(10000)
        assert result == "slept 10000s"
