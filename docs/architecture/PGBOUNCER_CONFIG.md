# PgBouncer Configuration Guide

## Overview
PgBouncer is a lightweight connection pooler for PostgreSQL, used to manage and optimize database connections in the MagFlow application.

## Key Features
- Connection pooling for better resource utilization
- TLS/SSL encryption for secure connections
- Support for prepared statements
- Connection routing and load balancing
- Authentication and access control

## Configuration

### Core Settings
```ini
[pgbouncer]
# Network
listen_addr = 0.0.0.0
listen_port = 6432

# Authentication
auth_type = md5
auth_file = /opt/bitnami/pgbouncer/conf/userlist.txt

# Connection Pooling
pool_mode = transaction
max_client_conn = 500
default_pool_size = 50
min_pool_size = 10
reserve_pool_size = 10
max_db_connections = 100

# Timeouts
server_connect_timeout = 15
server_idle_timeout = 600
query_wait_timeout = 120

# Prepared Statements
max_prepared_statements = 200
server_reset_query = DISCARD ALL

# TLS Configuration
client_tls_sslmode = require
server_tls_sslmode = verify-full
```

## Security

### Authentication
1. **User Authentication**
   - Configured via `auth_file` with MD5 hashed passwords
   - Example user entry: `"app" "md53175bce1d3201d16594cebf9d7eb3f9d"`

2. **TLS/SSL**
   - Client connections: TLS 1.2+ with strong ciphers
   - Backend connections: Full TLS verification
   - Certificate-based authentication

### Network Security
- Firewall rules to restrict access
- Running as non-root user
- Minimal required privileges

## Performance Tuning

### Connection Pooling
- **Pool Modes**
  - `session`: One server per client connection
  - `transaction`: Server assigned per transaction (default)
  - `statement`: Server assigned per statement (not recommended)

### Monitoring
- Built-in stats via `SHOW STATS`
- Logging of connections/disconnections
- Query timing metrics

## High Availability

### Load Balancing
- `server_round_robin = 1` for even distribution
- Multiple PgBouncer instances behind a load balancer

### Failover
- Automatic reconnection to standby servers
- Health checks with `server_check_delay`

## Common Issues

### Connection Issues
- **Too many connections**
  - Increase `max_client_conn` or optimize connection usage
  - Check for connection leaks in application code

### Performance Problems
- **High latency**
  - Adjust pool sizes
  - Check `query_wait_timeout`
  - Monitor `SHOW POOLS` for connection queueing

## Maintenance

### Commands
```sql
-- Show connections
SHOW CLIENTS;
SHOW SERVERS;

-- Pool status
SHOW POOLS;

-- Statistics
SHOW STATS;
SHOW STATS_TOTALS;
```

### Logging
- Connection attempts
- Query errors
- Pool statistics

## Best Practices

1. **Connection Management**
   - Use connection pooling in your application
   - Set appropriate timeouts
   - Implement retry logic for transient failures

2. **Security**
   - Always use TLS for production
   - Regularly rotate credentials
   - Monitor for suspicious activity

3. **Performance**
   - Monitor connection pool metrics
   - Adjust pool sizes based on workload
   - Use prepared statements for repeated queries

## Troubleshooting

### Common Errors
- **"sorry, too many clients already"**
  - Check `max_client_conn` and `max_db_connections`
  - Look for connection leaks

- **TLS handshake failures**
  - Verify certificate permissions
  - Check cipher suite compatibility

### Log Analysis
- Check PgBouncer logs for errors
- Monitor system resource usage
- Review query performance

## References
- [PgBouncer Documentation](https://www.pgbouncer.org/)
- [PostgreSQL Connection Pooling](https://www.postgresql.org/docs/current/pgbouncer.html)
- [TLS Configuration Guide](https://www.postgresql.org/docs/current/libpq-ssl.html)
