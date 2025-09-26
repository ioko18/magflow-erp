"""Circuit breaker health check."""

from typing import Any, Dict

from app.core.circuit_breaker import _registry


async def check_circuit_breakers() -> Dict[str, Any]:
    """Check the status of all circuit breakers."""
    circuit_breakers = {}

    # Check all registered circuit breakers
    for name, breaker in _registry.items():
        state = breaker.state
        status = "healthy" if state in ["closed", "half-open"] else "unhealthy"

        circuit_breakers[name] = {
            "status": status,
            "state": state,
            "failures": breaker.failure_count,
            "threshold": breaker.failure_threshold,
            "recovery_timeout": breaker.recovery_timeout,
            "opened_at": breaker.opened_at,
        }

    overall_status = "healthy"
    if any(cb.get("status") == "unhealthy" for cb in circuit_breakers.values()):
        overall_status = "unhealthy"

    return {
        "status": overall_status,
        "metadata": {
            "circuit_breakers": circuit_breakers,
        },
    }
