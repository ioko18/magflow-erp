#!/bin/bash

# Exit on error
set -e

echo "=== Setting up test environment ==="

# Check if in conda environment
if [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo "Error: Please activate the MagFlow conda environment first"
    echo "Run: conda activate MagFlow"
    exit 1
fi

# Install required packages
echo "\n=== Installing required packages ==="
pip install fastapi uvicorn httpx pytest pytest-asyncio

echo "\n=== Test environment setup complete! ==="
echo "You can now run the health check tests with: python run_health_checks.py"
