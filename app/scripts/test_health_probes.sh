#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to test an endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local expected_status=$3
    
    echo -n "Testing $name ($url)... "
    status_code=$(curl --silent --output /dev/null --write-out "%{http_code}" $url)
    
    if [ "$status_code" -eq "$expected_status" ]; then
        echo -e "${GREEN}PASS${NC} (Status: $status_code)"
        return 0
    else
        echo -e "${RED}FAIL${NC} (Expected: $expected_status, Got: $status_code)"
        return 1
    fi
}

# Test local endpoints
echo "Testing local health endpoints..."
test_endpoint "Liveness" "http://localhost:8000/api/v1/health/live" 200
test_endpoint "Readiness" "http://localhost:8000/api/v1/health/ready" 200
test_endpoint "Startup" "http://localhost:8000/api/v1/health/startup" 200

# Test with simulated failures
echo -e "\n=== Simulating database failure ==="

# Check current database status
echo -e "\n[1/7] Current database containers:"
docker ps -a | grep -E 'db|postgres|pgbouncer'

# Get the actual database container name
DB_CONTAINER=$(docker ps -a --format '{{.Names}}' | grep -E 'db|postgres|pgbouncer' | head -1)

if [ -z "$DB_CONTAINER" ]; then
    echo "ERROR: Could not find database container. Available containers:"
    docker ps -a
    exit 1
fi

echo -e "\n[2/7] Found database container: $DB_CONTAINER"

# Check database connectivity before stopping
echo -e "\n[3/7] Checking database connectivity before stopping..."
docker exec $DB_CONTAINER pg_isready || echo "Database is already down"

# Stop the database service
echo -e "\n[4/7] Stopping database container: $DB_CONTAINER"
docker stop $DB_CONTAINER

# Wait a moment for the database to be fully stopped
echo -e "\n[5/7] Waiting for database to stop..."
sleep 5

# Verify database is stopped
echo -e "\n[6/7] Database container status after stop:"
docker ps -a | grep -E 'db|postgres|pgbouncer' || echo "Database container not found"

# Check if we can still connect to the database (should fail)
echo -e "\n[7/7] Verifying database is unreachable..."
if docker exec $DB_CONTAINER pg_isready 2>/dev/null; then
    echo "ERROR: Database is still accessible after stopping container!"
    exit 1
else
    echo "Database is successfully stopped"
fi

# Test direct connection to database port
echo -e "\nTesting direct database connection on port 5432..."
if nc -z localhost 5432; then
    echo "WARNING: Port 5432 is still accepting connections!"
    echo "This might be due to another PostgreSQL instance running on your host."
    echo "Please make sure no other database is running on port 5432."
    exit 1
else
    echo "Port 5432 is closed as expected"
fi

# Clear the application's connection pool
echo -e "\nClearing application connection pool..."
curl -v -X POST http://localhost:8000/api/v1/health/clear-pool || echo "Failed to clear connection pool (expected if database is down)"

# Test the readiness endpoint with a direct curl to see the full response
echo -e "\nTesting readiness endpoint with database down..."
curl -v http://localhost:8000/api/v1/health/ready

# Run the test with retries
MAX_RETRIES=5
RETRY_DELAY=2
for i in $(seq 1 $MAX_RETRIES); do
    echo -e "\nTest attempt $i of $MAX_RETRIES..."
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health/ready | grep -q 503; then
        echo "Database is down as expected"
        break
    else
        echo "Database still appears to be up, waiting $RETRY_DELAY seconds..."
        if [ $i -eq $MAX_RETRIES ]; then
            echo "ERROR: Database health check did not fail after $MAX_RETRIES attempts"
            exit 1
        fi
        sleep $RETRY_DELAY
    fi
done

test_endpoint "Readiness (DB down)" "http://localhost:8000/api/v1/health/ready" 503

# Restore database connection
echo -e "\nRestoring database connection..."
docker compose start db

# Wait for database to be fully up
sleep 10

# Verify recovery
echo -e "\nVerifying recovery..."
# Give time for the application to detect the database is back
max_retries=10
count=0
while [ $count -lt $max_retries ]; do
    if curl -s http://localhost:8000/api/v1/health/ready | grep -q '"status":"ready"'; then
        break
    fi
    count=$((count + 1))
    sleep 5
    echo "Waiting for service to recover... (attempt $count/$max_retries)"
done

test_endpoint "Readiness (recovered)" "http://localhost:8000/api/v1/health/ready" 200

echo -e "\nHealth probe testing complete."
