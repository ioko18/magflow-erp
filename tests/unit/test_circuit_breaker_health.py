"""Test script for circuit breaker functionality and health checks."""

import asyncio
import logging
import time
from typing import Dict, List
from unittest.mock import patch
import pytest

from app.core.circuit_breaker import (
    DATABASE_CIRCUIT_BREAKER,
    CircuitState,
    CircuitBreaker,
    get_circuit_breaker,
)
from app.core.health.circuit_breaker_check import check_circuit_breakers


# Add batched implementation for performance comparison
async def check_circuit_breakers_batch(batch_size: int = 10) -> Dict:
    """Check the status of all circuit breakers in batches.

    Args:
        batch_size: Number of circuit breakers to process in parallel

    Returns:
        Dict containing the health status of all circuit breakers
    """
    from app.core.circuit_breaker import _registry, _registry_lock

    async def check_breaker(name: str, breaker: CircuitBreaker) -> Dict:
        """Check a single circuit breaker's status."""
        try:
            # Match the behavior of check_circuit_breakers in circuit_breaker_check.py
            state = str(breaker.state).split(".")[-1].lower()
            status = "healthy" if state in ["closed", "half-open"] else "unhealthy"

            return {
                "name": name,
                "status": status,
                "state": state,
                "failure_count": breaker.failure_count,
                "threshold": breaker.failure_threshold,
                "opened_at": breaker._opened_at,
                "recovery_timeout": breaker.recovery_timeout,
            }
        except Exception as e:
            return {"name": name, "status": "error", "error": str(e), "state": "error"}

    async def process_batch(batch: List[tuple]) -> List[Dict]:
        """Process a batch of circuit breakers."""
        tasks = [check_breaker(name, breaker) for name, breaker in batch]
        return await asyncio.gather(*tasks, return_exceptions=False)

    # Get all circuit breakers
    with _registry_lock:
        breakers = list(_registry.items())

    if not breakers:
        return {
            "status": "healthy",
            "message": "No circuit breakers registered",
            "metadata": {"circuit_breakers": {}},
        }

    # Process in batches
    all_results = []
    for i in range(0, len(breakers), batch_size):
        batch = breakers[i : i + batch_size]
        batch_results = await process_batch(batch)
        all_results.extend(batch_results)

    # Determine overall status
    status = "healthy"
    breaker_statuses = {}

    for result in all_results:
        breaker_statuses[result["name"]] = result
        if result["status"] != "healthy":
            status = "unhealthy"

    return {
        "status": status,
        "message": f"Checked {len(breaker_statuses)} circuit breakers",
        "metadata": {"circuit_breakers": breaker_statuses},
    }


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def reset_circuit_breaker():
    """Reset the circuit breaker to a known state before each test."""
    # Clear the registry to avoid test interference
    from app.core.circuit_breaker import _registry, _registry_lock

    with _registry_lock:
        _registry.clear()

    # Reset the default circuit breaker
    cb = DATABASE_CIRCUIT_BREAKER
    with cb._lock:
        cb._state = CircuitState.CLOSED
        cb._failure_count = 0
        cb._opened_at = None
        cb._half_open_attempts = 0
        cb._failure_timestamps.clear()
        if hasattr(cb, "_half_open_timer") and cb._half_open_timer is not None:
            cb._half_open_timer.cancel()
            cb._half_open_timer = None

    # Re-register the default circuit breaker
    with _registry_lock:
        _registry[cb.name] = cb

    return cb


