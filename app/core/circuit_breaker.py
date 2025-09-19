"""Minimal circuit breaker implementation for tests.

Provides a simple CircuitBreaker, error types, a retry decorator,
and global registry helpers as referenced by the test suite.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
import logging
from typing import Any, Callable, Dict, Optional, TypeVar

T = TypeVar("T")


class ServiceUnavailableError(RuntimeError):
    """Raised when a service call fails and should be treated as 503."""


class CircuitBreakerOpenError(RuntimeError):
    """Raised when the circuit breaker is open and calls are blocked."""


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    recovery_timeout: float = 60.0
    name: str = "default"

    def __post_init__(self) -> None:
        self._failure_count = 0
        self._state = "closed"  # closed | open | half-open
        self._opened_at: Optional[float] = None

    # Back-compat attributes accessed by tests
    @property
    def state(self) -> str:
        # Expose dynamic state considering timeout
        if self._state == "open" and self._opened_at is not None:
            if time.monotonic() - self._opened_at >= self.recovery_timeout:
                return "half-open"
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    @property
    def opened_at(self) -> Optional[float]:
        return self._opened_at

    def is_callable_allowed(self) -> bool:
        s = self.state
        if s == "closed":
            return True
        if s == "half-open":
            return True
        return False

    def _trip_open(self) -> None:
        self._state = "open"
        self._opened_at = time.monotonic()
        logging.getLogger(__name__).info("Circuit breaker '%s' is now OPEN", self.name)

    def _set_half_open(self) -> None:
        self._state = "half-open"
        logging.getLogger(__name__).info("Circuit breaker '%s' is now HALF-OPEN", self.name)

    def _close(self) -> None:
        self._state = "closed"
        self._failure_count = 0
        self._opened_at = None
        logging.getLogger(__name__).info("Circuit breaker '%s' is now CLOSED", self.name)

    def record_success(self) -> None:
        if self.state in ("half-open", "open"):
            self._close()
        else:
            self._failure_count = 0

    def record_failure(self) -> None:
        # If currently open and not yet half-open, do nothing extra
        if self.state == "open":
            return
        if self.state == "half-open":
            # Failure in half-open re-trips the circuit and counts as 1
            self._failure_count = max(1, self._failure_count)
            self._trip_open()
            return
        # Closed state: increase failure count
        self._failure_count += 1
        if self._failure_count >= self.failure_threshold:
            self._trip_open()

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs):
            # Transition to half-open if recovery time has passed
            if self._state == "open" and self._opened_at is not None:
                if time.monotonic() - self._opened_at >= self.recovery_timeout:
                    self._set_half_open()
            # Block if still open
            if self._state == "open":
                raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is OPEN")
            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except CircuitBreakerOpenError:
                raise
            except Exception as e:  # noqa: BLE001 - tests expect generic handling
                self.record_failure()
                # Wrap as service unavailable in half-open/closed
                raise ServiceUnavailableError(str(e))
        return wrapper


_registry: Dict[str, CircuitBreaker] = {}


# Global, test-visible breaker for database
DATABASE_CIRCUIT_BREAKER = CircuitBreaker(name="database", failure_threshold=5, recovery_timeout=30)
_registry[DATABASE_CIRCUIT_BREAKER.name] = DATABASE_CIRCUIT_BREAKER


def get_circuit_breaker(name: str) -> CircuitBreaker:
    if name in _registry:
        return _registry[name]
    cb = CircuitBreaker(name=name, failure_threshold=3, recovery_timeout=60)
    _registry[name] = cb
    return cb


def retry_with_circuit_breaker(
    breaker: CircuitBreaker,
    max_attempts: int = 3,
    initial_delay: float = 0.05,
    max_delay: float = 1.0,
):
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs):
            delay = initial_delay
            attempts = 0
            while True:
                attempts += 1
                try:
                    return breaker(func)(*args, **kwargs)
                except ServiceUnavailableError:
                    if attempts >= max_attempts:
                        raise
                    time.sleep(delay)
                    delay = min(max_delay, delay * 2)
        return wrapper
    return decorator
