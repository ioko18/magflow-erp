# TLS Configuration for MagFlow

This document provides instructions for setting up and managing TLS certificates for secure communication with PgBouncer and PostgreSQL.

## Prerequisites

- OpenSSL 1.1.1 or later
- Docker and Docker Compose
- `make` utility (optional but recommended)

## Directory Structure

```
certs/
├── ca/                  # CA certificate and key
│   ├── ca.crt
│   └── ca.key
├── pgbouncer.crt        # PgBouncer certificate
├── pgbouncer.key        # PgBouncer private key
├── pgbouncer-combined.pem # Combined cert+key for PgBouncer
├── postgres.crt         # PostgreSQL certificate
├── postgres.key         # PostgreSQL private key
└── postgres-combined.pem # Combined cert+key for PostgreSQL
```

## Initial Setup

1. **Generate CA Certificate** (if not already done):
   ```bash
   ./scripts/tls/make-ca.sh
   ```

2. **Generate Certificates** for PgBouncer and PostgreSQL:
   ```bash
   # For PgBouncer
   ./scripts/tls/make-cert.sh pgbouncer "DNS:pgbouncer,DNS:localhost,IP:127.0.0.1"

   # For PostgreSQL
   ./scripts/tls/make-cert.sh postgres "DNS:postgres,DNS:db,DNS:localhost,IP:127.0.0.1"
   ```

## Configuration

### PgBouncer Configuration (`pgbouncer.ini`)

```ini
[databases]
* = host=db dbname=magflow user=app

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 5432
auth_type = trust
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 100
default_pool_size = 20

# Client TLS settings
client_tls_sslmode = require
client_tls_cert_file = /etc/pgbouncer/certs/pgbouncer.crt
client_tls_key_file = /etc/pgbouncer/certs/pgbouncer.key
client_tls_ca_file = /etc/pgbouncer/certs/ca.crt

# Server TLS settings (for connecting to PostgreSQL)
server_tls_sslmode = verify-full
server_tls_cert_file = /etc/pgbouncer/certs/pgbouncer.crt
server_tls_key_file = /etc/pgbouncer/certs/pgbouncer.key
server_tls_ca_file = /etc/pgbouncer/certs/ca.crt
```

### PostgreSQL Configuration (`postgresql.conf`)

```ini
ssl = on
ssl_cert_file = '/var/lib/postgresql/data/server.crt'
ssl_key_file = '/var/lib/postgresql/data/server.key'
ssl_ca_file = '/var/lib/postgresql/data/ca.crt'
```

## Docker Compose Configuration

Update your `docker-compose.yml` to include the certificates:

```yaml
services:
  pgbouncer:
    # ... existing configuration ...
    volumes:
      - ./certs/pgbouncer-combined.pem:/etc/pgbouncer/certs/pgbouncer.pem
      - ./certs/ca/ca.crt:/etc/pgbouncer/certs/ca.crt
      - ./docker/pgbouncer/pgbouncer.ini:/etc/pgbouncer/pgbouncer.ini
      - ./docker/pgbouncer/userlist.txt:/etc/pgbouncer/userlist.txt
    environment:
      - PGBOUNCER_CONFIG_FILE=/etc/pgbouncer/pgbouncer.ini
      - PGBOUNCER_AUTH_FILE=/etc/pgbouncer/userlist.txt
      - PGBOUNCER_SSL_CERT_FILE=/etc/pgbouncer/certs/pgbouncer.pem
      - PGBOUNCER_SSL_KEY_FILE=/etc/pgbouncer/certs/pgbouncer.pem
      - PGBOUNCER_SSL_CA_FILE=/etc/pgbouncer/certs/ca.crt

  db:
    # ... existing configuration ...
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./certs/postgres.crt:/var/lib/postgresql/data/server.crt
      - ./certs/postgres.key:/var/lib/postgresql/data/server.key
      - ./certs/ca/ca.crt:/var/lib/postgresql/data/ca.crt
```

## Certificate Rotation

1. **Generate new certificates** (before old ones expire):
   ```bash
   # Generate new certificates with updated expiration
   ./scripts/tls/make-cert.sh pgbouncer "DNS:pgbouncer,DNS:localhost,IP:127.0.0.1"
   ./scripts/tls/make-cert.sh postgres "DNS:postgres,DNS:db,DNS:localhost,IP:127.0.0.1"
   ```

2. **Reload services** to use new certificates:
   ```bash
   docker compose cp certs/pgbouncer-combined.pem pgbouncer:/etc/pgbouncer/certs/pgbouncer.pem
   docker compose cp certs/postgres.crt db:/var/lib/postgresql/data/server.crt
   docker compose cp certs/postgres.key db:/var/lib/postgresql/data/server.key

   # Reload PgBouncer
   docker compose exec pgbouncer pgbouncer -R /etc/pgbouncer/pgbouncer.ini

   # Reload PostgreSQL
   docker compose exec db pg_ctl reload
   ```

## Testing the Setup

1. **Verify PgBouncer TLS** (from host):
   ```bash
   psql "postgresql://app:password@localhost:5432/magflow?sslmode=require" -c "SELECT 1"
   ```

2. **Check TLS connection info** in PostgreSQL:
   ```sql
   SELECT ssl, version(), inet_client_addr(), usename
   FROM pg_stat_ssl
   JOIN pg_stat_activity ON pg_stat_ssl.pid = pg_stat_activity.pid
   WHERE usename IS NOT NULL;
   ```

## Troubleshooting

### Common Issues

1. **Certificate verification failed**
   - Ensure the CA certificate is trusted by the client
   - Verify the certificate's subject alternative names (SANs) match the connection hostname

2. **Connection refused**
   - Check if PgBouncer is running: `docker compose ps pgbouncer`
   - Check logs: `docker compose logs pgbouncer`

3. **TLS handshake failed**
   - Verify the certificate and key files are readable by the service
   - Check file permissions (should be 600 for private keys)

### Checking Certificate Expiration

```bash
# Check CA expiration
echo "CA expires on: $(openssl x509 -enddate -noout -in certs/ca/ca.crt)"

# Check PgBouncer certificate
echo "PgBouncer cert expires on: $(openssl x509 -enddate -noout -in certs/pgbouncer.crt)"

# Check PostgreSQL certificate
echo "PostgreSQL cert expires on: $(openssl x509 -enddate -noout -in certs/postgres.crt)"
```

## Security Considerations

1. **CA Private Key**: Keep the CA private key (`ca.key`) secure and never share it.
2. **Certificate Lifetimes**:
   - CA: 10 years
   - Server certificates: 1 year (recommended)
3. **File Permissions**:
   - Private keys: 600 (rw-------)
   - Certificates: 644 (rw-r--r--)
4. **Revocation**: Consider implementing CRL or OCSP for certificate revocation if needed.
