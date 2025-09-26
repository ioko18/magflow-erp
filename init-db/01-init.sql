-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Set up search path
SET search_path TO app, public;

-- Create custom types if they don't exist
DO $$
BEGIN
    -- Create enum types if they don't exist
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role_enum') THEN
        CREATE TYPE user_role_enum AS ENUM ('admin', 'manager', 'user', 'viewer');
    END IF;
    
    -- Add more enums as needed
    -- IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'another_enum') THEN
    --     CREATE TYPE another_enum AS ENUM ('value1', 'value2');
    -- END IF;
END
$$;

-- Create schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS app AUTHORIZATION app;

-- Set default privileges for the app user
ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT ALL PRIVILEGES ON TABLES TO app;
ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT ALL PRIVILEGES ON SEQUENCES TO app;
ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT EXECUTE ON FUNCTIONS TO app;

-- Set search path for the current session
SET search_path TO app, public;
