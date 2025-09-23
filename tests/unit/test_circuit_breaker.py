"""Tests for the circuit breaker implementation."""

import time
from unittest.mock import patch

import pytest

from app.core.circuit_breaker import (
    DATABASE_CIRCUIT_BREAKER,
    CircuitBreaker,
    CircuitBreakerOpenError,
    ServiceUnavailableError,
    get_circuit_breaker,
)


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


def test_circuit_breaker_reset_after_timeout():
    """Test that circuit breaker resets after recovery timeout."""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1, name="test")

    # Trip the circuit
    cb.record_failure()
    assert cb.state == "open"

    # Wait for recovery timeout
    time.sleep(0.2)

    # Should be in half-open state now
    assert cb.state == "half-open"
    assert cb.is_callable_allowed() is True


def test_circuit_breaker_decorator_success():
    """Test circuit breaker decorator with successful call."""
    cb = CircuitBreaker(name="test")

    @cb
    def mock_success() -> str:
        return "success"

    assert mock_success() == "success"
    assert cb._failure_count == 0
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
    # Test existing circuit breakers
    assert get_circuit_breaker("database") == DATABASE_CIRCUIT_BREAKER

    # Test creating a new circuit breaker
    new_cb = get_circuit_breaker("new_service")
    assert new_cb.name == "new_service"
    assert new_cb.failure_threshold == 3
    assert new_cb.recovery_timeout == 60


def test_circuit_breaker_logging(caplog):
    """Test that circuit breaker logs state changes."""
    import logging

    logging.basicConfig(level=logging.INFO)

    with caplog.at_level(logging.INFO):
        cb = CircuitBreaker(
            name="test_logging",
            failure_threshold=1,
            recovery_timeout=0.1,
        )

        # Should log when tripping
        cb.record_failure()
        assert "Circuit breaker 'test_logging' is now OPEN" in caplog.text

        # Should log when resetting to half-open
        time.sleep(0.2)  # Ensure recovery timeout passes
        cb.is_callable_allowed()  # This should reset to half-open
        assert "Circuit breaker 'test_logging' is now HALF-OPEN" in caplog.text

        # Should log when closing
        cb.record_success()
        assert "Circuit breaker 'test_logging' is now CLOSED" in caplog.text


@patch("app.core.circuit_breaker.time.monotonic")
def test_circuit_breaker_half_open_success(mock_time):
    """Test circuit breaker half-open state with successful call."""
    # Set up mock time
    mock_time.return_value = 0

    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10, name="test_half_open")

    # Trip the circuit
    cb.record_failure()
    assert cb._state == "open"

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
    assert cb.state == "closed"
    assert cb._failure_count == 0


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
    assert cb._state == "open"

    # Fast forward past recovery timeout
    mock_time.return_value = 11

    # First call in half-open state fails
    def mock_call():
        raise ValueError("test error")

    wrapped = cb(mock_call)

    with pytest.raises(ServiceUnavailableError):
        wrapped()

    # Should trip back to open state
    assert cb.state == "open"
    # In half-open state, we don't increment failures on trip
    assert cb._failure_count == 1
    assert cb._opened_at is not None  # Should be reset to current time
