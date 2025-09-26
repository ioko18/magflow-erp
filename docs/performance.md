# Performance Testing Guide

This document provides guidance on running and interpreting performance tests for the MagFlow application.

## Test Scenarios

### 1. Product Listing

- **Endpoint**: `GET /products`
- **Parameters**: Search query, pagination cursor
- **Test Focus**: Read performance, search efficiency

### 2. Category Pagination

- **Endpoint**: `GET /categories`
- **Parameters**: Pagination cursor
- **Test Focus**: Pagination performance

### 3. Authentication

- **Endpoints**:
  - `POST /auth/login`
  - `POST /auth/refresh`
- **Test Focus**: Token generation and validation

## Running Tests

### Prerequisites

- Docker and Docker Compose
- Locust
- jq (for result processing)

### Running All Tests

```bash
chmod +x scripts/run_perf_test.sh
./scripts/run_perf_test.sh
```

### Running Specific Test

```bash
# Example: Run only product listing tests
./scripts/run_perf_test.sh products
```

## Interpreting Results

### Key Metrics

- **RPS (Requests Per Second)**: Throughput of the system
- **Response Times**:
  - p50 (median)
  - p95 (95th percentile)
  - p99 (99th percentile)
- **Error Rate**: Percentage of failed requests
- **PgBouncer Stats**:
  - Connection pool usage
  - Query timing
  - Prepared statement usage

### Performance Thresholds (CI)

| Metric              | Warning | Critical |
| ------------------- | ------- | -------- |
| p95 Response Time   | > 500ms | > 1000ms |
| Error Rate          | > 1%    | > 5%     |
| PgBouncer Wait Time | > 100ms | > 500ms  |

## PgBouncer Configuration

### Recommended Settings

```ini
[pgbouncer]
pool_mode = transaction
max_client_conn = 200
default_pool_size = 20
reserve_pool_size = 10
max_prepared_statements = 100
```

### Monitoring PgBouncer

```sql
-- Show pool statistics
SHOW POOLS;

-- Show prepared statements
SHOW PREPARED_STATEMENTS;

-- Show active queries
SHOW ACTIVE_SOCKETS;
```

## Performance Optimization Tips

1. **Database**

   - Ensure proper indexing on filtered/sorted columns
   - Monitor and adjust connection pool sizes
   - Consider read replicas for read-heavy workloads

1. **Application**

   - Use connection pooling effectively
   - Implement caching for frequently accessed data
   - Optimize database queries

1. **Infrastructure**

   - Monitor system resources (CPU, memory, I/O)
   - Consider horizontal scaling for API servers
   - Use a CDN for static assets

## Analyzing Results

### Example Output Analysis

```
Test: products_prepared_on
RPS: 245.6
p50: 45ms
p95: 120ms
p99: 210ms
Error Rate: 0.1%
```

### PgBouncer Metrics to Watch

- `pgbouncer_pool_client_wait_time`
- `pgbouncer_pool_query_time`
- `pgbouncer_pool_xact_count`
- `pgbouncer_pool_query_count`

## CI Integration

Add this to your CI pipeline to fail on performance regressions:

```yaml
- name: Run Performance Tests
  run: |
    ./scripts/run_perf_test.sh
    ./scripts/check_perf_thresholds.py \
      --p95 500 \
      --error-rate 1 \
      --results-dir ./load/results
```
