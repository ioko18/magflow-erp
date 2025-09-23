#!/bin/bash
set -e

# Load environment variables
source .env

# Function to check if PostgreSQL is ready
wait_for_postgres() {
    echo "Waiting for PostgreSQL to be ready..."
    until PGPASSWORD=$DB_PASS psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" >/dev/null 2>&1; do
        echo "Waiting for PostgreSQL..."
        sleep 1
    done
}

# Function to enable SCRAM authentication in PostgreSQL
setup_postgres_scram() {
    echo "Setting up SCRAM authentication in PostgreSQL..."

    # Set password encryption to SCRAM
    PGPASSWORD=$DB_PASS psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" <<-EOSQL
        -- Set password encryption to SCRAM
        ALTER SYSTEM SET password_encryption = 'scram-sha-256';
        SELECT pg_reload_conf();

        -- Create a role for PgBouncer if it doesn't exist
        DO \$\$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pgbouncer') THEN
                CREATE ROLE pgbouncer WITH LOGIN PASSWORD '${PGBOUNCER_PASSWORD:-ChangeMe123!}';
            END IF;
        END
        \$\$;

        -- Grant necessary permissions
        GRANT pg_monitor TO pgbouncer;

        -- Update existing user passwords to use SCRAM
        DO \$\$
        DECLARE
            user_record RECORD;
        BEGIN
            FOR user_record IN SELECT usename FROM pg_user WHERE usename = '${DB_USER}'
            LOOP
                EXECUTE format('ALTER USER %I WITH PASSWORD %L',
                             user_record.usename,
                             '${DB_PASS}');
            END LOOP;
        END
        \$\$;
EOSQL
}

# Function to update PgBouncer configuration
update_pgbouncer_config() {
    echo "Updating PgBouncer configuration..."

    # Create userlist.txt with SCRAM verifiers
    cat > docker/pgbouncer/userlist.txt <<-EOL
        "${DB_USER}" "SCRAM-SHA-256$$(pgbouncer -v | grep -oP '(?<=scram_get_verifier\()[^)]+' | xargs -I{} bash -c "echo '\$pbkdf2-sha256\$$(echo -n '${DB_PASS}' | base64 | tr -d '\n')'" | tr -d '\n')"
EOL

    # Update pgbouncer.ini to use auth_query
    sed -i.bak -E '/^auth_type =/c\
auth_type = scram-sha-256
# auth_file = /etc/pgbouncer/userlist.txt  # Uncomment for file-based auth
auth_query = SELECT usename, passwd FROM pg_shadow WHERE usename = \$1' docker/pgbouncer/pgbouncer.ini
}

# Main execution
wait_for_postgres
setup_postgres_scram
update_pgbouncer_config

echo "SCRAM authentication setup complete. Restarting PgBouncer..."
docker compose restart pgbouncer

echo "Verifying SCRAM authentication..."
if PGPASSWORD="$DB_PASS" psql -h localhost -p 6432 -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" &>/dev/null; then
    echo "✅ SCRAM authentication is working correctly!"
else
    echo "❌ SCRAM authentication failed. Please check the configuration."
    exit 1
fi
