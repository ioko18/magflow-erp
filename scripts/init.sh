#!/bin/bash
set -e

# Initialize environment
cp .env.example .env

# Create necessary directories
mkdir -p logs

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Initialize database
echo "Initializing database..."
docker-compose up -d db

# Wait for database to be ready
echo "Waiting for database to be ready..."
until docker-compose exec -T db pg_isready -U app -d magflow > /dev/null 2>&1; do
  sleep 1
done

# Run migrations
echo "Running database migrations..."
alembic upgrade head

echo "\nSetup complete! You can now start the application with:"
echo "docker-compose up -d"
echo ""
echo "Or run it directly with:"
echo "uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
