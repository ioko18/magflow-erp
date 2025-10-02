#!/bin/bash
set -e

echo "🚀 MagFlow ERP - Starting application..."

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def check_db():
    try:
        engine = create_async_engine(settings.DB_URI, echo=False)
        async with engine.connect() as conn:
            await conn.execute(text('SELECT 1'))
        await engine.dispose()
        return True
    except Exception as e:
        print(f'Database not ready: {e}')
        return False

exit(0 if asyncio.run(check_db()) else 1)
" 2>/dev/null; then
        echo "✅ Database is ready!"
        break
    fi
    
    attempt=$((attempt + 1))
    echo "   Attempt $attempt/$max_attempts - Database not ready yet..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ Database connection timeout after $max_attempts attempts"
    exit 1
fi

# Check if database is initialized
echo "🔍 Checking database initialization status..."
if python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def check_tables():
    try:
        engine = create_async_engine(settings.DB_URI, echo=False)
        async with engine.connect() as conn:
            result = await conn.execute(
                text(\"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'app' AND table_name = 'users'\")
            )
            count = result.scalar()
            await engine.dispose()
            return count > 0
    except Exception as e:
        print(f'Error checking tables: {e}')
        return False

exit(0 if asyncio.run(check_tables()) else 1)
" 2>/dev/null; then
    echo "✅ Database already initialized"
else
    echo "🔧 Initializing database..."
    python /app/scripts/init_database_complete.py
    
    if [ $? -eq 0 ]; then
        echo "✅ Database initialized successfully!"
    else
        echo "❌ Database initialization failed!"
        exit 1
    fi
fi

# Run Alembic migrations to ensure schema is up to date
echo "🔄 Running database migrations..."
alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Migrations completed successfully!"
else
    echo "⚠️  Migration warnings (may be normal if already up to date)"
fi

echo "🎉 Application ready to start!"
echo ""

# Execute the main command
exec "$@"