def test_circuit_breaker_state_transitions():
    """Test the circuit breaker state transitions directly."""
    # Create a new circuit breaker with a short recovery timeout for testing
    cb = CircuitBreaker(
        name="test_circuit_health",
        failure_threshold=3,
        recovery_timeout=0.1,  # Short timeout for testing
        half_open_max_attempts=2,
    )

    # Reset to known state
    with cb._lock:
        cb._state = CircuitState.CLOSED
        cb._failure_count = 0
        cb._opened_at = None

    # Test initial state
    assert str(cb.state) == "closed", f"Expected 'closed', got '{cb.state}'"
    assert cb.failure_count == 0

    # Record failures until circuit opens
    for _ in range(cb.failure_threshold - 1):
        cb.record_failure()

    # Should still be closed
    assert str(cb.state) == "closed", f"Expected 'closed', got '{cb.state}'"

    # One more failure should open the circuit
    cb.record_failure()
    assert str(cb.state) == "open", f"Expected 'open', got '{cb.state}'"

    # Manually set the opened_at time to trigger half-open transition
    with cb._lock:
        cb._opened_at = time.monotonic() - (cb.recovery_timeout + 0.1)

    # Access the state to trigger the transition check
    current_state = str(cb.state)

    # Should transition to half-open after timeout
    assert current_state == "half-open", f"Expected 'half-open', got '{current_state}'"

    # Record success to close the circuit
    cb.record_success()
    assert str(cb.state) == "closed", f"Expected 'closed', got '{cb.state}'"
    assert cb.failure_count == 0, "Failure count should be reset"


def test_circuit_breaker_half_open_handling(reset_circuit_breaker):
    """Test half-open state handling."""
    cb = reset_circuit_breaker

    # Set to half-open state
    with cb._lock:
        cb._state = CircuitState.HALF_OPEN

    # Record a failure - should go back to open
    cb.record_failure()
    assert str(cb.state) == "open", f"Expected 'open', got '{cb.state}'"


def test_circuit_breaker_performance():
    """Test that circuit breaker operations are fast."""
    # Create a test circuit breaker
    cb = CircuitBreaker(name="test_perf", failure_threshold=3, recovery_timeout=1.0)

    # Test that operations complete in a reasonable time
    start_time = time.perf_counter()
    for _ in range(1000):
        cb.record_success()
    end_time = time.perf_counter()

    # Verify performance (should complete in less than 0.1 seconds for 1000 ops)
    assert (end_time - start_time) < 0.1, "Circuit breaker operations too slow"


@pytest.mark.asyncio
async def test_health_check_all_healthy():
    """Test health check when all circuit breakers are healthy."""
    # Create a test circuit breaker in closed state
    _ = get_circuit_breaker("test_healthy", failure_threshold=3)

    # Get health status
    status = await check_circuit_breakers()

    # Verify status
    assert status["status"] == "healthy"
    assert "test_healthy" in status["metadata"]["circuit_breakers"]
    assert status["metadata"]["circuit_breakers"]["test_healthy"]["status"] == "healthy"
    assert status["metadata"]["circuit_breakers"]["test_healthy"]["state"] == "closed"


@pytest.mark.asyncio
async def test_health_check_unhealthy():
    """Test health check when a circuit breaker is open."""
    # Create a test circuit breaker and force it to open
    cb = get_circuit_breaker("test_unhealthy", failure_threshold=1)
    cb.record_failure()  # This will open the circuit

    # Get health status
    status = await check_circuit_breakers()

    # Verify status shows unhealthy
    assert status["status"] == "unhealthy"
    assert (
        status["metadata"]["circuit_breakers"]["test_unhealthy"]["status"]
        == "unhealthy"
    )
    assert status["metadata"]["circuit_breakers"]["test_unhealthy"]["state"] == "open"


@pytest.mark.asyncio
async def test_health_check_half_open():
    """Test health check when a circuit breaker is half-open."""
    # Create a test circuit breaker with a short recovery timeout
    cb = get_circuit_breaker(
        "test_half_open",
        failure_threshold=1,
        recovery_timeout=0.1,
        failure_window_seconds=0.1,
    )

    # Record a failure to open the circuit
    cb.record_failure()

    # Fast-forward time to trigger half-open state
    current_time = time.monotonic()
    with patch("time.monotonic") as mock_monotonic:
        # Mock time to be after the recovery timeout
        mock_monotonic.return_value = current_time + 0.2

        # Get health status with mocked time
        status = await check_circuit_breakers()

    # Verify status shows half-open as healthy
    assert status["status"] == "healthy"
    assert (
        status["metadata"]["circuit_breakers"]["test_half_open"]["state"] == "half-open"
    )


