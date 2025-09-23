#!/bin/sh
set -e

# Create JWT keys directory with correct permissions
mkdir -p /app/jwt-keys
chown -R appuser:appuser /app/jwt-keys
chmod 755 /app/jwt-keys

echo "JWT keys directory initialized successfully"
