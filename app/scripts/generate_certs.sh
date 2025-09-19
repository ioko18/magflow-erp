#!/bin/bash
set -e

# Create certs directory
CERT_DIR="${1:-./certs}"
mkdir -p "$CERT_DIR/ca"
mkdir -p "$CERT_DIR/private"

# Generate CA key and certificate
openssl req -new -x509 -days 3650 -nodes \
  -out "$CERT_DIR/ca/ca.crt" \
  -keyout "$CERT_DIR/ca/ca.key" \
  -subj "/CN=MagFlow CA" \
  -addext "subjectAltName = DNS:localhost,IP:127.0.0.1"

# Generate PostgreSQL server key and certificate signing request (CSR)
openssl req -new -nodes -text \
  -out "$CERT_DIR/postgres.csr" \
  -keyout "$CERT_DIR/private/postgresql.key" \
  -subj "/CN=postgres"

# Sign the server certificate with the CA
openssl x509 -req -in "$CERT_DIR/postgres.csr" -text \
  -CA "$CERT_DIR/ca/ca.crt" \
  -CAkey "$CERT_DIR/ca/ca.key" \
  -CAcreateserial \
  -out "$CERT_DIR/postgresql.crt" \
  -days 3650 \
  -extfile <(printf "subjectAltName=DNS:postgres,DNS:localhost,IP:127.0.0.1")

# Generate PgBouncer server key and certificate
openssl req -new -nodes -text \
  -out "$CERT_DIR/pgbouncer.csr" \
  -keyout "$CERT_DIR/private/pgbouncer.key" \
  -subj "/CN=pgbouncer"

# Sign the PgBouncer certificate with the CA
openssl x509 -req -in "$CERT_DIR/pgbouncer.csr" -text \
  -CA "$CERT_DIR/ca/ca.crt" \
  -CAkey "$CERT_DIR/ca/ca.key" \
  -CAcreateserial \
  -out "$CERT_DIR/pgbouncer.crt" \
  -days 3650 \
  -extfile <(printf "subjectAltName=DNS:pgbouncer,DNS:localhost,IP:127.0.0.1")

# Set proper permissions
chmod 600 "$CERT_DIR/private"/*
chmod 644 "$CERT_DIR/ca/ca.crt"
chmod 644 "$CERT_DIR"/*.crt

# Create combined certificate for PgBouncer
cat "$CERT_DIR/pgbouncer.crt" "$CERT_DIR/private/pgbouncer.key" > "$CERT_DIR/pgbouncer-combined.pem"
chmod 600 "$CERT_DIR/pgbouncer-combined.pem"

echo "Certificates generated in $CERT_DIR:"
find "$CERT_DIR" -type f -exec ls -la {} \;

echo -e "\nTo use these certificates, add these volumes to your docker-compose.yml:"
cat << EOF
    volumes:
      - ./certs/ca/ca.crt:/etc/ssl/certs/ca-certificates/ca.crt:ro
      - ./certs/postgresql.crt:/etc/ssl/certs/postgresql.crt:ro
      - ./certs/private/postgresql.key:/etc/ssl/private/postgresql.key:ro
      - ./certs/pgbouncer.crt:/etc/ssl/certs/pgbouncer.crt:ro
      - ./certs/private/pgbouncer.key:/etc/ssl/private/pgbouncer.key:ro
      - ./certs/pgbouncer-combined.pem:/etc/ssl/private/pgbouncer-combined.pem:ro
EOF
