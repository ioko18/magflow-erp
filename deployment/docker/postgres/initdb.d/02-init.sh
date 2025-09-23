#!/bin/bash
set -e

# Create the app user if it doesn't exist
echo "Creating user 'app' if it doesn't exist..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app') THEN
            CREATE USER app WITH PASSWORD 'app_password_change_me';
            GRANT ALL PRIVILEGES ON DATABASE magflow TO app;
        END IF;
    END
    \$\$;

    -- Connect to the magflow database
    \c magflow

    -- Create the schema if it doesn't exist
    CREATE SCHEMA IF NOT EXISTS app;
    GRANT ALL PRIVILEGES ON SCHEMA app TO app;

    -- Create idempotency_keys table if it doesn't exist
    CREATE TABLE IF NOT EXISTS app.idempotency_keys (
        key TEXT PRIMARY KEY,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        expires_at TIMESTAMPTZ NOT NULL,
        method TEXT NOT NULL,
        path TEXT NOT NULL,
        response_status_code INTEGER,
        response_headers JSONB,
        response_body BYTEA
    );

    -- Create index for expiration
    CREATE INDEX IF NOT EXISTS idx_idempotency_keys_expires_at ON app.idempotency_keys (expires_at);

    -- Create a test table for benchmarking
    CREATE TABLE IF NOT EXISTS app.test_table (
        id SERIAL PRIMARY KEY,
        data TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    -- Insert test data
    INSERT INTO app.test_table (data)
    SELECT md5(random()::text)
    FROM generate_series(1, 1000);

    -- Grant permissions
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA app TO app;
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app TO app;
EOSQL

echo "Database initialization complete!"
