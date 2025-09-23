FROM bitnami/pgbouncer:1.21.0

# Switch to root to set permissions
USER root

# Install additional tools for debugging, SSL and PostgreSQL client
RUN install_packages inetutils-ping net-tools iproute2 ca-certificates openssl postgresql-client \
    && update-ca-certificates

# Create the 1001 user and group
RUN groupadd -r pgbouncer -g 1001 \
    && useradd -u 1001 -r -g pgbouncer -d /opt/bitnami/pgbouncer -s /sbin/nologin -c "PgBouncer user" pgbouncer

# Create necessary directories with proper permissions
RUN mkdir -p /opt/bitnami/pgbouncer/conf/ \
    && mkdir -p /opt/bitnami/pgbouncer/certs/ \
    && chown -R pgbouncer:pgbouncer /opt/bitnami/pgbouncer \
    && chmod -R 775 /opt/bitnami/pgbouncer \
    && chmod 600 /opt/bitnami/pgbouncer/certs/*.key 2>/dev/null || true

# Copy configuration files and healthcheck script
COPY docker/pgbouncer/pgbouncer.ini /opt/bitnami/pgbouncer/conf/
COPY docker/pgbouncer/userlist.txt /opt/bitnami/pgbouncer/conf/
COPY docker/pgbouncer/healthcheck.sh /opt/bitnami/pgbouncer/bin/healthcheck.sh

# Set execute permissions and switch to non-root user
RUN chmod +x /opt/bitnami/pgbouncer/bin/healthcheck.sh && \
    chown -R pgbouncer:pgbouncer /opt/bitnami/pgbouncer

# Switch to non-root user
USER 1001

# Set up health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD ["/opt/bitnami/pgbouncer/bin/healthcheck.sh"]

# Set environment variables for SSL
ENV PGBOUNCER_SET_CLIENT_ENCODING=yes \
    PGBOUNCER_LOG_CONNECTIONS=on \
    PGBOUNCER_LOG_DISCONNECTIONS=on \
    PGBOUNCER_LOG_POOLER_ERRORS=on \
    PGBOUNCER_STATS_PERIOD=60 \
    PGBOUNCER_VERBOSE=1

# Set the entrypoint to directly run PgBouncer
ENTRYPOINT ["/opt/bitnami/pgbouncer/bin/pgbouncer", "-u", "pgbouncer", "-v", "/opt/bitnami/pgbouncer/conf/pgbouncer.ini"]

# Expose PgBouncer port
EXPOSE 6432
