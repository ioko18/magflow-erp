"""Direct test for circuit breaker health check functionality."""

import asyncio
import logging
from typing import Dict, Any
import pytest

from app.core.circuit_breaker import CircuitBreaker, get_circuit_breaker, _registry
from app.core.health.circuit_breaker_check import check_circuit_breakers

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
TEST_CIRCUIT_NAME = "test_circuit_health"
TEST_CIRCUIT_NAME_2 = "another_test_circuit"
FAILURE_THRESHOLD = 3
RECOVERY_TIMEOUT = 0.1  # Shorter timeout for testing


async def get_circuit_status(breaker_name: str) -> Dict[str, Any]:
    """Helper to get the status of a specific circuit breaker."""
    status = await check_circuit_breakers()
    return status["metadata"]["circuit_breakers"][breaker_name]


def reset_circuit_breaker(name: str) -> None:
    """Helper to reset a circuit breaker for testing."""
    if name in _registry:
        del _registry[name]


@pytest.fixture(autouse=True)
def cleanup_circuit_breakers():
    """Fixture to clean up circuit breakers after each test."""
    # Store the original registry
    original_registry = _registry.copy()
    # Clear the registry before each test
    _registry.clear()

    yield

    # Restore the original registry after each test
    _registry.clear()
    _registry.update(original_registry)


async def test_initial_state():
    """Test that a new circuit breaker starts in the closed state."""
    # Get or create a test-specific circuit breaker
    breaker_name = f"{TEST_CIRCUIT_NAME}_initial"
    _ = get_circuit_breaker(
        breaker_name,
        failure_threshold=FAILURE_THRESHOLD,
        recovery_timeout=RECOVERY_TIMEOUT,
    )

    # Check initial state
    status = await check_circuit_breakers()
    assert breaker_name in status["metadata"]["circuit_breakers"]
    cb_status = status["metadata"]["circuit_breakers"][breaker_name]

    # The circuit breaker should be in 'closed' state initially
    assert cb_status["state"] == "closed"
    assert cb_status["status"] == "healthy"
    assert cb_status["failures"] == 0


async def test_failure_threshold():
    """Test that the circuit opens after exceeding failure threshold."""
    # Reset any existing circuit breaker
    reset_circuit_breaker(TEST_CIRCUIT_NAME)

    # Get or create a test-specific circuit breaker with a short window
    circuit_breaker = get_circuit_breaker(
        TEST_CIRCUIT_NAME,
        failure_threshold=FAILURE_THRESHOLD,
        recovery_timeout=RECOVERY_TIMEOUT,
        failure_window_seconds=10.0,  # Long enough window for test
    )

    # Record failures up to threshold - 1
    for i in range(FAILURE_THRESHOLD - 1):
        circuit_breaker.record_failure()
        status = await get_circuit_status(TEST_CIRCUIT_NAME)
        assert status["state"] == "closed"
        assert status["status"] == "healthy"
        assert status["failures"] == i + 1

    # One more failure should open the circuit
    circuit_breaker.record_failure()
    status = await get_circuit_status(TEST_CIRCUIT_NAME)
    assert status["state"] == "open"
    assert status["status"] == "unhealthy"
    assert (
        status["failures"] >= FAILURE_THRESHOLD
    )  # Could be more if previous tests left failures


