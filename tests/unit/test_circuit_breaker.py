"""Tests for the circuit breaker implementation."""

from unittest.mock import patch

import pytest

from app.core.circuit_breaker import (
    DATABASE_CIRCUIT_BREAKER,
    CircuitBreaker,
    CircuitBreakerOpenError,
    ServiceUnavailableError,
    get_circuit_breaker,
)


# Helper function to get state as string
def get_state(cb):
    return str(cb._state).lower()


@pytest.fixture(autouse=True)
def reset_circuit_breaker_registry(monkeypatch):
    """Clear the global circuit breaker registry before each test."""
    # Use a fresh dictionary for the registry in each test
    monkeypatch.setattr("app.core.circuit_breaker._registry", {})


def test_circuit_breaker_initial_state():
    """Test that circuit breaker starts in closed state."""
    cb = CircuitBreaker(name="test")
    assert cb.is_callable_allowed() is True
    assert cb.state == "closed"


def test_circuit_breaker_trips_after_failures():
    """Test that circuit breaker trips after specified failures."""
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1, name="test")

    # First failure
    cb.record_failure()
    assert cb.is_callable_allowed() is True

    # Second failure should trip the circuit
    cb.record_failure()
    assert cb.is_callable_allowed() is False
    assert cb.state == "open"


@patch("app.core.circuit_breaker.time.monotonic")
@patch("app.core.circuit_breaker.threading.Timer")
def test_circuit_breaker_reset_after_timeout(mock_timer, mock_time):
    """Test that circuit breaker resets after recovery timeout."""
    # Set initial time
    mock_time.return_value = 0.0

    # Create circuit breaker with very short recovery timeout for testing
    cb = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=0.1,  # 100ms recovery timeout
        name="test_reset_timeout",
    )

    # Store the transition callback to call it later
    transition_callback = None

    class MockTimer:
        def __init__(self, interval, function, *args, **kwargs):
            nonlocal transition_callback
            transition_callback = function
            self.interval = interval
            self.function = function
            self.args = args or ()
            self.kwargs = kwargs or {}
            self.started = False
            self.daemon = False

        def start(self):
            self.started = True

    mock_timer.side_effect = MockTimer

    # Trip the circuit
    cb.record_failure()

    # Check that the circuit is open
    assert cb.state == "open"

    # Verify the timer was scheduled
    assert transition_callback is not None
    assert mock_timer.called

    # Fast forward just before recovery timeout (90ms)
    mock_time.return_value = 0.09

    # Timer should not have fired yet
    assert cb.state == "open"

    # Fast forward past recovery timeout (150ms)
    mock_time.return_value = 0.15

    # Manually trigger the timer callback to simulate the timer firing
    transition_callback()

    # Now the state should be half-open
    assert cb.state == "half-open"

    # Now check if call is allowed - should be allowed in half-open state
    assert cb.is_callable_allowed() is True


def test_circuit_breaker_decorator_success():
    """Test circuit breaker decorator with successful call."""
    cb = CircuitBreaker(name="test")

    @cb
    def mock_success() -> str:
        return "success"

    assert mock_success() == "success"
    assert cb.failure_count == 0  # Use property instead of private attribute
    assert cb.state == "closed"


def test_circuit_breaker_decorator_failure():
    """Test circuit breaker decorator with failing call."""
    cb = CircuitBreaker(failure_threshold=1, name="test")

    @cb
    def mock_failure() -> None:
        raise ValueError("test error")

    # First call should fail but not trip the circuit
    with pytest.raises(ServiceUnavailableError):
        mock_failure()

    # Circuit should be open now
    with pytest.raises(CircuitBreakerOpenError):
        mock_failure()

    # Reset for next test
    cb.record_success()


def test_retry_with_circuit_breaker():
    """Test retry decorator with circuit breaker."""
    from app.core.circuit_breaker import retry_with_circuit_breaker

    cb = CircuitBreaker(failure_threshold=2, name="test_retry")

    @retry_with_circuit_breaker(cb, max_attempts=2, initial_delay=0.01, max_delay=0.1)
    def mock_retry(should_fail: bool = True) -> str:
        if should_fail:
            raise ServiceUnavailableError("Temporary failure")
        return "success"

    # Should retry and then fail
    with pytest.raises(ServiceUnavailableError):
        mock_retry(should_fail=True)

    # Should succeed on first try
    assert mock_retry(should_fail=False) == "success"


