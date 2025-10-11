#!/bin/bash
# Start MagFlow Backend Script

echo "🚀 Starting MagFlow Backend..."

# Navigate to project directory
cd "$(dirname "$0")"

# Activate conda environment
echo "📦 Activating conda environment..."
eval "$(conda shell.bash hook)"
conda activate MagFlow

# Set environment variables if not set
if [ -z "$DATABASE_URL" ]; then
    echo "⚙️  Setting DATABASE_URL from docker-compose..."
    export DATABASE_URL="postgresql+asyncpg://app:pQ4mR9tY2wX7zK3nL8vB5cD1fG6hJ0@localhost:5433/magflow"
fi

if [ -z "$REDIS_URL" ]; then
    echo "⚙️  Setting REDIS_URL from docker-compose..."
    export REDIS_URL="redis://:pQ4mR9tY2wX7zK3nL8vB5cD1fG6hJ0@localhost:6379/0"
fi

# Check if port 8000 is already in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 8000 is already in use. Stopping existing process..."
    kill -9 $(lsof -ti:8000)
    sleep 2
fi

# Check database connection
echo "🔍 Checking database connection..."
if psql $DATABASE_URL -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✅ Database connection OK"
else
    echo "❌ Database connection failed!"
    echo "Please check your DATABASE_URL environment variable"
    exit 1
fi

# Check Redis connection
echo "🔍 Checking Redis connection..."
if redis-cli -u $REDIS_URL ping > /dev/null 2>&1; then
    echo "✅ Redis connection OK"
else
    echo "⚠️  Redis connection failed (caching will be disabled)"
fi

# Start backend
echo "🚀 Starting FastAPI server on http://localhost:8000..."
echo "📚 API Documentation: http://localhost:8000/docs"
echo "📊 Health Check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo "----------------------------------------"

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
