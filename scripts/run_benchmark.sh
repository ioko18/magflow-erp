#!/bin/bash
set -e

# Configuration
CERT_DIR="./certs"
DB_USER=${DB_USER:-app}
DB_PASS=${DB_PASS:-app_password_change_me}
DB_NAME=${DB_NAME:-magflow}
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-6432}

# Generate certificates if they don't exist
if [ ! -f "$CERT_DIR/ca/ca.crt" ]; then
    echo "Generating certificates..."
    ./scripts/generate_certs.sh
fi

# Wait for PgBouncer to be ready
echo "Waiting for PgBouncer to be ready..."
until pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME; do
    sleep 1
done

# Test TLS connection
echo -e "\n=== Testing TLS Connection ==="
./scripts/test_pgbouncer_tls.py \
    --dsn "postgresql://$DB_USER:$DB_PASS@$DB_HOST:$DB_PORT/$DB_NAME?sslmode=verify-full&sslrootcert=$CERT_DIR/ca/ca.crt" \
    --ca-cert "$CERT_DIR/ca/ca.crt"

# Test prepared statements
echo -e "\n=== Testing Prepared Statements ==="
./scripts/test_pgbouncer_tls.py \
    --dsn "postgresql://$DB_USER:$DB_PASS@$DB_HOST:$DB_PORT/$DB_NAME?sslmode=verify-full&sslrootcert=$CERT_DIR/ca/ca.crt" \
    --ca-cert "$CERT_DIR/ca/ca.crt" \
    --test-prepared \
    --num-queries 20

# Run benchmark with prepared statements
echo -e "\n=== Running Benchmark with Prepared Statements ==="
python3 scripts/benchmark_pgbouncer.py \
    --dsn "postgresql://$DB_USER:$DB_PASS@$DB_HOST:$DB_PORT/$DB_NAME?sslmode=verify-full&sslrootcert=$CERT_DIR/ca/ca.crt" \
    --ssl-cert "$CERT_DIR/postgresql.crt" \
    --ssl-key "$CERT_DIR/private/postgresql.key" \
    --ssl-root-cert "$CERT_DIR/ca/ca.crt" \
    --threads 10 \
    --queries 1000

# Run benchmark without prepared statements
echo -e "\n=== Running Benchmark without Prepared Statements ==="
python3 scripts/benchmark_pgbouncer.py \
    --dsn "postgresql://$DB_USER:$DB_PASS@$DB_HOST:$DB_PORT/$DB_NAME?sslmode=verify-full&sslrootcert=$CERT_DIR/ca/ca.crt" \
    --ssl-cert "$CERT_DIR/postgresql.crt" \
    --ssl-key "$CERT_DIR/private/postgresql.key" \
    --ssl-root-cert "$CERT_DIR/ca/ca.crt" \
    --threads 10 \
    --queries 1000 \
    --no-ssl

echo -e "\n=== PgBouncer Stats ==="
PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d pgbouncer -c "SHOW STATS;"

echo -e "\n=== PgBouncer Pools ==="
PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d pgbouncer -c "SHOW POOLS;"

echo -e "\n=== Test completed successfully ==="
