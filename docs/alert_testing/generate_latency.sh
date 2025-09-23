#!/bin/bash
# Generate artificial latency for testing SLO alerts
# Usage: ./generate_latency.sh <latency_ms> <duration_sec>

set -e

LATENCY_MS=${1:-500}
DURATION=${2:-300}

# Check if curl is installed
if ! command -v curl &> /dev/null; then
    echo "Error: curl is required but not installed"
    exit 1
fi

echo "Generating $LATENCY_MS ms latency for $DURATION seconds..."

for ((i=0; i<DURATION; i++)); do
    # Generate random jitter (±10% of latency)
    JITTER=$((RANDOM % (LATENCY_MS / 5) - (LATENCY_MS / 10)))
    CURRENT_LATENCY=$((LATENCY_MS + JITTER))
    
    # Ensure latency is not negative
    if [ $CURRENT_LATENCY -lt 0 ]; then
        CURRENT_LATENCY=0
    fi
    
    # Call the test endpoint
    curl -s -o /dev/null \
         -H "Content-Type: application/json" \
         -X POST \
         -d "{\"delay_ms\": $CURRENT_LATENCY}" \
         http://localhost:8000/api/v1/test/latency
    
    # Random sleep between 0.5s and 1.5s to simulate variable traffic
    sleep 0.$((RANDOM % 10 + 5))
done

echo "Latency test completed"
