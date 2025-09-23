#!/bin/bash
set -e

# Create necessary directories
mkdir -p /etc/ssl/certs/postgresql
mkdir -p /etc/ssl/private

# Set proper permissions on certificates
chmod 600 /etc/ssl/private/postgresql/server.key
chmod 644 /etc/ssl/certs/postgresql/server.crt
chmod 644 /etc/ssl/certs/postgresql/ca.crt

# Update postgresql.conf with SSL settings
cat >> /var/lib/postgresql/data/postgresql.conf <<EOL
# SSL Configuration
ssl = on
ssl_cert_file = '/etc/ssl/certs/postgresql/server.crt'
ssl_key_file = '/etc/ssl/private/postgresql/server.key'
ssl_ca_file = '/etc/ssl/certs/postgresql/ca.crt'
ssl_ciphers = 'HIGH:!aNULL:!eNULL:!EXPORT:!DES:!3DES:!MD5:!PSK:!RC4'
ssl_prefer_server_ciphers = on
ssl_ecdh_curve = 'prime256v1'
EOL

# Update pg_hba.conf to require SSL for all connections
cat >> /var/lib/postgresql/data/pg_hba.conf <<EOL
# Require SSL for all remote connections
hostssl all all all md5 clientcert=1
EOL

echo "SSL configuration completed successfully"
