# Use specific version for reproducibility
FROM bitnami/pgbouncer:1.21.0

# Set environment variables
ENV PGBOUNCER_DATABASE="postgres" \
    PGBOUNCER_AUTH_TYPE="scram-sha-256" \
    PGBOUNCER_IGNORE_STARTUP_PARAMETERS="extra_float_digits" \
    PGBOUNCER_POOL_MODE="transaction" \
    PGBOUNCER_MAX_CLIENT_CONN="1000" \
    PGBOUNCER_DEFAULT_POOL_SIZE="20" \
    PGBOUNCER_MIN_POOL_SIZE="5" \
    PGBOUNCER_RESERVE_POOL_SIZE="5" \
    PGBOUNCER_MAX_DB_CONNECTIONS="100" \
    PGBOUNCER_MAX_USER_CONNECTIONS="100" \
    PGBOUNCER_STATS_PERIOD="60" \
    PGBOUNCER_SERVER_RESET_QUERY="DISCARD ALL" \
    PGBOUNCER_SERVER_RESET_QUERY_ALWAYS="0" \
    PGBOUNCER_DISABLE_PQEXEC="0" \
    PGBOUNCER_APPLICATION_NAME_ADD_HOST="1" \
    PGBOUNCER_CONNECT_QUERY="SELECT 1"

# Copy configuration files
COPY docker/pgbouncer/pgbouncer.ini /opt/bitnami/pgbouncer/conf/
COPY docker/pgbouncer/userlist.txt /opt/bitnami/pgbouncer/conf/

# Set permissions

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
  CMD pg_isready -h localhost -p 6432 -d ${POSTGRESQL_DATABASE:-postgres} -U ${POSTGRESQL_USERNAME:-postgres}

# Expose PgBouncer port
EXPOSE 6432

# Run as non-root user
USER 1001

# Set entrypoint
ENTRYPOINT ["/opt/bitnami/scripts/pgbouncer/entrypoint.sh"]
CMD ["/opt/bitnami/scripts/pgbouncer/run.sh"]
