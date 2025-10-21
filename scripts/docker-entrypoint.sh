#!/bin/bash
# Note: We don't use 'set -e' globally because we handle errors explicitly in migration retry logic

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

# Run Alembic migrations with retry logic and proper error handling
echo "🔄 Running database migrations..."

# Function to run migrations with retries
run_migrations_with_retry() {
    local max_attempts=3
    local attempt=1
    local temp_output="/tmp/migration_output_$$.txt"
    
    while [ $attempt -le $max_attempts ]; do
        echo "   📝 Migration attempt $attempt/$max_attempts..." >&2
        
        # Run migrations and capture output
        alembic upgrade head > "$temp_output" 2>&1
        local exit_code=$?
        
        if [ $exit_code -eq 0 ]; then
            # Success - show output and return
            cat "$temp_output"
            rm -f "$temp_output"
            echo "✅ Migrations completed successfully!" >&2
            return 0
        else
            # Failed - check if it's a race condition
            echo "   ⚠️  Migration attempt $attempt failed with exit code $exit_code" >&2
            
            # Check if it's a duplicate key/type error (race condition)
            if grep -q -E "(duplicate key|already exists|UniqueViolation|pg_type_typname_nsp_index)" "$temp_output" 2>/dev/null; then
                echo "   🔍 Race condition detected (another container is running migrations)" >&2
                
                # Don't show the full error trace for race conditions
                echo "   💤 Waiting for other container to complete migrations..." >&2
                rm -f "$temp_output"
                
                # Wait progressively longer
                local wait_time=$((attempt * 2))
                sleep $wait_time
                
                # Check if migrations are now complete
                if python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def check_migrations():
    try:
        engine = create_async_engine(settings.DB_URI, echo=False)
        async with engine.connect() as conn:
            result = await conn.execute(
                text(\"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'app' AND table_name = 'alembic_version'\")
            )
            if result.scalar() > 0:
                result = await conn.execute(text(\"SELECT COUNT(*) FROM app.alembic_version\"))
                await engine.dispose()
                return result.scalar() > 0
            await engine.dispose()
            return False
    except Exception:
        return False

exit(0 if asyncio.run(check_migrations()) else 1)
" 2>/dev/null; then
                    echo "✅ Migrations completed by another container!" >&2
                    return 0
                fi
                
                if [ $attempt -lt $max_attempts ]; then
                    echo "   🔄 Retrying migration check..." >&2
                    attempt=$((attempt + 1))
                else
                    echo "❌ Migration verification failed after $max_attempts attempts!" >&2
                    return 1
                fi
            else
                # Different error - show full output
                echo "   ❌ Unexpected migration error:" >&2
                cat "$temp_output"
                rm -f "$temp_output"
                
                if [ $attempt -lt $max_attempts ]; then
                    echo "   🔄 Retrying in 3 seconds..." >&2
                    sleep 3
                    attempt=$((attempt + 1))
                else
                    echo "❌ Migration failed after $max_attempts attempts!" >&2
                    return $exit_code
                fi
            fi
        fi
    done
    
    # Should never reach here
    return 1
}

# Run migrations with retry logic
if ! run_migrations_with_retry; then
    echo "❌ Migration process failed!" >&2
    exit 1
fi

echo "🎉 Application ready to start!"
echo ""

# Execute the main command
exec "$@"
