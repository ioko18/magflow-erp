#!/bin/bash
set -euo pipefail

# Configuration
CA_DIR="./certs/ca"
CA_KEY="$CA_DIR/ca.key"
CA_CRT="$CA_DIR/ca.crt"
CA_SUBJECT="/CN=MagFlow Internal CA/OU=Database/O=MagFlow/L=Remote/ST=Remote/C=RO"
CA_DAYS=3650  # 10 years

# Create CA directory
mkdir -p "$CA_DIR"

# Generate private key for CA
echo "Generating CA private key..."
openssl genrsa -out "$CA_KEY" 4096

# Generate self-signed CA certificate
echo "Generating self-signed CA certificate..."
openssl req -new -x509 \
    -days "$CA_DAYS" \
    -key "$CA_KEY" \
    -out "$CA_CRT" \
    -subj "$CA_SUBJECT" \
    -addext "keyUsage = critical, keyCertSign, cRLSign" \
    -addext "basicConstraints = critical, CA:TRUE" \
    -addext "subjectKeyIdentifier = hash" \
    -addext "authorityKeyIdentifier = keyid:always,issuer"

# Set proper permissions
chmod 600 "$CA_KEY"
chmod 644 "$CA_CRT"

echo "\nCA generation complete!"
echo "CA certificate: $CA_CRT"
echo "CA private key: $CA_KEY"
echo "\nTo view the CA certificate:"
echo "  openssl x509 -in $CA_CRT -text -noout"
