"""Circuit breaker health check."""

from typing import Any, Dict

from app.core.circuit_breaker import _registry


def check_circuit_breakers() -> Dict[str, Any]:
    """Check the status of all circuit breakers."""
    circuit_breakers = {}

    # Check all registered circuit breakers
    for name, breaker in _registry.items():
        circuit_breakers[name] = {
            "status": (
                "healthy" if breaker.state in ["closed", "half-open"] else "unhealthy"
            ),
            "state": breaker.state,
            "failures": breaker.failure_count,
            "threshold": breaker.failure_threshold,
            "recovery_timeout": breaker.recovery_timeout,
            "opened_at": breaker.opened_at,
        }

    return {
        "status": "healthy",
        "metadata": {
            "circuit_breakers": circuit_breakers,
        },
    }
