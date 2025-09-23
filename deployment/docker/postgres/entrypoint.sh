#!/bin/bash
set -e

# Create directories and set permissions
mkdir -p /etc/ssl/certs/postgresql /etc/ssl/private/postgresql
chown -R postgres:postgres /etc/ssl/certs/postgresql /etc/ssl/private/postgresql
chmod 600 /etc/ssl/private/postgresql/*.key 2>/dev/null || true
chmod 644 /etc/ssl/certs/postgresql/*.crt 2>/dev/null || true

# Start PostgreSQL with TLS configuration
exec /usr/local/bin/docker-entrypoint.sh postgres \
  -c ssl=on \
  -c ssl_cert_file=/etc/ssl/certs/postgresql/server.crt \
  -c ssl_key_file=/etc/ssl/private/postgresql/server.key \
  -c ssl_ca_file=/etc/ssl/certs/postgresql/ca.crt \
  -c shared_preload_libraries=pg_stat_statements \
  -c pg_stat_statements.track=all \
  -c log_connections=on \
  -c log_disconnections=on \
  -c log_statement=all \
  -c log_destination=stderr
