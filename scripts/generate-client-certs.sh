#!/bin/bash
set -e

# Create directory for client certificates
mkdir -p certs/client

# Generate client key and certificate signing request (CSR)
openssl req -new -nodes \
  -newkey rsa:2048 \
  -keyout certs/client/client.key \
  -out certs/client/client.csr \
  -subj "/CN=pgbouncer"

# Sign the client certificate with the CA
openssl x509 -req \
  -in certs/client/client.csr \
  -CA certs/ca/ca.crt \
  -CAkey certs/ca/ca.key \
  -CAcreateserial \
  -out certs/client/client.crt \
  -days 365 \
  -sha256

# Set proper permissions
chmod 600 certs/client/*

echo "Client certificates generated in certs/client/"
