"""Direct test for circuit breaker health check functionality."""

import asyncio

from app.core.circuit_breaker import get_circuit_breaker
from app.core.health.circuit_breaker_check import check_circuit_breakers


async def test_circuit_breaker_health():
    """Test the circuit breaker health check functionality directly."""
    print("Testing circuit breaker health check...")

    # Get the database circuit breaker
    db_circuit_breaker = get_circuit_breaker("database")

    # Test 1: Initial state (should be closed)
    print("\nTest 1: Initial state (should be closed)")
    status = await check_circuit_breakers()
    print("Health check response:", status)

    # Check circuit breaker status in response
    assert "metadata" in status, "Metadata not in response"
    assert "circuit_breakers" in status["metadata"], "Circuit breakers not in metadata"
    cb_status = status["metadata"]["circuit_breakers"]
    assert "database" in cb_status, "Database circuit breaker not in response"
    print(f"Database circuit breaker status: {cb_status['database']}")
    assert cb_status["database"]["state"] == "closed"

    # Test 2: Simulate failures to open the circuit
    print("\nTest 2: Simulating failures to open the circuit")
    for _ in range(db_circuit_breaker.failure_threshold + 1):
        db_circuit_breaker.record_failure()

    # Check status - should be open
    status = await check_circuit_breakers()
    cb_status = status["metadata"]["circuit_breakers"]
    print(f"After failures - Database circuit breaker status: {cb_status['database']}")
    assert cb_status["database"]["state"] == "open"

    # Test 3: Wait for circuit to go to half-open
    print("\nTest 3: Waiting for circuit to go to half-open state")
    wait_time = db_circuit_breaker.recovery_timeout + 1
    print(f"Waiting {wait_time} seconds for circuit to recover...")

    # Fast-forward time for testing
    import time

    original_sleep = time.sleep
    time.sleep = lambda x: None  # Monkey patch time.sleep

    # Check status - should be half-open after recovery timeout
    db_circuit_breaker._opened_at = time.time() - wait_time  # Fast-forward time
    status = await check_circuit_breakers()
    cb_status = status["metadata"]["circuit_breakers"]
    print(
        f"After recovery timeout - Database circuit breaker status: {cb_status['database']}",
    )
    assert cb_status["database"]["state"] == "half-open"

    # Test 4: Success should close the circuit
    print("\nTest 4: Simulating success to close the circuit")
    db_circuit_breaker.record_success()

    # Check status - should be closed
    status = await check_circuit_breakers()
    cb_status = status["metadata"]["circuit_breakers"]
    print(f"After success - Database circuit breaker status: {cb_status['database']}")
    assert cb_status["database"]["state"] == "closed"

    # Restore time.sleep
    time.sleep = original_sleep

    print("\n✅ All tests passed!")


if __name__ == "__main__":
    asyncio.run(test_circuit_breaker_health())
