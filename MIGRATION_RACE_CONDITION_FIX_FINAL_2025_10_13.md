# Migration Race Condition Fix - Final Solution
**Date**: 2025-10-13  
**Status**: ✅ RESOLVED

## Problem
When starting multiple Docker containers simultaneously (`app`, `worker`, `beat`), they all attempted to run Alembic migrations concurrently, causing a PostgreSQL race condition:

```
ERROR: duplicate key value violates unique constraint "pg_type_typname_nsp_index"
DETAIL: Key (typname, typnamespace)=(alembic_version, 16443) already exists.
```

## Root Cause
Multiple containers were trying to create the `alembic_version` table simultaneously, causing PostgreSQL internal type catalog conflicts.

## Solution
Implemented **PostgreSQL Advisory Locks** in `alembic/env.py` to ensure only one container runs migrations at a time:

### Changes Made

#### 1. Added Advisory Lock in `alembic/env.py`
```python
async def run_migrations_online() -> None:
    connectable = create_async_engine(settings.DB_URI, future=True)

    async with connectable.connect() as connection:
        # Acquire PostgreSQL advisory lock to prevent race conditions
        # Lock ID: 123456789 (arbitrary unique number for migrations)
        await connection.execute(text("SELECT pg_advisory_lock(123456789)"))

        try:
            # Set search path and create schema
            await connection.execute(text(f'SET search_path TO "{schema_name}", public'))
            await connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
            await connection.commit()

            # Run migrations
            await connection.run_sync(do_run_migrations)
        finally:
            # Always release the advisory lock
            await connection.execute(text("SELECT pg_advisory_unlock(123456789)"))

    await connectable.dispose()
```

#### 2. Removed `version_table_schema` Configuration
Commented out `version_table_schema=schema_name` in both `do_run_migrations()` and `run_migrations_offline()` to keep the `alembic_version` table in the default `public` schema.

## How It Works
1. **Advisory Lock**: PostgreSQL advisory locks are session-level locks that don't lock actual database objects
2. **Lock ID**: Uses a unique integer (123456789) to identify this specific lock
3. **Automatic Blocking**: When container A acquires the lock, containers B and C wait automatically
4. **Guaranteed Release**: The `finally` block ensures the lock is always released, even if migrations fail

## Benefits
- ✅ **No Race Conditions**: Only one container runs migrations at a time
- ✅ **No Code Changes in Migrations**: The lock is transparent to migration scripts
- ✅ **Automatic Retry**: Other containers wait and proceed once the lock is released
- ✅ **No Deadlocks**: Advisory locks are automatically released when the connection closes
- ✅ **Zero Downtime**: Containers start successfully regardless of which one runs migrations first

## Testing Results
Tested with multiple scenarios:
1. ✅ Fresh start with `docker compose down -v && docker compose up -d`
2. ✅ Simultaneous container restarts
3. ✅ Multiple rapid restarts
4. ✅ All containers healthy and operational

**No database errors detected in any scenario.**

## Verification Commands
```bash
# Check for errors
docker compose logs db | grep -E "(ERROR|duplicate)"

# Verify migrations completed
docker compose logs app worker | grep -E "Migration"

# Check application health
curl http://localhost:8000/api/v1/health/ready
```

## Files Modified
- `alembic/env.py` - Added advisory lock mechanism and removed version_table_schema

## Migration Status
All 4 consolidated migrations run successfully:
1. ✅ `86f7456767fd` - Initial database schema with ALL tables and ENUM types
2. ✅ `6d303f2068d4` - Create emag offer tables
3. ✅ `20251010_add_auxiliary` - Add auxiliary tables
4. ✅ `20251013_fix_all_tz` - Fix all timezone columns

## Conclusion
The race condition is completely resolved using PostgreSQL's built-in advisory lock mechanism. This is a standard, production-ready solution used by many applications to coordinate database operations across multiple instances.
