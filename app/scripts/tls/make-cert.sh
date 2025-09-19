#!/bin/bash
set -euo pipefail

# Configuration
CERT_DIR="./certs"
CA_DIR="$CERT_DIR/ca"
CA_KEY="$CA_DIR/ca.key"
CA_CRT="$CA_DIR/ca.crt"
DAYS=365  # 1 year

# Check if CA exists
if [[ ! -f "$CA_KEY" || ! -f "$CA_CRT" ]]; then
    echo "Error: CA files not found. Please run make-ca.sh first."
    exit 1
fi

# Parse arguments
if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <name> [<alt_names>]"
    echo "Example: $0 pgbouncer "DNS:pgbouncer,DNS:localhost,IP:127.0.0.1""
    echo "Example: $0 postgres "DNS:postgres,DNS:db,DNS:localhost,IP:127.0.0.1""
    exit 1
fi

NAME="$1"
ALT_NAMES="${2:-DNS:$NAME}"

# Create certs directory if it doesn't exist
mkdir -p "$CERT_DIR"

# Generate private key
echo "Generating private key for $NAME..."
openssl genrsa -out "$CERT_DIR/$NAME.key" 2048

# Create CSR config
CONFIG="$CERT_DIR/$NAME.cnf"
cat > "$CONFIG" << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = $NAME

[v3_req]
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = $ALT_NAMES
EOF

# Generate CSR
echo "Generating CSR for $NAME..."
openssl req -new \
    -key "$CERT_DIR/$NAME.key" \
    -out "$CERT_DIR/$NAME.csr" \
    -config "$CONFIG"

# Sign the certificate
echo "Signing certificate for $NAME..."
openssl x509 -req \
    -in "$CERT_DIR/$NAME.csr" \
    -CA "$CA_CRT" \
    -CAkey "$CA_KEY" \
    -CAcreateserial \
    -out "$CERT_DIR/$NAME.crt" \
    -days "$DAYS" \
    -extensions v3_req \
    -extfile "$CONFIG"

# Generate combined certificate and key for PgBouncer
cat "$CERT_DIR/$NAME.crt" "$CERT_DIR/$NAME.key" > "$CERT_DIR/$NAME-combined.pem"

# Set proper permissions
chmod 600 "$CERT_DIR/$NAME.key" "$CERT_DIR/$NAME-combined.pem"
chmod 644 "$CERT_DIR/$NAME.crt"

# Cleanup
rm -f "$CONFIG" "$CERT_DIR/$NAME.csr"

echo "\nCertificate generation complete!"
echo "Certificate: $CERT_DIR/$NAME.crt"
echo "Private key: $CERT_DIR/$NAME.key"
echo "Combined (cert+key): $CERT_DIR/$NAME-combined.pem"
echo "\nTo verify the certificate:"
echo "  openssl x509 -in $CERT_DIR/$NAME.crt -text -noout"
echo "\nTo verify against CA:"
echo "  openssl verify -CAfile $CA_CRT $CERT_DIR/$NAME.crt"
