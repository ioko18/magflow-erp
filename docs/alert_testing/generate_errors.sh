#!/bin/bash
# Generate errors for testing SLO alerts
# Usage: ./generate_errors.sh <error_percent> <duration_sec>

set -e

ERROR_PCT=${1:-1}  # Default to 1% errors
DURATION=${2:-300}  # Default to 5 minutes
REQUESTS_PER_SEC=10
TOTAL_REQUESTS=$((REQUESTS_PER_SEC * DURATION))

# Calculate error interval based on percentage
if (( $(echo "$ERROR_PCT > 0" | bc -l) )); then
    ERROR_EVERY=$(bc -l <<< "scale=2; 100/$ERROR_PCT")
    # Round to nearest integer
    ERROR_EVERY=$(printf "%.0f" "$ERROR_EVERY")
else
    ERROR_EVERY=0
fi

# Ensure ERROR_EVERY is at least 1 to avoid division by zero
if [ $ERROR_EVERY -lt 1 ]; then
    ERROR_EVERY=1
fi

# Check if curl is installed
if ! command -v curl &> /dev/null; then
    echo "Error: curl is required but not installed"
    exit 1
fi

echo "Generating $ERROR_PCT% errors ($ERROR_EVERY) for $DURATION seconds..."

for ((i=1; i<=TOTAL_REQUESTS; i++)); do
    # Generate error based on percentage
    if ((i % ERROR_EVERY == 0)); then
        # Generate different error types (400, 500, 503)
        ERROR_TYPE=$((RANDOM % 3))
        case $ERROR_TYPE in
            0) ENDPOINT="/api/v1/test/error/400" ;;
            1) ENDPOINT="/api/v1/test/error/500" ;;
            2) ENDPOINT="/api/v1/test/error/503" ;;
        esac
    else
        ENDPOINT="/api/v1/test/health"
    fi
    
    # Call the endpoint
    curl -s -o /dev/null -w "%{http_code} $ENDPOINT\n" \
         "http://localhost:8000${ENDPOINT}" &
    
    # Sleep to maintain request rate with some jitter
    sleep $(bc -l <<< "scale=3; (1/$REQUESTS_PER_SEC) + ($RANDOM%1000)/10000")
done

wait
echo "Error test completed"
