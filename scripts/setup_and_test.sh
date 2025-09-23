#!/bin/bash

# Exit on error
set -e

echo "=== Setting up MagFlow test environment ==="

# Check if in conda environment
if [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo "Error: Please activate the MagFlow conda environment first"
    echo "Run: conda activate MagFlow"
    exit 1
fi

# Install required packages
echo "\n=== Installing required packages ==="
pip install fastapi uvicorn httpx pytest

# Create test script
cat > test_health_endpoints.py << 'EOL'
"""Test script for health check endpoints."""
import asyncio
import sys
from fastapi.testclient import TestClient

# Add the app directory to the Python path
sys.path.append('.')

# Import app after setting up the path
from app.main import app

client = TestClient(app)

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
EOL

# Make the test script executable
chmod +x test_health_endpoints.py

echo "\n=== Running health check tests ==="
python test_health_endpoints.py

echo "\n=== Setup and testing complete! ==="
echo "You can now run the FastAPI server with: uvicorn app.main:app --reload"
