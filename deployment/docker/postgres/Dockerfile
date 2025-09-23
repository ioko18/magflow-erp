FROM postgres:16-alpine

# Create directories for SSL certificates
RUN mkdir -p /var/lib/postgresql/certs

# Copy SSL certificates
COPY certs/pgbouncer.crt /var/lib/postgresql/server.crt
COPY certs/pgbouncer.key /var/lib/postgresql/server.key
COPY certs/ca/ca.crt /var/lib/postgresql/ca.crt

# Set permissions
RUN chown -R postgres:postgres /var/lib/postgresql/certs \
    && chmod 600 /var/lib/postgresql/server.* \
    && chmod 644 /var/lib/postgresql/ca.crt

# Copy custom configuration
COPY docker/postgres/postgresql.conf /etc/postgresql/postgresql.conf
COPY docker/postgres/pg_hba.conf /etc/postgresql/pg_hba.conf

# Set the command to use our custom configuration
CMD ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf"]
