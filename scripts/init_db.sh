#!/bin/bash
# Initialize the MagFlow database with proper users and permissions

set -e

# Load environment variables
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Default values
DB_NAME=${DB_NAME:-magflow}
DB_USER=${DB_USER:-app}
DB_PASS=${DB_PASS:-app_password_change_me}
DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-5432}

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until docker-compose exec -T db pg_isready -U postgres -h localhost >/dev/null 2>&1; do
  sleep 1
done

# Create database and user if they don't exist
echo "Creating database and user..."
docker-compose exec -T db psql -U postgres -v ON_ERROR_STOP=1 <<-EOSQL
  -- Create database if not exists
  SELECT 'CREATE DATABASE $DB_NAME'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec
  
  -- Create user if not exists and set password
  DO \$\$
  BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DB_USER') THEN
      CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';
      RAISE NOTICE 'User $DB_USER created';
    ELSE
      ALTER USER $DB_USER WITH PASSWORD '$DB_PASS';
      RAISE NOTICE 'User $DB_USER password updated';
    END IF;
  END \$\$;
  
  -- Grant privileges
  GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
  \c $DB_NAME
  GRANT ALL ON SCHEMA public TO $DB_USER;
  GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;
  GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;
  GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO $DB_USER;
  
  -- Create schema if not exists
  CREATE SCHEMA IF NOT EXISTS app;
  GRANT ALL ON SCHEMA app TO $DB_USER;
  
  -- Set default privileges for future objects
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO $DB_USER;
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TYPES TO $DB_USER;
  
  -- Create extensions
  CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
  CREATE EXTENSION IF NOT EXISTS "pgcrypto";
  CREATE EXTENSION IF NOT EXISTS "hstore";
  
  -- Notify completion
  NOTIFY pgrst, 'reload schema';
EOSQL

# Generate SCRAM hash for PgBouncer
echo "Generating SCRAM hash for PgBouncer..."
./scripts/generate_scram_hash.sh "$DB_USER" "$DB_PASS"

echo "Database initialization complete!"