@pytest.mark.asyncio
async def test_health_check_multiple_breakers():
    """Test health check with multiple circuit breakers in different states."""
    # Create multiple circuit breakers in different states
    _ = get_circuit_breaker("test_healthy_1")  # Closed by default
    unhealthy_cb = get_circuit_breaker("test_unhealthy_1", failure_threshold=1)
    unhealthy_cb.record_failure()  # Open this one

    # Get health status
    status = await check_circuit_breakers()

    # Verify overall status is unhealthy if any breaker is open
    assert status["status"] == "unhealthy"

    # Verify all breakers are reported
    assert "test_healthy_1" in status["metadata"]["circuit_breakers"]
    assert "test_unhealthy_1" in status["metadata"]["circuit_breakers"]

    # Verify individual statuses
    assert (
        status["metadata"]["circuit_breakers"]["test_healthy_1"]["status"] == "healthy"
    )
    assert (
        status["metadata"]["circuit_breakers"]["test_unhealthy_1"]["status"]
        == "unhealthy"
    )


@pytest.mark.asyncio
async def test_health_check_empty_registry():
    """Test health check when no circuit breakers are registered."""
    # Clear the registry
    from app.core.circuit_breaker import _registry, _registry_lock

    with _registry_lock:
        _registry.clear()

    # Get health status
    status = await check_circuit_breakers()

    # Verify status is healthy with no breakers
    assert status["status"] == "healthy"
    assert status["metadata"]["circuit_breakers"] == {}


@pytest.mark.asyncio
async def test_health_check_metrics():
    """Test that health check includes proper metrics in the response."""
    # Create a test circuit breaker
    cb = get_circuit_breaker("test_metrics", failure_threshold=2)

    # Record one failure (but not enough to open the circuit)
    cb.record_failure()

    # Get health status
    status = await check_circuit_breakers()

    # Verify metrics are included
    metrics = status["metadata"]["circuit_breakers"]["test_metrics"]
    assert "failures" in metrics
    assert metrics["failures"] == 1
    assert "threshold" in metrics
    assert metrics["threshold"] == 2
    assert "recovery_timeout" in metrics

    # Record another failure to open the circuit
    cb.record_failure()
    status = await check_circuit_breakers()
    metrics = status["metadata"]["circuit_breakers"]["test_metrics"]
    assert metrics["status"] == "unhealthy"
    assert metrics["state"] == "open"
    assert "opened_at" in metrics


@pytest.mark.asyncio
async def test_async_health_check():
    """Test that the health check works in an async context."""
    # Create a test circuit breaker
    _ = get_circuit_breaker("test_async")

    # Get health status asynchronously
    status = await check_circuit_breakers()

    # Verify status
    assert status["status"] == "healthy"
    assert "test_async" in status["metadata"]["circuit_breakers"]


