#!/bin/bash
set -e

# Create directories if they don't exist
mkdir -p /etc/ssl/certs/postgresql /etc/ssl/private/postgresql

# Copy certificates to the correct locations
if [ -f "/etc/ssl/certs/postgresql/server.crt" ]; then
    cp /etc/ssl/certs/postgresql/server.crt /var/lib/postgresql/server.crt
    chown postgres:postgres /var/lib/postgresql/server.crt
    chmod 600 /var/lib/postgresql/server.crt
fi

if [ -f "/etc/ssl/private/postgresql/server.key" ]; then
    cp /etc/ssl/private/postgresql/server.key /var/lib/postgresql/server.key
    chown postgres:postgres /var/lib/postgresql/server.key
    chmod 600 /var/lib/postgresql/server.key
fi

if [ -f "/etc/ssl/certs/postgresql/ca.crt" ]; then
    cp /etc/ssl/certs/postgresql/ca.crt /var/lib/postgresql/root.crt
    chown postgres:postgres /var/lib/postgresql/root.crt
    chmod 600 /var/lib/postgresql/root.crt
fi

# Set ownership and permissions on directories
chown -R postgres:postgres /etc/ssl/certs/postgresql /etc/ssl/private/postgresql
chmod 700 /etc/ssl/private/postgresql
chmod 755 /etc/ssl/certs/postgresql

echo "PostgreSQL SSL certificates and permissions set up successfully"
