#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Testing TLS Configuration ===${NC}"

# Check if psql is installed
if ! command -v psql &> /dev/null; then
    echo -e "${RED}Error: psql is not installed. Please install PostgreSQL client tools.${NC}"
    exit 1
fi

# Check if OpenSSL is installed
if ! command -v openssl &> /dev/null; then
    echo -e "${RED}Error: openssl is not installed.${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

# Check if containers are running
if ! docker ps | grep -q magflow_pgbouncer; then
    echo -e "${RED}Error: PgBouncer container is not running. Starting containers...${NC}"
    docker compose up -d

    # Wait for containers to start
    echo -e "${GREEN}Waiting for services to start...${NC}"
    sleep 10
fi

# Test 1: Verify PgBouncer is listening with TLS
echo -e "\n${GREEN}Test 1: Verify PgBouncer TLS port (6432) is open${NC}"
if nc -z localhost 6432; then
    echo -e "✓ PgBouncer is listening on port 6432"
else
    echo -e "${RED}✗ PgBouncer is not listening on port 6432${NC}"
    exit 1
fi

# Test 2: Test TLS connection to PgBouncer
echo -e "\n${GREEN}Test 2: Verify TLS handshake with PgBouncer${NC}"
if echo | openssl s_client -connect localhost:6432 -CAfile certs/ca/ca.crt -brief 2>&1 | grep -q 'Verification: OK'; then
    echo -e "✓ Successfully established TLS connection to PgBouncer"
else
    echo -e "${RED}✗ Failed to establish TLS connection to PgBouncer${NC}"
    echo -e "Troubleshooting tips:"
    echo -e "1. Check if PgBouncer is running: docker compose ps"
    echo -e "2. Check PgBouncer logs: docker compose logs pgbouncer"
    echo -e "3. Verify certificates are mounted: docker exec -it magflow_pgbouncer ls -la /etc/pgbouncer/certs/"
    exit 1
fi

# Test 3: Connect to PgBouncer using psql with SSL
echo -e "\n${GREEN}Test 3: Connect to PgBouncer using psql with SSL${NC}"
PGPASSWORD=app_password_change_me psql -h localhost -p 6432 -U app -d magflow -c "SELECT 'Successfully connected with SSL', ssl.pid, ssl.ssl, ssl.version FROM pg_stat_ssl ssl JOIN pg_stat_activity act ON ssl.pid = act.pid WHERE act.usename = 'app' AND act.application_name = 'psql'" 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Successfully connected to PgBouncer with SSL${NC}"
else
    echo -e "${RED}✗ Failed to connect to PgBouncer with SSL${NC}"
    exit 1
fi

# Test 4: Verify PostgreSQL is using TLS
echo -e "\n${GREEN}Test 4: Verify PostgreSQL is using TLS${NC}"
if docker exec -it magflow_pg psql -U app -d magflow -c "SELECT datname, usename, ssl, client_addr FROM pg_stat_ssl JOIN pg_stat_activity ON pg_stat_ssl.pid = pg_stat_activity.pid WHERE usename IS NOT NULL;" 2>&1 | grep -q "t"; then
    echo -e "✓ PostgreSQL is using TLS for connections"
else
    echo -e "${RED}✗ PostgreSQL is not using TLS for connections${NC}"
    exit 1
fi

echo -e "\n${GREEN}=== All TLS tests completed successfully! ===${NC}"
