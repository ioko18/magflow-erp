#!/usr/bin/env bash

set -euo pipefail

# MagFlow ERP Startup Script
# This script ensures all dependencies are installed and starts the server

echo "🔧 Checking Python environment and dependencies..."

# Use the current environment's python
PYTHON_BIN="${PYTHON:-python}"

# Verify Python is available
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "❌ Could not find Python executable '$PYTHON_BIN'. Set PYTHON env var or ensure 'python' is on PATH."
  exit 1
fi

# Install project requirements if key modules are missing
if ! "$PYTHON_BIN" - <<'PY'
try:
    import dependency_injector  # DI container
    import fastapi
    import uvicorn
    import redis.asyncio  # redis client used for rate limiting
except Exception as e:
    raise SystemExit(1)
PY
then
  echo "📦 Installing missing dependencies from requirements.txt..."
  # Workaround for environments with incorrect CA bundle env vars
  unset SSL_CERT_FILE || true
  unset REQUESTS_CA_BUNDLE || true
  "$PYTHON_BIN" -m pip install -r requirements.txt
fi

echo "✅ All dependencies are ready!"
echo "🚀 Starting MagFlow ERP server on http://0.0.0.0:8080 ..."

# Start the server using the module to ensure the current Python env is used
exec "$PYTHON_BIN" -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
