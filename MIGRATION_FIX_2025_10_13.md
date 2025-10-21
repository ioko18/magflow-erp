# Migration Fix - October 13, 2025

## Problem
The application was failing to start with the error:
```
asyncpg.exceptions.DuplicateTableError: relation "users" already exists
```

## Root Cause
The database tables were already created by the `init-db` scripts, but Alembic's migration system thought no migrations had been run yet. When Alembic tried to run the initial migration `86f7456767fd`, it attempted to create tables that already existed, causing the error.

## Solution
Made all Alembic migrations **idempotent** by adding checks to verify if tables/columns exist before attempting to create them. This ensures migrations can be safely run multiple times without errors.

## Files Modified

### 1. `/alembic/versions/86f7456767fd_initial_database_schema_with_users_.py`
- Added table existence checks using SQLAlchemy inspector
- Only creates tables if they don't already exist
- Tables checked: `users`, `roles`, `permissions`, `user_roles`, `role_permissions`, `refresh_tokens`

### 2. `/alembic/versions/4242d9721c62_add_missing_tables.py`
- Added table existence check for `audit_logs`
- Only creates table and indexes if table doesn't exist

### 3. `/alembic/versions/97aa49837ac6_add_product_relationships_tables.py`
- Added table existence checks for `product_variants` and `product_genealogy`
- Only creates tables and their indexes if they don't exist

### 4. `/alembic/versions/6d303f2068d4_create_emag_offer_tables.py`
- Added table existence checks for:
  - `emag_products`
  - `emag_product_offers`
  - `emag_offer_syncs`
  - `emag_import_conflicts`
- Only creates tables and indexes if they don't exist

### 5. `/alembic/versions/20251013_fix_import_logs_timezone.py`
- Added column type checks before altering columns
- Only converts columns from `TIMESTAMP WITHOUT TIME ZONE` to `TIMESTAMP WITH TIME ZONE` if needed
- Columns: `import_logs.started_at`, `import_logs.completed_at`, `product_mappings.last_imported_at`

### 6. `/alembic/versions/20251013_fix_product_supplier_sheets_tz.py`
- Added column type checks before altering columns
- Uses parameterized queries to avoid SQL injection warnings
- Columns: `price_updated_at`, `last_imported_at`, `verified_at`, `created_at`, `updated_at`

## Migration Already Idempotent
- `/alembic/versions/b1234f5d6c78_add_metadata_column_to_emag_product_offers.py` - Already had proper checks

## Additional Fixes Applied

### 7. Fixed Multiple SQL Statements Issue
The asyncpg driver doesn't support multiple SQL statements in a single `op.execute()` call. Split the seed data INSERT statements into separate calls:
- Separated role insertion from permissions insertion
- Each INSERT is now executed independently

### 8. Fixed NOT NULL Constraint Violation
The seed data INSERT statements were missing required `created_at` and `updated_at` columns:
- Added `created_at` and `updated_at` columns to INSERT statements
- Used `now()` function to populate timestamp values

### 9. Fixed Duplicate ENUM Type Error
The `init_database_complete.py` script was trying to create ENUM types that already existed:
- Added comprehensive check to verify if database schema is already initialized
- Checks both for existing tables (`users`) and ENUM types (`cancellationstatus`)
- If either tables or ENUMs exist, skip table creation to avoid duplicate errors
- File: `/scripts/init_database_complete.py`
- Query checks: `information_schema.tables` and `pg_type` catalog

## Testing Results
✅ **All containers are now running successfully!**

After applying all fixes:
1. ✅ Migrations run successfully even if tables already exist
2. ✅ Tables that already exist are skipped
3. ✅ Only new changes are applied
4. ✅ Application starts without errors
5. ✅ Health check endpoint returns: `{"status": "alive"}`

### Container Status
```
NAME             STATUS
magflow_app      Up (healthy)
magflow_worker   Up (healthy)
magflow_db       Up (healthy)
magflow_redis    Up (healthy)
```

### Application Logs
```
✅ Database already initialized
🔄 Running database migrations...
✅ Migrations completed successfully!
🎉 Application ready to start!
INFO: Uvicorn running on http://0.0.0.0:8000
INFO: Application startup complete
```

## Summary
The migration errors have been completely resolved. The application now:
- Handles existing database tables gracefully
- Runs migrations idempotently
- Starts successfully with all services healthy
- Responds to health check requests
