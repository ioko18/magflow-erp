#!/bin/bash
set -e

# Configuration
DURATION="1m"
USERS=100
SPAWN_RATE=10
PGBOUNCER_STATS_URL="http://pgbouncer:9628/metrics"
RESULTS_DIR="./load/results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "🚀 Starting performance test suite..."

# Create results directory
mkdir -p "$RESULTS_DIR"

# Function to run a single test scenario
run_test() {
    local name=$1
    local tags=$2
    local output_file="${RESULTS_DIR}/${TIMESTAMP}_${name}.json"
    
    echo "\n🔍 Running test: $name"
    echo "📊 Tags: $tags"
    
    # Get initial PgBouncer stats
    echo "📈 Collecting initial PgBouncer stats..."
    curl -s "$PGBOUNCER_STATS_URL" > "${output_file%.json}_pgbouncer_before.prom"
    
    # Run Locust
    echo "🏃 Running load test for $DURATION with $USERS users..."
    locust -f load/locustfile.py \
        --headless \
        --users $USERS \
        --spawn-rate $SPAWN_RATE \
        --run-time $DURATION \
        --tags $tags \
        --json \
        --host http://localhost:8000 \
        --csv "${output_file%.json}" \
        --html "${output_file%.json}.html"
    
    # Get final PgBouncer stats
    echo "📉 Collecting final PgBouncer stats..."
    curl -s "$PGBOUNCER_STATS_URL" > "${output_file%.json}_pgbouncer_after.prom"
    
    # Process results
    echo "\n📊 Test completed. Results saved to $output_file"
    echo "📈 P50/P95/P99 percentiles:"
    jq -r '["p50","p95","p99"] as $p | 
           ["Percentile","Value"] | @tsv, 
           ($p[] as $p | [$p, (.[] | select(.name=="Total") | .response_time_percentile_${p:1})] | @tsv)' \
       "${output_file%.json}_stats.json" | column -t
}

# Run tests with prepared statements on
echo "\n🔧 Configuring PgBouncer with prepared statements ON"
docker-compose exec -T pgbouncer psql -U pgbouncer -d pgbouncer -c "SET pgbouncer.pool_mode = 'transaction';"
docker-compose exec -T pgbouncer psql -U pgbouncer -d pgbouncer -c "SET pgbouncer.max_prepared_statements = 100;"

run_test "products_prepared_on" "products"
run_test "categories_prepared_on" "categories"
run_test "auth_prepared_on" "auth"

# Run tests with prepared statements off
echo "\n🔧 Configuring PgBouncer with prepared statements OFF"
docker-compose exec -T pgbouncer psql -U pgbouncer -d pgbouncer -c "SET pgbouncer.pool_mode = 'session';"
docker-compose exec -T pgbouncer psql -U pgbouncer -d pgbouncer -c "SET pgbouncer.max_prepared_statements = 0;"

run_test "products_prepared_off" "products"
run_test "categories_prepared_off" "categories"
run_test "auth_prepared_off" "auth"

echo "\n🎉 All tests completed! Results are in $RESULTS_DIR"
echo "Use 'make analyze-perf' to generate the performance report"