@pytest.mark.asyncio
async def test_health_check_performance():
    """Test that health check performs well with many circuit breakers."""
    from app.core.circuit_breaker import _registry, _registry_lock

    # Clear existing circuit breakers to ensure consistent test environment
    with _registry_lock:
        _registry.clear()

    # Create many circuit breakers with different states using list comprehension
    current_time = time.time()
    breakers = []

    for i in range(100):  # Reduced from 100 to 50 for faster tests
        breaker_name = f"test_perf_{i}"
        breaker = get_circuit_breaker(breaker_name)
        breakers.append(breaker)

        # Set breaker state based on index
        if i % 3 == 0:
            # OPEN state
            breaker._failure_count = breaker.failure_threshold + 1
            breaker._state = CircuitState.OPEN
            breaker._opened_at = current_time
        elif i % 5 == 0:
            # HALF_OPEN state
            breaker._failure_count = 0
            breaker._state = CircuitState.HALF_OPEN
            breaker._opened_at = current_time - (breaker.recovery_timeout + 1)
        else:
            # CLOSED state (default)
            breaker._failure_count = 0
            breaker._state = CircuitState.CLOSED
            breaker._opened_at = None

    # Warm-up runs to avoid cold start issues
    warmup_iters = 3
    for _ in range(warmup_iters):
        await check_circuit_breakers()
        await check_circuit_breakers_batch(batch_size=20)

    # Run performance tests
    test_iters = 5  # Reduced from 10 to 5 for faster tests
    batch_sizes = [10, 20, 50]

    # Time standard health check
    standard_times = []
    for _ in range(test_iters):
        start_time = time.perf_counter()
        await check_circuit_breakers()
        standard_times.append(time.perf_counter() - start_time)

    # Time batched health checks
    batched_times = {size: [] for size in batch_sizes}
    for size in batch_sizes:
        for _ in range(test_iters):
            start_time = time.perf_counter()
            await check_circuit_breakers_batch(batch_size=size)
            batched_times[size].append(time.perf_counter() - start_time)

    # Get final status for assertions
    status = await check_circuit_breakers()
    batched_status = await check_circuit_breakers_batch(batch_size=20)

    # Calculate statistics
    def get_stats(times):
        return {
            "avg": sum(times) / len(times),
            "min": min(times),
            "max": max(times),
            "total": sum(times),
        }

    standard_stats = get_stats(standard_times)
    batched_stats = {size: get_stats(times) for size, times in batched_times.items()}

    # Log performance results
    logger.info("\n" + "=" * 80)
    logger.info("Performance Test Results (after warmup):")

    def log_stats(name, stats):
        logger.info(
            f"{name}: {stats['avg']*1000:.2f}ms avg "
            f"(min: {stats['min']*1000:.2f}ms, max: {stats['max']*1000:.2f}ms, "
            f"total: {stats['total']*1000:.2f}ms)"
        )

    log_stats("Standard check", standard_stats)
    for size, stats in sorted(batched_stats.items()):
        log_stats(f"Batch size {size}", stats)

    # Find best batch performance
    best_batch_size, best_batch_stats = min(
        batched_stats.items(), key=lambda x: x[1]["avg"]
    )

    logger.info(
        f"\nBest batch performance: size={best_batch_size} "
        f"({best_batch_stats['avg']*1000:.2f}ms avg)"
    )
    logger.info("=" * 80 + "\n")

    # Verify both methods return the same number of breakers
    num_breakers = len(status["metadata"]["circuit_breakers"])
    assert (
        num_breakers == len(batched_status["metadata"]["circuit_breakers"])
    ), f"Mismatch in number of breakers: {num_breakers} vs {len(batched_status['metadata']['circuit_breakers'])}"

    # Verify unhealthy breakers match between implementations
    def get_unhealthy(status_dict):
        return {
            name: cb.get("status")
            for name, cb in status_dict["metadata"]["circuit_breakers"].items()
            if cb.get("status") != "healthy"
        }

    unhealthy_standard = get_unhealthy(status)
    unhealthy_batched = get_unhealthy(batched_status)

    assert unhealthy_standard == unhealthy_batched, (
        f"Mismatch in unhealthy breakers. "
        f"Standard: {set(unhealthy_standard.items()) - set(unhealthy_batched.items())}, "
        f"Batched: {set(unhealthy_batched.items()) - set(unhealthy_standard.items())}"
    )

    # Performance assertions with more informative messages
    perf_threshold = 0.05  # 50ms threshold (reduced from 100ms)
    assert standard_stats["avg"] < perf_threshold, (
        f"Standard health check too slow: {standard_stats['avg']*1000:.2f}ms "
        f"(threshold: {perf_threshold*1000:.2f}ms)"
    )

    assert best_batch_stats["avg"] < perf_threshold, (
        f"Best batch check too slow: {best_batch_stats['avg']*1000:.2f}ms "
        f"(threshold: {perf_threshold*1000:.2f}ms)"
    )

    # Clean up
    with _registry_lock:
        _registry.clear()
