#!/bin/sh
# Health check script for PgBouncer
PGPASSWORD=${DB_PASS:-app_password_change_me} psql -h 127.0.0.1 -p 6432 -U ${DB_USER:-app} -d ${DB_NAME:-magflow} -c "SELECT 1;" -t
