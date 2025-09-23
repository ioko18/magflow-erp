# PgBouncer Configuration & Optimization

## TLS Configuration

### Certificate Setup
1. Generate certificates using the provided script:
   ```bash
   ./scripts/generate_certs.sh
   ```
2. Certificates will be created in `./certs/` directory
3. Required files:
   - `ca/ca.crt`: CA certificate
   - `postgresql.crt` and `private/postgresql.key`: PostgreSQL server certificate
   - `pgbouncer.crt` and `private/pgbouncer.key`: PgBouncer server certificate
   - `pgbouncer-combined.pem`: Combined certificate and key for PgBouncer

### TLS Settings
- **Client to PgBouncer**:
  - `client_tls_sslmode = require`
  - Validates client certificates against CA
  - Strong ciphers only (AES256-GCM, etc.)

- **PgBouncer to PostgreSQL**:
  - `server_tls_sslmode = verify-full`
  - Validates server certificate against CA
  - Enforces hostname verification

## Prepared Statements Support

### Configuration
- **max_prepared_statements**: 200 (adjust based on application needs)
- **server_reset_query**: `DISCARD ALL` (clean up prepared statements between transactions)
- **server_reset_query_always**: 1 (always run reset query)
- **server_check_delay**: 10s (time between server connection checks)
- **server_lifetime**: 1800s (30 minutes, recycle connections periodically)
- **server_idle_timeout**: 600s (10 minutes, close idle connections)

### Performance Tuning
- **Connection Pooling**:
  - `max_client_conn = 500`
  - `default_pool_size = 50`
  - `min_pool_size = 10`
  - `reserve_pool_size = 10`
  - `max_db_connections = 100`

- **Timeouts**:
  - `query_wait_timeout = 120s`
  - `idle_transaction_timeout = 0` (disabled)
  - `query_timeout = 0` (disabled)

### Monitoring
- **Stats Users**: `stats_users = stats_user`
- **Admin Users**: `admin_users = admin_user`
- **Logging**:
  - `log_connections = 1`
  - `log_disconnections = 1`
  - `log_pooler_errors = 1`
  - `log_stats = 1`
  - `stats_period = 60`

### Important Notes
1. **Memory Usage**: Each prepared statement consumes ~10KB of memory in PgBouncer
2. **DDL Changes**: After schema changes (ALTER TABLE, etc.), clients should reconnect
3. **Monitoring**: Track `SHOW STATS` for prepared statement usage and evictions
4. **Pool Sizing**: Ensure `max_client_conn` is appropriately sized for your workload

### Best Practices
- Use parameterized queries in your application
- Set appropriate statement timeouts
- Monitor `pgbouncer.prepared_statements` for usage patterns
- Consider increasing `max_prepared_statements` if you see evictions in logs
- Regularly rotate TLS certificates (annually recommended)
- Monitor TLS handshake failures in logs

## Security

## Current Setup
- **Version**: pgbouncer/pgbouncer:1.24.1 (official image)
- **Port**: 6432 (pgbouncer service)
- **Pool Modes**:
  - `magflow_tx`: transaction pooling (default for application)
  - `magflow_session`: session pooling (for migrations)
- **Auth Type**: SCRAM-SHA-256 (secure password authentication)
- **Healthcheck**: `psql -U pgbouncer -h 127.0.0.1 -p 6432 -d pgbouncer -c "SHOW STATS;"`

## Connection Details
- **Application DSN**: `postgresql+psycopg://user:pass@pgbouncer:6432/magflow_tx`
- **Alembic DSN**: `postgresql+psycopg://user:pass@pgbouncer:6432/magflow_session`

## SCRAM Authentication Setup

### 1. Update PostgreSQL Configuration

First, ensure PostgreSQL is configured to use SCRAM authentication. Add these lines to `postgresql.conf`:

```ini
password_encryption = 'scram-sha-256'
```

### 2. Set Up PgBouncer

1. **Using auth_query (Recommended for Production)**
   - PgBouncer will query PostgreSQL for user credentials
   - Update `pgbouncer.ini`:
     ```ini
     auth_type = scram-sha-256
     auth_query = SELECT usename, passwd FROM pg_shadow WHERE usename = $1
     ```

2. **Using userlist.txt (Alternative)**
   - Generate SCRAM verifiers using the provided script:
     ```bash
     ./scripts/generate_scram_verifiers.py app your_secure_password > docker/pgbouncer/userlist.txt
     ```
   - Update `pgbouncer.ini`:
     ```ini
     auth_type = scram-sha-256
     auth_file = /etc/pgbouncer/userlist.txt
     ```

### 3. Automated Setup

Run the setup script to configure SCRAM authentication:

```bash
# Make the script executable
chmod +x scripts/setup_scram_auth.sh

# Run the setup (will prompt for password if not in .env)
./scripts/setup_scram_auth.sh
```

### 4. Verify Authentication

Test the connection using SCRAM authentication:

```bash
PGPASSWORD=your_password psql -h localhost -p 6432 -U app -d magflow -c "SELECT 1"
```

## Key Configuration

## SQLAlchemy Configuration
- **Pool Class**: NullPool (delegates to PgBouncer)
- **Pre-ping**: Enabled for connection validation
- **Application Name**: magflow-app (for monitoring)

## SCRAM-SHA-256 Migration Checklist

### Prerequisites
- PostgreSQL 10+ with SCRAM support
- PgBouncer 1.21+ with SCRAM support
- Updated client libraries

### Migration Steps

1. **Generate SCRAM hashes** (do NOT commit to repo):
   ```bash
   # Generate SCRAM hash for user
   python3 -c "
   import hashlib, secrets, base64
   password = 'your_password_here'
   salt = secrets.token_bytes(16)
   # SCRAM-SHA-256 implementation needed
   "
   ```

2. **Update userlist.txt format**:
   ```
   # From MD5 format:
   "username" "md5hash"

   # To SCRAM format:
   "username" "SCRAM-SHA-256$4096:salt$storedkey:serverkey"
   ```

3. **Update pgbouncer.ini**:
   ```ini
   auth_type = scram-sha-256
   auth_file = /etc/pgbouncer/userlist.txt
   ```

4. **Environment variables**:
   ```bash
   # Add to .env (not committed)
   PGBOUNCER_AUTH_TYPE=scram-sha-256
   ```

5. **Test connection**:
   ```bash
   psql -h localhost -p 6432 -U app -d magflow
   ```

### Security Benefits
- Stronger password hashing (SHA-256 vs MD5)
- Salt-based protection against rainbow tables
- Challenge-response authentication
- Forward secrecy

### Rollback Plan
1. Revert `auth_type = md5` in pgbouncer.ini
2. Restore MD5 userlist.txt format
3. Restart PgBouncer service

## Version Pinning & Healthcheck Strategy

### Why We Pin Versions (Avoid :latest)
- **Stability**: Prevents unexpected breaking changes from automatic updates
- **Security**: Using latest available stable version (1.12.0)
- **Reproducibility**: Ensures consistent behavior across environments
- **Controlled Updates**: Allows testing before upgrading to newer versions

### Why We Use `SHOW STATS` for Healthcheck
- **Functional Verification**: Tests actual PgBouncer functionality, not just port availability
- **Admin Interface**: Verifies the admin interface is responsive
- **Connection Pool Status**: Ensures the connection pooling mechanism is working
- **Better Than `nc -z`**: Port checks can pass even when the service is degraded

## Monitoring
- Health endpoint: `/observability/pool`
- Admin commands: `SHOW STATS`, `SHOW POOLS`, `SHOW CONFIG`
- Application name visible in `pg_stat_activity`