async def test_half_open_state():
    """Test transition to half-open state after recovery timeout."""
    # Reset any existing circuit breaker
    reset_circuit_breaker(TEST_CIRCUIT_NAME)

    # Use a very short recovery timeout for testing (30ms)
    recovery_timeout = 0.03

    # Get or create a test-specific circuit breaker
    circuit_breaker = get_circuit_breaker(
        TEST_CIRCUIT_NAME,
        failure_threshold=2,  # Lower threshold for faster testing
        recovery_timeout=recovery_timeout,
        failure_window_seconds=1.0,  # Short window for test
    )

    # Open the circuit with 2 failures (exceeding threshold of 2)
    for _ in range(2):
        circuit_breaker.record_failure()

    # Verify it's open
    status = await get_circuit_status(TEST_CIRCUIT_NAME)
    assert status["state"] == "open", f"Expected OPEN, got {status['state']}"
    assert status["status"] == "unhealthy"

    # Wait for recovery timeout (add 50% buffer)
    await asyncio.sleep(recovery_timeout * 1.5)

    # Should transition to half-open state
    status = await get_circuit_status(TEST_CIRCUIT_NAME)
    assert status["state"] == "half-open", f"Expected HALF-OPEN, got {status['state']}"
    assert (
        status["status"] == "healthy"
    )  # half-open is considered healthy for monitoring

    # Record success - should close the circuit
    circuit_breaker.record_success()

    # Should be closed now
    status = await get_circuit_status(TEST_CIRCUIT_NAME)
    assert status["state"] == "closed", f"Expected CLOSED, got {status['state']}"
    assert (
        status["failures"] == 0
    ), "Failure count should be reset after successful close"
    assert status["status"] == "healthy"
    # Don't check failures count as it's now managed by the sliding window


async def test_failure_in_half_open_state():
    """Test that a failure in half-open state re-opens the circuit."""
    # Reset any existing circuit breaker
    reset_circuit_breaker(TEST_CIRCUIT_NAME)

    # Use a very short recovery timeout for testing (30ms)
    recovery_timeout = 0.03

    # Get or create a test-specific circuit breaker with lower threshold
    circuit_breaker = get_circuit_breaker(
        TEST_CIRCUIT_NAME,
        failure_threshold=2,  # Lower threshold for faster testing
        recovery_timeout=recovery_timeout,
        failure_window_seconds=1.0,  # Short window for test
    )

    # Open the circuit with 2 failures (exceeding threshold of 2)
    for _ in range(2):
        circuit_breaker.record_failure()

    # Verify it's open
    status = await get_circuit_status(TEST_CIRCUIT_NAME)
    assert status["state"] == "open", f"Expected OPEN, got {status['state']}"

    # Wait for recovery timeout (add 50% buffer)
    await asyncio.sleep(recovery_timeout * 1.5)

    # Should be in half-open state now
    status = await get_circuit_status(TEST_CIRCUIT_NAME)
    assert status["state"] == "half-open", f"Expected HALF-OPEN, got {status['state']}"

    # Record another failure in half-open state - should re-open the circuit
    circuit_breaker.record_failure()
    status = await get_circuit_status(TEST_CIRCUIT_NAME)
    assert (
        status["state"] == "open"
    ), f"Expected OPEN after failure in half-open, got {status['state']}"
    assert status["status"] == "unhealthy"


async def test_multiple_circuit_breakers(monkeypatch):
    """Test that multiple circuit breakers operate independently."""
    # Reset any existing circuit breakers
    reset_circuit_breaker(f"{TEST_CIRCUIT_NAME}_1")
    reset_circuit_breaker(f"{TEST_CIRCUIT_NAME}_2")

    # Use mock time for testing
    mock_time = 0.0

    # Create a mock time function that we can control
    def mock_monotonic():
        return mock_time

    # Patch the time.monotonic function
    monkeypatch.setattr("time.monotonic", mock_monotonic)

    # Use very short timeouts for testing (milliseconds)
    fast_recovery = 0.01  # 10ms
    slow_recovery = 0.02  # 20ms

    # Create two circuit breakers with different configurations
    cb1 = get_circuit_breaker(
        f"{TEST_CIRCUIT_NAME}_1",
        failure_threshold=2,
        recovery_timeout=slow_recovery,
        failure_window_seconds=0.1,  # Shorter window for test
    )

    cb2 = get_circuit_breaker(
        f"{TEST_CIRCUIT_NAME}_2",
        failure_threshold=3,
        recovery_timeout=fast_recovery,
        failure_window_seconds=0.1,  # Shorter window for test
    )

    # Trip first circuit breaker (needs 2 failures)
    for _ in range(2):
        cb1.record_failure()

    # Trip second circuit breaker (needs 3 failures)
    for _ in range(3):
        cb2.record_failure()

    # Verify both are open
    status1 = await get_circuit_status(f"{TEST_CIRCUIT_NAME}_1")
    status2 = await get_circuit_status(f"{TEST_CIRCUIT_NAME}_2")
    assert status1["state"] == "open"
    assert status2["state"] == "open"

    # Fast forward time for the faster circuit breaker to recover
    mock_time += fast_recovery * 1.1  # Just past the recovery time

    # First should still be open, second should be half-open
    status1 = await get_circuit_status(f"{TEST_CIRCUIT_NAME}_1")
    status2 = await get_circuit_status(f"{TEST_CIRCUIT_NAME}_2")
    assert status1["state"] == "open"
    assert status2["state"] == "half-open"

    # Fast forward time for the slower circuit breaker to recover
    mock_time += (slow_recovery - fast_recovery) * 1.1  # Just past the recovery time

    # Both should be in half-open now
    status1 = await get_circuit_status(f"{TEST_CIRCUIT_NAME}_1")
    status2 = await get_circuit_status(f"{TEST_CIRCUIT_NAME}_2")
    assert status1["state"] == "half-open"
    assert status2["state"] == "half-open"


