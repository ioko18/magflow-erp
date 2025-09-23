#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

# Use curl to check the liveness endpoint
# We use the localhost address to avoid going through the load balancer
if curl -sSf http://localhost:8000/health/live > /dev/null; then
    # If liveness check passes, check readiness
    if curl -sSf http://localhost:8000/health/ready > /dev/null; then
        exit 0  # Both checks passed
    else
        echo "Readiness check failed"
        exit 1
    fi
else
    echo "Liveness check failed"
    exit 1
fi
