# SLO Alert Runbooks

This document provides detailed runbooks for responding to SLO-related alerts in the MagFlow system.

## Table of Contents

1. [HighLatencyFastBurn](#highlatencyfastburn)
1. [HighLatencySlowBurn](#highlatencyslowburn)
1. [HighErrorRateFastBurn](#higherrorratefastburn)
1. [HighErrorRateSlowBurn](#higherrorrateslowburn)
1. [ServiceDegraded](#servicedegraded)

## HighLatencyFastBurn

**Severity**: Page (P1)
**Alert Description**: p95 latency > 300ms for 5 minutes (14.4x burn rate)

### Immediate Actions

1. **Check Dashboard**

   - Review the [SLO Dashboard](http://localhost:3000/d/magflow/magflow-slos) for latency spikes
   - Identify affected endpoints and services
   - Check for recent deployments or configuration changes

1. **Check System Resources**

   ```bash
   # Check CPU/Memory usage
   docker stats

   # Check PostgreSQL performance
   docker compose exec db psql -U postgres -c "SELECT * FROM pg_stat_activity WHERE state = 'active'"
   ```

1. **Check Logs**

   ```bash
   # Check application logs for errors
   docker compose logs --tail=100 app

   # Check database logs
   docker compose logs --tail=100 db
   ```

### Resolution Steps

1. **If Caused by Traffic Spike**

   - Scale up application instances
   - Check if auto-scaling is working as expected
   - Consider implementing rate limiting for abusive clients

1. **If Caused by Database Issues**

   - Check for long-running queries
   - Verify database connection pool settings
   - Check for table/index bloat

1. **If Caused by Application Issues**

   - Roll back recent deployments if needed
   - Check for memory leaks
   - Review recent code changes

### Post-Mortem Required

- Yes, if the issue caused significant user impact
- Document root cause and remediation steps

______________________________________________________________________

## HighLatencySlowBurn

**Severity**: Ticket (P2)
**Alert Description**: p95 latency > 300ms for 1 hour (3.6x burn rate)

### Immediate Actions

1. **Review Historical Data**

   - Check if this is a recurring pattern
   - Compare with business hours/peak usage times

1. **Check for Resource Saturation**

   - Database CPU/memory usage
   - Disk I/O metrics
   - Network latency between services

### Resolution Steps

1. **Performance Tuning**

   - Optimize slow queries
   - Add database indexes if needed
   - Review connection pool settings

1. **Architecture Review**

   - Consider read replicas for read-heavy workloads
   - Implement caching for frequently accessed data
   - Review service dependencies

### Post-Mortem Required

- If issue persists after initial fixes
- Document findings and long-term solutions

______________________________________________________________________

## HighErrorRateFastBurn

**Severity**: Page (P1)
**Alert Description**: Error rate > 1.44% for 5 minutes (14.4x burn rate)

### Immediate Actions

1. **Check Error Types**

   - Review error logs for patterns
   - Identify if errors are from specific endpoints or services
   - Check for 5xx vs 4xx errors

1. **Check Dependencies**

   - Verify status of external services
   - Check database connectivity
   - Verify cache health

### Resolution Steps

1. **For 5xx Errors**

   - Check application logs for stack traces
   - Review recent deployments
   - Consider rolling back if needed

1. **For 4xx Errors**

   - Check for client-side issues
   - Validate API contracts
   - Review authentication/authorization logs

### Post-Mortem Required

- For all production incidents
- Document error patterns and fixes

______________________________________________________________________

## HighErrorRateSlowBurn

**Severity**: Ticket (P2)
**Alert Description**: Error rate > 0.36% for 1 hour (3.6x burn rate)

### Immediate Actions

1. **Trend Analysis**

   - Check if error rate is increasing
   - Identify affected user segments
   - Review recent changes

1. **Impact Assessment**

   - Determine business impact
   - Check if critical workflows are affected

### Resolution Steps

1. **Long-term Fixes**

   - Implement better error handling
   - Add retry logic for transient failures
   - Improve monitoring for affected components

1. **Documentation**

   - Update runbooks with new findings
   - Add tests to catch similar issues

### Post-Mortem Required

- If error rate remains elevated
- Document systemic issues and solutions

______________________________________________________________________

## ServiceDegraded

**Severity**: Page (P1)
**Alert Description**: Service is down or severely degraded

### Immediate Actions

1. **Service Status**

   - Check if containers are running
   - Verify service health endpoints
   - Check for crash loops

1. **Infrastructure**

   - Check host resources
   - Verify network connectivity
   - Check storage availability

### Resolution Steps

1. **Service Recovery**

   - Restart failed containers
   - Check for resource constraints
   - Verify configuration changes

1. **Failover**

   - Initiate failover if applicable
   - Verify backup systems

### Post-Mortem Required

- For all incidents
- Document timeline and resolution steps

______________________________________________________________________

## General Troubleshooting Commands

### Database Queries

```sql
-- Check for locks
SELECT blocked_locks.pid AS blocked_pid,
       blocked_activity.usename AS blocked_user,
       blocking_locks.pid AS blocking_pid,
       blocking_activity.usename AS blocking_user,
       blocked_activity.query AS blocked_statement
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks 
    ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.DATABASE IS NOT DISTINCT FROM blocked_locks.DATABASE
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.GRANTED;

-- Check for long-running queries
SELECT pid, now() - query_start AS duration, query, state
FROM pg_stat_activity 
WHERE now() - query_start > '5 minutes'::interval
ORDER BY duration DESC;
```

### Docker Commands

```bash
# View logs
sudo docker compose logs -f --tail=100 app

# Restart services
sudo docker compose restart app

# Check container stats
docker stats

# Get shell in container
docker compose exec app bash
```

### Redis Commands

```bash
# Check Redis status
docker compose exec redis redis-cli info

# Check keys
docker compose exec redis redis-cli --scan --pattern '*'

# Flush cache (use with caution)
docker compose exec redis redis-cli FLUSHALL
```

## Escalation Path

1. Primary On-call: @team-lead
1. Secondary On-call: @senior-dev
1. Engineering Manager: @eng-manager

## Maintenance Windows

- Regular maintenance: Sundays 02:00-04:00 UTC
- Emergency changes: As needed with manager approval
