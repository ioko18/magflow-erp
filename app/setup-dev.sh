#!/bin/bash

# MagFlow Development Setup Script
echo '🚀 Setting up MagFlow development environment...'

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo '❌ Docker is required'; exit 1; }

# Create directories
mkdir -p logs jwt-keys monitoring/prometheus monitoring/grafana/provisioning monitoring/grafana/dashboards

# Copy environment if needed
[ -f .env ] || cp .env.example .env

# Generate JWT keys if needed
[ -f jwt-keys/private.pem ] || {
    openssl genrsa -out jwt-keys/private.pem 2048
    openssl rsa -in jwt-keys/private.pem -pubout -out jwt-keys/public.pem
}

# Start services
echo '🐳 Starting services...'
docker compose up -d

# Wait for services
echo '⏳ Waiting for services to be ready...'
sleep 10

echo '✅ Development environment ready!'
echo ''
echo '🔗 Access points:'
echo '  • API: http://localhost:8000'
echo '  • Docs: http://localhost:8000/docs'
echo '  • Health: http://localhost:8000/health'
echo ''
echo '🧪 Run tests: docker compose exec app pytest'

