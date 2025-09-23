-- Create the database
CREATE DATABASE magflow;

-- Connect to the database
\c magflow

-- Create the schema
CREATE SCHEMA IF NOT EXISTS app;

-- Create the user with password
CREATE USER app WITH PASSWORD 'app_password_change_me';
GRANT ALL PRIVILEGES ON DATABASE magflow TO app;
GRANT ALL PRIVILEGES ON SCHEMA app TO app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA app TO app;

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT ALL PRIVILEGES ON TABLES TO app;
ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT ALL PRIVILEGES ON SEQUENCES TO app;

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

-- Grant permissions on idempotency_keys table
GRANT ALL PRIVILEGES ON TABLE app.idempotency_keys TO app;

-- Create a test table for benchmarking
CREATE TABLE IF NOT EXISTS app.test_table (
    id SERIAL PRIMARY KEY,
    data TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Insert some test data
INSERT INTO app.test_table (data)
SELECT md5(random()::text)
FROM generate_series(1, 1000);

-- Grant permissions on test table
GRANT ALL PRIVILEGES ON TABLE app.test_table TO app;
GRANT USAGE, SELECT ON SEQUENCE app.test_table_id_seq TO app;
