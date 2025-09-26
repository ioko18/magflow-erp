# Security Configuration

## Database Timeouts

This document outlines the database timeout configurations for the MagFlow application. These settings are designed to prevent long-running transactions and idle connections that could impact database performance.

### Timeout Settings

#### 1. Statement Timeout (30 seconds)

```sql
ALTER ROLE app IN DATABASE magflow SET statement_timeout = '30s';
```

- **Purpose**: Automatically cancels any query that runs longer than 30 seconds.
- **Impact**: Prevents long-running queries from consuming database resources.
- **When to adjust**:
  - For complex reporting queries that require more time
  - During data migrations or batch operations

#### 2. Idle Transaction Timeout (2 minutes)

```sql
ALTER ROLE app IN DATABASE magflow SET idle_in_transaction_session_timeout = '120s';
```

- **Purpose**: Terminates any transaction that has been idle for more than 2 minutes.
- **Impact**: Prevents transactions from holding locks indefinitely.
- **When to adjust**:
  - For long-running maintenance operations
  - During data imports/exports

#### 3. Lock Timeout (5 seconds)

```sql
ALTER ROLE app IN DATABASE magflow SET lock_timeout = '5s';
```

- **Purpose**: Fails any operation that can't acquire a lock within 5 seconds.
- **Impact**: Prevents queries from waiting too long for locks.
- **When to adjust**:
  - In high-concurrency scenarios
  - During bulk operations

### Applying Timeout Settings

1. **Initial Setup**:

   ```bash
   docker compose exec db psql -U app -d magflow -f scripts/sql/role_timeouts.sql
   ```

1. **Verification**:

   ```sql
   -- Check current timeout settings
   SHOW statement_timeout;
   SHOW idle_in_transaction_session_timeout;
   SHOW lock_timeout;

   -- Or view all settings for the current session
   SHOW ALL;
   ```

1. **Testing Timeouts**:

   ```sql
   -- Test statement timeout (should fail after 30 seconds)
   SELECT pg_sleep(35);

   -- Test idle transaction timeout (start a transaction and wait 2+ minutes)
   BEGIN;
   SELECT pg_sleep(130);
   ```

### Best Practices

1. **Application-Level Timeouts**:

   - Set timeouts in your application that are slightly lower than the database timeouts.
   - This ensures the application can handle timeouts gracefully.

1. **Connection Pooling**:

   - Configure connection pool timeouts to match database timeouts.
   - Ensure proper connection cleanup in your application.

1. **Monitoring**:

   - Monitor for timeout-related errors in your application logs.
   - Set up alerts for frequent timeouts that might indicate performance issues.

### Troubleshooting

#### Common Issues

1. **Query Timeouts**:

   - **Symptom**: Queries fail with "canceling statement due to statement timeout"
   - **Solution**:
     - Optimize the slow query
     - Increase `statement_timeout` if needed
     - Consider using a different role for long-running operations

1. **Idle Transaction Timeouts**:

   - **Symptom**: "canceling statement due to statement timeout" after long idle periods
   - **Solution**:
     - Ensure transactions are committed or rolled back promptly
     - Use `SET LOCAL` to adjust timeouts for specific transactions

1. **Lock Timeouts**:

   - **Symptom**: "canceling statement due to lock timeout"
   - **Solution**:
     - Review transaction isolation levels
     - Optimize transaction scope
     - Consider using `NOWAIT` for non-critical operations