def test_global_circuit_breakers():
    """Test that global circuit breakers are properly initialized."""
    assert DATABASE_CIRCUIT_BREAKER.name == "database"
    assert DATABASE_CIRCUIT_BREAKER.failure_threshold == 5
    assert DATABASE_CIRCUIT_BREAKER.recovery_timeout == 30


def test_get_circuit_breaker():
    """Test getting circuit breakers by service name."""
    # Test getting the database circuit breaker
    db_cb = get_circuit_breaker("database")
    assert db_cb.name == "database"
    assert db_cb.failure_threshold == 5
    assert db_cb.recovery_timeout == 30

    # Test creating a new circuit breaker
    new_cb = get_circuit_breaker("new_service")
    assert new_cb.name == "new_service"
    assert new_cb.failure_threshold == 3
    assert new_cb.recovery_timeout == 60.0


@patch("app.core.circuit_breaker.time.monotonic")
def test_circuit_breaker_logging(mock_time, caplog, reset_circuit_breaker_registry):
    """Test that circuit breaker logs state changes."""
    import logging

    # Setup mock time - start at 0
    mock_time.return_value = 0.0

    # Clear any existing log handlers to prevent duplicate output
    logger = logging.getLogger("app.core.circuit_breaker")
    logger.handlers.clear()

    # Set up basic logging to capture logs
    logging.basicConfig(level=logging.INFO)

    # Create circuit breaker with very short recovery timeout for testing
    cb = CircuitBreaker(
        name="test_logging",
        failure_threshold=1,
        recovery_timeout=0.1,  # 100ms recovery timeout
    )

    # Clear any existing logs
    caplog.clear()

    # 1. Test OPEN state logging
    with caplog.at_level(logging.INFO, logger="app.core.circuit_breaker"):
        # Record a failure to trip the circuit
        cb.record_failure()

        # Verify OPEN state was logged
        open_logs = [
            record for record in caplog.records if "is now OPEN" in record.message
        ]
        assert len(open_logs) > 0, "Expected log message for OPEN state not found"

    # Clear logs for next check
    caplog.clear()

    # Fast forward past recovery timeout (150ms)
    mock_time.return_value = 0.15

    # 2. Test HALF-OPEN state logging
    with caplog.at_level(logging.INFO, logger="app.core.circuit_breaker"):
        # This should transition to half-open
        cb.is_callable_allowed()

        # Verify HALF-OPEN state was logged
        half_open_logs = [
            record for record in caplog.records if "is now HALF-OPEN" in record.message
        ]
        assert (
            len(half_open_logs) > 0
        ), "Expected log message for HALF-OPEN state not found"

    # Clear logs for next check
    caplog.clear()

    # 3. Test CLOSED state logging
    with caplog.at_level(logging.INFO, logger="app.core.circuit_breaker"):
        # Record a success to close the circuit
        cb.record_success()

        # Verify CLOSED state was logged
        closed_logs = [
            record for record in caplog.records if "is now CLOSED" in record.message
        ]
        assert len(closed_logs) > 0, "Expected log message for CLOSED state not found"


@patch("app.core.circuit_breaker.time.monotonic")
def test_circuit_breaker_half_open_success(mock_time):
    """Test circuit breaker half-open state with successful call."""
    # Set up mock time
    mock_time.return_value = 0

    cb = CircuitBreaker(
        failure_threshold=1, recovery_timeout=10, name="test_half_open_success"
    )

    # Trip the circuit
    cb.record_failure()
    assert get_state(cb) == "open"

    # Fast forward past recovery timeout
    mock_time.return_value = 11

    # First call in half-open state should be allowed
    call_count = 0

    def mock_call():
        nonlocal call_count
        call_count += 1
        return "success"

    wrapped = cb(mock_call)
    result = wrapped()

    assert result == "success"
    assert call_count == 1
    assert get_state(cb) == "closed"
    assert cb.failure_count == 0


@patch("app.core.circuit_breaker.time.monotonic")
def test_circuit_breaker_half_open_failure(mock_time):
    """Test circuit breaker half-open state with failing call."""
    # Set up mock time
    mock_time.return_value = 0

    cb = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=10,
        name="test_half_open_fail",
    )

    # Trip the circuit
    cb.record_failure()
    assert get_state(cb) == "open"

    # Fast forward past recovery timeout
    mock_time.return_value = 11

    # Call in half-open state that fails
    def mock_call():
        raise ValueError("test error")

    wrapped = cb(mock_call)
    with pytest.raises(ServiceUnavailableError):
        wrapped()

    # Should trip back to open state
    assert get_state(cb) == "open"
    assert cb._opened_at is not None  # Should be reset to current time
