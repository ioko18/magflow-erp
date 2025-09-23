"""Test script for circuit breaker health check functionality."""

import asyncio
import time

from fastapi.testclient import TestClient

from app.core.circuit_breaker import get_circuit_breaker
from app.main import app

# Create a test client
client = TestClient(app)


async def test_circuit_breaker_health():
    """Test the circuit breaker health check functionality."""
    print("Testing circuit breaker health check...")

    # Get the database circuit breaker
    db_circuit_breaker = get_circuit_breaker("database")

    # Test 1: Initial state (should be closed)
    print("\nTest 1: Initial state (should be closed)")
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    print("Health check response:", data)

    # Check circuit breaker status in response
    assert (
        "circuit_breakers" in data["details"]
    ), "Circuit breaker status not in response"
    cb_status = data["details"]["circuit_breakers"]
    assert "database" in cb_status, "Database circuit breaker not in response"
    print(f"Database circuit breaker status: {cb_status['database']}")
    assert cb_status["database"]["state"] == "closed"

    # Test 2: Simulate failures to open the circuit
    print("\nTest 2: Simulating failures to open the circuit")
    for _ in range(db_circuit_breaker.failure_threshold + 1):
        db_circuit_breaker.record_failure()

    # Give it a moment to update
    await asyncio.sleep(0.1)

    # Check health again - should show open circuit
    response = client.get("/api/v1/health")
    data = response.json()
    cb_status = data["details"]["circuit_breakers"]
    print(f"After failures - Database circuit breaker status: {cb_status['database']}")
    assert cb_status["database"]["state"] == "open"

    # Test 3: Check readiness probe (should fail when circuit is open)
    print("\nTest 3: Checking readiness probe (should fail when circuit is open)")
    response = client.get("/api/v1/health/ready")
    print(f"Readiness status code: {response.status_code}")
    print(f"Readiness response: {response.json()}")
    assert response.status_code == 503  # Service Unavailable

    # Test 4: Wait for circuit to go to half-open
    print("\nTest 4: Waiting for circuit to go to half-open state")
    wait_time = db_circuit_breaker.recovery_timeout + 1
    print(f"Waiting {wait_time} seconds for circuit to recover...")
    await asyncio.sleep(wait_time)

    # Check health again - should be half-open
    response = client.get("/api/v1/health")
    data = response.json()
    cb_status = data["details"]["circuit_breakers"]
    print(
        f"After recovery timeout - Database circuit breaker status: {cb_status['database']}",
    )
    assert cb_status["database"]["state"] == "half-open"

    # Test 5: Success should close the circuit
    print("\nTest 5: Simulating success to close the circuit")
    db_circuit_breaker.record_success()

    # Check health again - should be closed
    response = client.get("/api/v1/health")
    data = response.json()
    cb_status = data["details"]["circuit_breakers"]
    print(f"After success - Database circuit breaker status: {cb_status['database']}")
    assert cb_status["database"]["state"] == "closed"

    print("\n✅ All tests passed!")


if __name__ == "__main__":
    import threading
    import time

    import uvicorn

    # Start the FastAPI server in a separate thread
    def run_server():
        uvicorn.run(app, host="0.0.0.0", port=8000)

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Give the server a moment to start
    time.sleep(2)

    # Run the tests
    try:
        asyncio.run(test_circuit_breaker_health())
    except Exception as e:
        print(f"❌ Test failed: {e!s}")
        raise
