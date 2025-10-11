"""Advanced circuit breaker implementation with thread safety and metrics.

This module provides a robust circuit breaker pattern implementation that helps
build resilient applications by gracefully handling failures in distributed systems.

Key Features:
- Thread-safe operations
- Configurable failure thresholds and recovery timeouts
- Support for half-open state for gradual recovery
- Built-in metrics and monitoring
- Decorator-based API for easy integration
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

# datetime imports removed as they're not used
from enum import Enum
from functools import wraps
from typing import Any, TypeVar

from prometheus_client import Counter, Gauge, Histogram

# Set up logging
_logger = logging.getLogger(__name__)

T = TypeVar("T")

# Prometheus metrics
# Using a separate gauge for each state to work with older prometheus_client versions
CIRCUIT_STATE_CLOSED = Gauge(
    "circuit_breaker_state_closed",
    "Circuit breaker is in CLOSED state (1) or not (0)",
    ["circuit_name"],
)
CIRCUIT_STATE_OPEN = Gauge(
    "circuit_breaker_state_open",
    "Circuit breaker is in OPEN state (1) or not (0)",
    ["circuit_name"],
)
CIRCUIT_STATE_HALF_OPEN = Gauge(
    "circuit_breaker_state_half_open",
    "Circuit breaker is in HALF_OPEN state (1) or not (0)",
    ["circuit_name"],
)
CIRCUIT_TRIPS = Counter(
    "circuit_breaker_trips_total",
    "Total number of times the circuit breaker has tripped to OPEN state",
    ["circuit_name"],
)
CIRCUIT_FAILURES = Counter(
    "circuit_breaker_failures_total",
    "Total number of failures in the circuit",
    ["circuit_name"],
)
CIRCUIT_RECOVERIES = Counter(
    "circuit_breaker_recoveries_total",
    "Number of successful circuit recoveries",
    ["circuit_name"],
)
CIRCUIT_LATENCY = Histogram(
    "circuit_breaker_latency_seconds",
    "Latency of circuit breaker operations",
    ["circuit_name", "operation"],
)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half-open"

    def __str__(self):
        return self.value


class CircuitBreakerError(Exception):
    """Base class for circuit breaker errors."""


class ServiceUnavailableError(CircuitBreakerError):
    """Raised when a service call fails and should be treated as 503."""


class CircuitBreakerOpenError(CircuitBreakerError):
    """Raised when the circuit breaker is open and calls are blocked."""


@dataclass
class CircuitBreaker:
    """Circuit breaker implementation with thread safety and metrics.

    Args:
        name: Unique name for the circuit breaker
        failure_threshold: Number of failures before opening the circuit
        recovery_timeout: Time in seconds before attempting to close the circuit
        half_open_max_attempts: Maximum number of attempts in half-open state
    """

    name: str
    failure_threshold: int = 3
    recovery_timeout: float = 60.0
    half_open_max_attempts: int = 1
    failure_window_seconds: float = 60.0  # Time window in seconds to track failures
    _state: CircuitState = field(init=False, default=CircuitState.CLOSED)
    _failure_timestamps: deque[float] = field(init=False, default_factory=deque)
    _half_open_attempts: int = field(init=False, default=0)
    _lock: threading.RLock = field(init=False, default_factory=threading.RLock)
    _opened_at: float | None = field(init=False, default=None)
    _half_open_timer: threading.Timer | None = field(init=False, default=None)
    _logger: logging.Logger = field(
        init=False, default_factory=lambda: logging.getLogger(__name__)
    )

    def __post_init__(self) -> None:
        """Initialize the circuit breaker with default values and validation."""
        if not self.name:
            raise ValueError("Circuit breaker must have a name")
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if self.recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be greater than 0")
        if self.half_open_max_attempts < 1:
            raise ValueError("half_open_max_attempts must be at least 1")
        if self.failure_window_seconds <= 0:
            raise ValueError("failure_window_seconds must be greater than 0")

    def _update_metrics(self) -> None:
        """Update Prometheus metrics with current state."""
        # Reset all states to 0 first
        CIRCUIT_STATE_CLOSED.labels(circuit_name=self.name).set(0)
        CIRCUIT_STATE_OPEN.labels(circuit_name=self.name).set(0)
        CIRCUIT_STATE_HALF_OPEN.labels(circuit_name=self.name).set(0)

        # Set current state to 1
        if self._state == CircuitState.CLOSED:
            CIRCUIT_STATE_CLOSED.labels(circuit_name=self.name).set(1)
        elif self._state == CircuitState.OPEN:
            CIRCUIT_STATE_OPEN.labels(circuit_name=self.name).set(1)
        elif self._state == CircuitState.HALF_OPEN:
            CIRCUIT_STATE_HALF_OPEN.labels(circuit_name=self.name).set(1)

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Allow the circuit breaker to be used as a decorator.

        Args:
            func: The function to wrap with circuit breaker logic

        Returns:
            A wrapped function that applies circuit breaker logic
        """

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            if not self.is_callable_allowed():
                self._logger.warning(
                    "Circuit breaker '%s' is %s. Blocking call to %s",
                    self.name,
                    self.state,
                    func.__name__,
                )
                raise CircuitBreakerOpenError(f"Circuit '{self.name}' is {self.state}")

            try:
                with CIRCUIT_LATENCY.labels(
                    circuit_name=self.name, operation=func.__name__
                ).time():
                    result = func(*args, **kwargs)

                # Record success for all states to handle half-open state properly
                self.record_success()

                return result

            except Exception as ex:
                # Record the failure and re-raise the appropriate exception
                self.record_failure()
                if isinstance(ex, (CircuitBreakerError, KeyboardInterrupt, SystemExit)):
                    raise
                raise ServiceUnavailableError(f"Service call failed: {str(ex)}") from ex

        return wrapper

    @property
    def state(self) -> str:
        """Get the current state of the circuit breaker.

        Returns:
            str: Current state as a lowercase string ('closed', 'open', or 'half-open')
        """
        with self._lock:
            self._check_and_transition_state()
            return str(self._state)

    @property
    def failure_count(self) -> int:
        """Get the current failure count within the sliding window."""
        with self._lock:
            self._check_and_transition_state()  # Ensure state is up to date
            self._clean_old_failures()
            return len(self._failure_timestamps)

    @property
    def opened_at(self) -> float | None:
        """Get the timestamp when the circuit was opened."""
        with self._lock:
            return self._opened_at

    def is_callable_allowed(self) -> bool:
        """Check if a call is allowed in the current state.

        Returns:
            bool: True if calls are allowed, False otherwise
        """
        with self._lock:
            # First check if we need to transition states
            self._check_and_transition_state()

            if self._state == CircuitState.OPEN:
                self._logger.debug("Circuit '%s' is OPEN - call blocked", self.name)
                return False

            if self._state == CircuitState.HALF_OPEN:
                return self._handle_half_open_state()

            # Default case: CLOSED state
            self._logger.debug("Circuit '%s' is CLOSED - call allowed", self.name)
            return True

    def _handle_half_open_state(self) -> bool:
        """Handle the HALF_OPEN state logic.

        Returns:
            bool: True if the call is allowed, False otherwise
        """
        # In half-open state, we allow a limited number of test calls
        if self._half_open_attempts >= self.half_open_max_attempts:
            # If we've reached max attempts, trip back to OPEN
            self._logger.warning(
                "Circuit '%s' HALF-OPEN max attempts reached, tripping to OPEN",
                self.name,
            )
            self._trip_open()
            return False

        # Don't increment attempts here, only after a successful call
        self._logger.debug(
            "Circuit '%s' is HALF-OPEN - call allowed (attempt %d/%d)",
            self.name,
            self._half_open_attempts + 1,  # Show next attempt number
            self.half_open_max_attempts,
        )
        return True

    def _check_and_transition_state(self) -> None:
        """Check and transition state based on current conditions."""
        with self._lock:
            current_time = time.monotonic()

            # Clean up old failures before checking state transitions
            self._clean_old_failures()

            # Check if we should transition from OPEN to HALF_OPEN
            if self._state == CircuitState.OPEN:
                if (
                    self._opened_at is not None
                    and current_time - self._opened_at >= self.recovery_timeout
                ):
                    self._set_half_open()

            # Check if we should transition from HALF_OPEN to CLOSED or re-OPEN
            elif self._state == CircuitState.HALF_OPEN:
                # In half-open state, check if we've exceeded max attempts
                if self._half_open_attempts >= self.half_open_max_attempts:
                    self._logger.debug(
                        "Circuit breaker '%s' exceeded max half-open attempts (%d), reopening circuit",
                        self.name,
                        self.half_open_max_attempts,
                    )
                    self._trip_open()
                # Check if we've been in half-open state too long
                elif self._opened_at is not None and (
                    current_time - self._opened_at
                ) >= (self.recovery_timeout * 2):
                    self._logger.debug(
                        "Circuit breaker '%s' in HALF-OPEN state too long (%.2fs), reopening circuit",
                        self.name,
                        current_time - self._opened_at,
                    )
                    self._trip_open()

            # Check if we should transition from CLOSED to OPEN
            elif (
                self._state == CircuitState.CLOSED
                and len(self._failure_timestamps) >= self.failure_threshold
            ):
                self._trip_open()

    def _trip_open(self) -> None:
        """Transition to the OPEN state."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                # Already in OPEN state
                return

            previous_state = self._state
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()
            self._schedule_half_open_transition()

            # Log the transition - match the expected format in tests
            self._logger.warning(
                "Circuit breaker '%s' is now OPEN (failures: %d, threshold: %d)",
                self.name,
                len(self._failure_timestamps),
                self.failure_threshold,
            )

            # Update metrics
            self._update_metrics()
            CIRCUIT_TRIPS.labels(circuit_name=self.name).inc()

            # Emit state change event
            self._emit_state_change_event(previous_state, CircuitState.OPEN)

    def _set_half_open(self) -> None:
        """Transition to the HALF_OPEN state."""
        with self._lock:
            if self._state != CircuitState.OPEN:
                # Only transition to HALF_OPEN from OPEN state
                return

            previous_state = self._state
            self._state = CircuitState.HALF_OPEN
            self._half_open_attempts = 0
            self._opened_at = None  # Clear the opened_at timestamp

            self._logger.info(
                "Circuit breaker '%s' is now HALF-OPEN (previous state: %s)",
                self.name,
                previous_state.value.upper(),
            )

            # Update metrics
            self._update_metrics()

            # Emit state change event
            self._emit_state_change_event(previous_state, CircuitState.HALF_OPEN)

    def _emit_state_change_event(
        self, from_state: CircuitState, to_state: CircuitState
    ) -> None:
        """Emit a state change event.

        Args:
            from_state: The previous state of the circuit breaker
            to_state: The new state of the circuit breaker
        """
        # This is a no-op implementation that can be overridden by subclasses
        # or extended with event emission logic
        self._logger.debug(
            "Circuit breaker '%s' state changed: %s -> %s",
            self.name,
            from_state.value.upper(),
            to_state.value.upper(),
        )

    def _close(self) -> None:
        """Transition to the CLOSED state."""
        with self._lock:
            if self._state == CircuitState.CLOSED:
                # Already in CLOSED state
                return

            previous_state = self._state
            self._state = CircuitState.CLOSED
            self._failure_timestamps.clear()
            self._half_open_attempts = 0
            self._opened_at = None
            self._cancel_half_open_timer()

            self._logger.info(
                "Circuit breaker '%s' is now CLOSED (previous state: %s)",
                self.name,
                previous_state.value.upper(),
            )

            # Update metrics
            self._update_metrics()
            CIRCUIT_RECOVERIES.labels(circuit_name=self.name).inc()

            # Emit state change event
            self._emit_state_change_event(previous_state, CircuitState.CLOSED)

    def _clean_old_failures(self) -> None:
        """Remove failures that are outside the sliding window."""
        if not self._failure_timestamps:
            return

        current_time = time.monotonic()
        cutoff_time = current_time - self.failure_window_seconds

        # Remove all failures older than the window
        while self._failure_timestamps and self._failure_timestamps[0] < cutoff_time:
            self._failure_timestamps.popleft()

    def _cancel_half_open_timer(self) -> None:
        """Cancel the half-open timer if it's running."""
        if self._half_open_timer is not None:
            self._half_open_timer.cancel()
            self._half_open_timer = None

    def record_success(self) -> None:
        """Record a successful call and update the circuit state if needed."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                # In half-open state, a success means we can close the circuit
                # First increment the attempt counter
                self._half_open_attempts += 1
                self._logger.debug(
                    "Circuit '%s' HALF-OPEN attempt %d/%d succeeded",
                    self.name,
                    self._half_open_attempts,
                    self.half_open_max_attempts,
                )

                # Then transition to CLOSED state
                self._close()

            elif self._state == CircuitState.CLOSED and self._failure_timestamps:
                # In closed state, clear old failures on success
                prev_failures = len(self._failure_timestamps)
                self._failure_timestamps.clear()
                self._update_metrics()
                self._logger.debug(
                    "Circuit '%s' failure count reset after success (was: %d)",
                    self.name,
                    prev_failures,
                )
            elif self._state == CircuitState.OPEN:
                # If we get a success in OPEN state, transition to HALF_OPEN
                self._set_half_open()
                self._logger.debug(
                    "Circuit '%s' received success in OPEN state, transitioning to HALF-OPEN",
                    self.name,
                )

    def record_failure(self) -> None:
        """Record a failed call and update the circuit state if needed."""
        with self._lock:
            CIRCUIT_FAILURES.labels(circuit_name=self.name).inc()
            current_time = time.monotonic()

            # Add the current failure timestamp
            self._failure_timestamps.append(current_time)
            self._clean_old_failures()

            if self._state == CircuitState.HALF_OPEN:
                # In half-open state, any failure should re-trip the circuit
                self._logger.warning(
                    "Circuit breaker '%s' HALF-OPEN attempt failed (attempt %d/%d)",
                    self.name,
                    self._half_open_attempts,
                    self.half_open_max_attempts,
                )
                self._trip_open()
            elif self._state == CircuitState.CLOSED:
                # Check if we've exceeded the failure threshold within the window
                failure_count = len(self._failure_timestamps)
                if failure_count >= self.failure_threshold:
                    self._logger.warning(
                        "Circuit breaker '%s' failure threshold reached (%d >= %d) in the last %.1fs",
                        self.name,
                        failure_count,
                        self.failure_threshold,
                        self.failure_window_seconds,
                    )
                    self._trip_open()
                else:
                    self._logger.debug(
                        "Circuit breaker '%s' failure recorded (%d/%d) in the last %.1fs",
                        self.name,
                        failure_count,
                        self.failure_threshold,
                        self.failure_window_seconds,
                    )
            else:  # OPEN state
                # In OPEN state, just log the failure but don't trip again
                self._logger.debug(
                    "Circuit breaker '%s' failure recorded while OPEN (total failures in window: %d)",
                    self.name,
                    len(self._failure_timestamps),
                )

    def _cancel_half_open_timer(self) -> None:
        """Cancel any scheduled half-open transition timer."""
        if self._half_open_timer is not None:
            self._half_open_timer.cancel()
            self._half_open_timer = None

    def _schedule_half_open_transition(self) -> None:
        """Schedule transition to HALF_OPEN state after the recovery timeout."""
        self._cancel_half_open_timer()

        def _transition() -> None:
            with self._lock:
                if self._state == CircuitState.OPEN:
                    self._set_half_open()
                self._half_open_timer = None

        timer = threading.Timer(self.recovery_timeout, _transition)
        timer.daemon = True
        timer.start()
        self._half_open_timer = timer


# Global registry for circuit breakers
_registry: dict[str, CircuitBreaker] = {}
_registry_lock = threading.RLock()

# Global, test-visible breaker for database
DATABASE_CIRCUIT_BREAKER = CircuitBreaker(
    name="database",
    failure_threshold=5,
    recovery_timeout=30,
)
with _registry_lock:
    _registry[DATABASE_CIRCUIT_BREAKER.name] = DATABASE_CIRCUIT_BREAKER


def get_circuit_breaker(name: str, **kwargs: Any) -> CircuitBreaker:
    """Get or create a circuit breaker by name.

    Args:
        name: The name of the circuit breaker
        **kwargs: Additional arguments to pass to CircuitBreaker constructor

    Returns:
        An existing or new CircuitBreaker instance
    """
    with _registry_lock:
        # Special case for database circuit breaker to maintain backward compatibility
        if name == "database" and name not in _registry:
            _logger.debug(
                f"Returning global DATABASE_CIRCUIT_BREAKER instance: {id(DATABASE_CIRCUIT_BREAKER)}"
            )
            return DATABASE_CIRCUIT_BREAKER

        if name in _registry:
            cb = _registry[name]
            _logger.debug(
                f"Returning existing circuit breaker '{name}': {id(cb)}, state: {cb._state}"
            )
            return cb

        # Create new circuit breaker with provided or default parameters
        cb = CircuitBreaker(
            name=name,
            failure_threshold=kwargs.get("failure_threshold", 3),
            recovery_timeout=kwargs.get("recovery_timeout", 60.0),
            half_open_max_attempts=kwargs.get("half_open_max_attempts", 1),
            failure_window_seconds=kwargs.get("failure_window_seconds", 60.0),
        )
        _logger.debug(
            f"Created new circuit breaker '{name}': {id(cb)}, state: {cb._state}"
        )
        _registry[name] = cb
        return cb


def retry_with_circuit_breaker(
    breaker: CircuitBreaker,
    max_attempts: int = 3,
    initial_delay: float = 0.05,
    max_delay: float = 1.0,
    jitter: float = 0.1,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorate a function with retry and circuit breaker logic.

    Args:
        breaker: The circuit breaker to use
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        jitter: Random jitter factor (0-1) to add to delays

    Returns:
        A decorator that adds retry and circuit breaker logic to a function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            delay = initial_delay

            for attempt in range(1, max_attempts + 1):
                try:
                    # Check if the circuit breaker allows the call
                    if not breaker.is_callable_allowed():
                        raise CircuitBreakerOpenError(
                            f"Circuit '{breaker.name}' is open"
                        )

                    result = func(*args, **kwargs)

                    # If we get here, the call was successful
                    if breaker._state == CircuitState.HALF_OPEN:
                        breaker.record_success()

                    return result

                except Exception as ex:
                    last_exception = ex

                    # Don't retry for circuit breaker errors
                    if isinstance(ex, CircuitBreakerOpenError):
                        raise

                    # Log the attempt
                    _logger.warning(
                        "Attempt %d/%d failed: %s",
                        attempt,
                        max_attempts,
                        str(ex),
                        exc_info=_logger.isEnabledFor(logging.DEBUG),
                    )

                    # If this is the last attempt, re-raise the exception
                    if attempt == max_attempts:
                        break

                    # Calculate next delay with exponential backoff and jitter
                    delay = min(max_delay, delay * 2)
                    if jitter > 0:
                        import random

                        delay = delay * (1 + random.uniform(-jitter, jitter))

                    # Sleep before retry
                    time.sleep(delay)

            # If we get here, all attempts failed
            if isinstance(last_exception, Exception):
                # Record the failure in the circuit breaker
                breaker.record_failure()

                # Convert to ServiceUnavailableError if not already a CircuitBreakerError
                if not isinstance(last_exception, CircuitBreakerError):
                    last_exception = ServiceUnavailableError(
                        f"Service call failed after {max_attempts} attempts: {str(last_exception)}"
                    )

                raise last_exception

            # This should never happen, but just in case
            raise ServiceUnavailableError("Service call failed with no exception")

        return wrapper

    return decorator
