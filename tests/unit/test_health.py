"""Simple test script to verify health check endpoints.
This script can be run directly to test the health check functionality.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_health_endpoints():
    """Test all health check endpoints."""
    print("\n=== Testing Health Check Endpoints ===\n")

    # Test liveness probe
    print("1. Testing /health/live endpoint...")
    response = client.get("/api/v1/health/live")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    # Test readiness probe
    print("\n2. Testing /health/ready endpoint...")
    response = client.get("/api/v1/health/ready")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    # Test startup probe
    print("\n3. Testing /health/startup endpoint...")
    response = client.get("/api/v1/health/startup")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    # Test main health check
    print("\n4. Testing /health endpoint...")
    response = client.get("/api/v1/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")


if __name__ == "__main__":
    asyncio.run(test_health_endpoints())