async def test_sliding_window_failure_count():
    """Test that only failures within the sliding window are counted."""
    # Reset any existing circuit breaker
    reset_circuit_breaker("sliding_window_test")

    # Use a very short window for testing (50ms)
    window_seconds = 0.05

    # Create a circuit breaker with a short window
    circuit_breaker = get_circuit_breaker(
        "sliding_window_test",
        failure_threshold=3,  # Need 3 failures to trip
        recovery_timeout=0.1,  # Short recovery for test
        failure_window_seconds=window_seconds,
    )

    # Record 2 failures (below threshold)
    for _ in range(2):
        circuit_breaker.record_failure()

    # Check that we have 2 failures in the window
    status = await get_circuit_status("sliding_window_test")
    assert status["failures"] == 2
    assert status["state"] == "closed"

    # Wait for the window to expire (add small buffer)
    await asyncio.sleep(window_seconds * 1.2)

    # The failures should have expired from the window
    status = await get_circuit_status("sliding_window_test")
    assert status["failures"] == 0, "Failures should have expired from the window"

    # Record 2 more failures (should be the only ones in the new window)
    for _ in range(2):
        circuit_breaker.record_failure()

    # Should still be closed (only 2 failures in current window)
    status = await get_circuit_status("sliding_window_test")
    assert status["failures"] == 2
    assert status["state"] == "closed"

    # One more failure should trip the circuit
    circuit_breaker.record_failure()
    status = await get_circuit_status("sliding_window_test")
    assert status["state"] == "open"


async def test_circuit_breaker_error_handling():
    """Test error handling in circuit breaker operations."""
    # Test with invalid parameters
    with pytest.raises(ValueError, match="failure_threshold must be at least 1"):
        get_circuit_breaker("invalid", failure_threshold=0)

    with pytest.raises(ValueError, match="recovery_timeout must be greater than 0"):
        get_circuit_breaker("invalid", recovery_timeout=0)

    with pytest.raises(ValueError, match="half_open_max_attempts must be at least 1"):
        get_circuit_breaker("invalid", half_open_max_attempts=0)

    with pytest.raises(
        ValueError, match="failure_window_seconds must be greater than 0"
    ):
        get_circuit_breaker("invalid", failure_window_seconds=0)

    # Test with empty name - this will now raise a ValueError due to the validation in __post_init__
    with pytest.raises(ValueError, match="Circuit breaker must have a name"):
        CircuitBreaker("")


if __name__ == "__main__":
    # Run all tests with increased verbosity
    import sys

    sys.exit(
        pytest.main(
            [
                "-v",
                "--log-cli-level=INFO",
                "--cov=app.core.circuit_breaker",
                "--cov=app.core.health.circuit_breaker_check",
                "--cov-report=term-missing",
                __file__,
            ]
        )
    )
