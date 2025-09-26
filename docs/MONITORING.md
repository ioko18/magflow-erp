# MagFlow ERP - Monitoring & Troubleshooting Guide

[![Prometheus](https://img.shields.io/badge/Prometheus-Ready-orange.svg)](https://prometheus.io/)
[![Grafana](https://img.shields.io/badge/Grafana-Ready-blue.svg)](https://grafana.com/)
[![ELK Stack](https://img.shields.io/badge/ELK-Stack-green.svg)](https://www.elastic.co/elastic-stack/)

Comprehensive monitoring and troubleshooting guide for MagFlow ERP system.

## 📋 Table of Contents

- [Monitoring Overview](#monitoring-overview)
- [Health Checks](#health-checks)
- [Metrics & Analytics](#metrics--analytics)
- [Logging System](#logging-system)
- [Alerting](#alerting)
- [Performance Monitoring](#performance-monitoring)
- [Troubleshooting](#troubleshooting)
- [Common Issues](#common-issues)
- [Debug Mode](#debug-mode)
- [Backup & Recovery](#backup--recovery)

## 📊 Monitoring Overview

### Monitoring Architecture

#### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Application   │────│   Prometheus    │────│    Grafana      │
│   (FastAPI)     │    │   Metrics       │    │   Dashboards    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │────│   PgExporter    │────│   Logs &        │
│   Database      │    │   Metrics       │    │   Metrics       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Redis       │────│   RedisExporter │────│   AlertManager  │
│     Cache       │    │   Metrics       │    │   Alerts        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

#### Monitoring Stack

- **Application Metrics**: Prometheus-compatible endpoints
- **Database Monitoring**: PostgreSQL exporter and pg_stat_statements
- **Cache Monitoring**: Redis exporter and info commands
- **External Services**: Health checks for eMAG API
- **Logs**: Structured logging with JSON format
- **Dashboards**: Grafana with pre-built dashboards
- **Alerts**: Prometheus AlertManager with notification channels

### Key Metrics

#### Application Metrics

- **Request Rate**: HTTP requests per second
- **Response Time**: Average response time by endpoint
- **Error Rate**: 4xx/5xx responses percentage
- **Active Users**: Concurrent authenticated users
- **Database Connections**: Connection pool usage
- **Memory Usage**: Memory consumption by service
- **CPU Usage**: CPU utilization percentage

#### Business Metrics

- **Sales Volume**: Daily/monthly sales totals
- **Inventory Turnover**: Stock movement velocity
- **Customer Activity**: Active customers count
- **Order Processing**: Order fulfillment rate
- **Purchase Efficiency**: Purchase order processing time

## 🔍 Health Checks

### Health Check Endpoints

#### Basic Health Check

```bash
curl http://localhost:8000/health
```

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0"
}
```

#### Detailed Health Check

```bash
curl http://localhost:8000/health/detailed
```

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "checks": {
    "database": {
      "status": "healthy",
      "response_time": 12.3,
      "connections": {
        "active": 5,
        "idle": 15,
        "total": 20
      }
    },
    "redis": {
      "status": "healthy",
      "response_time": 1.2
    },
    "external_apis": {
      "emag": {
        "status": "healthy",
        "response_time": 150.5
      }
    }
  },
  "system": {
    "memory_usage": 45.2,
    "cpu_usage": 23.1,
    "disk_usage": 67.8
  }
}
```

#### Database Health Check

```bash
curl http://localhost:8000/health/database
```

**Response:**

```json
{
  "status": "healthy",
  "database": {
    "connection_count": 20,
    "active_connections": 5,
    "idle_connections": 15,
    "max_connections": 100,
    "response_time": 12.3,
    "queries_per_second": 45.2,
    "slow_queries": 0
  },
  "tables": {
    "users": {"rows": 1250, "size": "1.2MB"},
    "inventory_items": {"rows": 5600, "size": "3.4MB"},
    "sales_orders": {"rows": 890, "size": "2.1MB"}
  }
}
```

#### External Services Health

```bash
curl http://localhost:8000/health/external
```

**Response:**

```json
{
  "status": "healthy",
  "external_services": {
    "emag_api": {
      "status": "healthy",
      "response_time": 145.2,
      "last_check": "2024-01-15T10:29:45Z",
      "error_rate": 0.02
    }
  }
}
```

### Kubernetes Health Checks

#### Liveness Probe

```yaml
# deployment/kubernetes/health-liveness.yml
apiVersion: v1
kind: ConfigMap
metadata:
  name: health-check-config
data:
  liveness.sh: |
    #!/bin/bash
    curl -f http://localhost:8000/health/live || exit 1
```

#### Readiness Probe

```yaml
# deployment/kubernetes/health-readiness.yml
apiVersion: v1
kind: ConfigMap
metadata:
  name: readiness-check-config
data:
  readiness.sh: |
    #!/bin/bash
    curl -f http://localhost:8000/health/ready || exit 1
```

#### Startup Probe

```yaml
# deployment/kubernetes/health-startup.yml
apiVersion: v1
kind: ConfigMap
metadata:
  name: startup-check-config
data:
  startup.sh: |
    #!/bin/bash
    # Wait for application to start
    for i in {1..30}; do
      if curl -f http://localhost:8000/health/startup 2>/dev/null; then
        exit 0
      fi
      sleep 2
    done
    exit 1
```

## 📈 Metrics & Analytics

### Prometheus Metrics

#### Application Metrics Endpoint

```bash
curl http://localhost:8000/metrics
```

**Sample Output:**

```
# HELP http_requests_total Total number of HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/v1/inventory",status="200"} 1250
http_requests_total{method="POST",endpoint="/api/v1/sales-orders",status="201"} 89
http_requests_total{method="GET",endpoint="/health",status="200"} 4500

# HELP http_request_duration_seconds HTTP request duration in seconds
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{method="GET",endpoint="/api/v1/inventory",le="0.1"} 1180
http_request_duration_seconds_bucket{method="GET",endpoint="/api/v1/inventory",le="0.5"} 65
http_request_duration_seconds_bucket{method="GET",endpoint="/api/v1/inventory",le="1.0"} 5

# HELP database_connections_active Number of active database connections
# TYPE database_connections_active gauge
database_connections_active 5

# HELP redis_connections Number of Redis connections
# TYPE redis_connections gauge
redis_connections 3
```

#### Prometheus Configuration

```yaml
# monitoring/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alerts.yml"

scrape_configs:
  - job_name: 'magflow-erp'
    static_configs:
      - targets: ['magflow-erp:8000']
    metrics_path: /metrics
    scrape_interval: 5s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
    scrape_interval: 30s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
    scrape_interval: 30s

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
    scrape_interval: 30s
```

### Grafana Dashboards

#### Main Dashboard

- **Request Rate**: HTTP requests per second
- **Response Times**: Average response time by endpoint
- **Error Rates**: 4xx/5xx error percentages
- **Database Performance**: Connection pool and query performance
- **Memory Usage**: Memory consumption over time
- **Active Users**: Concurrent user sessions

#### Database Dashboard

- **Connection Pool**: Active vs idle connections
- **Query Performance**: Slow queries and execution times
- **Table Sizes**: Row counts and disk usage
- **Index Usage**: Index hit rates and unused indexes
- **Lock Monitoring**: Database locks and wait times

#### Business Metrics Dashboard

- **Sales Volume**: Daily/monthly sales totals
- **Inventory Levels**: Stock levels and turnover rates
- **Customer Activity**: Active customers and order frequency
- **Purchase Orders**: Supplier performance and lead times

## 📋 Logging System

### Structured Logging

#### Log Format

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "INFO",
  "module": "app.api.v1.endpoints.inventory",
  "function": "get_inventory",
  "line": 45,
  "message": "Retrieved inventory items",
  "user_id": 123,
  "request_id": "req-abc-123",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "method": "GET",
  "endpoint": "/api/v1/inventory",
  "status_code": 200,
  "response_time": 125.3,
  "items_count": 45
}
```

#### Log Levels

- **DEBUG**: Detailed debugging information
- **INFO**: General information about application flow
- **WARNING**: Potentially harmful situations
- **ERROR**: Error conditions that don't stop execution
- **CRITICAL**: Critical errors that require immediate attention

### Log Configuration

#### Application Logging

```python
# app/core/logging.py
import logging
import sys
from typing import Dict, Any

def setup_logging(log_level: str = "INFO") -> None:
    """Setup structured JSON logging."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def get_logger(name: str) -> logging.Logger:
    """Get logger with structured formatting."""
    logger = logging.getLogger(name)
    return logger

# Structured log record
def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    extra: Dict[str, Any] = None
):
    """Log with structured context."""
    if extra:
        logger.log(getattr(logging, level.upper()), message, extra=extra)
    else:
        logger.log(getattr(logging, level.upper()), message)
```

#### Docker Logging

```yaml
# docker-compose.yml
services:
  app:
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "5"
    environment:
      - LOG_FORMAT=json
      - LOG_LEVEL=INFO
```

### Log Analysis

#### Query Logs

```bash
# View recent errors
tail -f logs/app.log | jq '.level == "ERROR"'

# Search for specific user activity
cat logs/app.log | jq 'select(.user_id == 123)'

# Analyze request patterns
cat logs/app.log | jq '.endpoint' | sort | uniq -c

# Check response times
cat logs/app.log | jq '[.response_time] | sort | reverse | .[0:10]'
```

#### ELK Stack Integration

```yaml
# deployment/logging/elasticsearch.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: elasticsearch
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: elasticsearch
        image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
        env:
        - name: discovery.type
          value: single-node
        volumeMounts:
        - name: data
          mountPath: /usr/share/elasticsearch/data
      volumes:
      - name: data
        emptyDir: {}

---
# deployment/logging/logstash.yml
apiVersion: apps/v1
kind: ConfigMap
metadata:
  name: logstash-config
data:
  logstash.conf: |
    input {
      file {
        path => "/var/log/containers/*magflow*.log"
        codec => "json"
      }
    }

    filter {
      json {
        source => "message"
      }
    }

    output {
      elasticsearch {
        hosts => ["elasticsearch:9200"]
        index => "magflow-logs-%{+YYYY.MM.dd}"
      }
    }
```

## 🚨 Alerting

### Alert Rules

#### Application Alerts

```yaml
# monitoring/alerts/application-alerts.yml
groups:
- name: magflow_application_alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
    for: 5m
    labels:
      severity: warning
      service: magflow-erp
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value | printf "%.2f" }}% for the last 5 minutes"

  - alert: HighResponseTime
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
    for: 10m
    labels:
      severity: warning
      service: magflow-erp
    annotations:
      summary: "High response time detected"
      description: "95th percentile response time is {{ $value | printf "%.2f" }}s"

  - alert: DatabaseConnectionPoolExhausted
    expr: database_connections_active > 18
    for: 2m
    labels:
      severity: critical
      service: magflow-erp
    annotations:
      summary: "Database connection pool exhausted"
      description: "Active connections: {{ $value }} out of 20"
```

#### Database Alerts

```yaml
# monitoring/alerts/database-alerts.yml
groups:
- name: magflow_database_alerts
  rules:
  - alert: DatabaseConnectionsHigh
    expr: pg_stat_activity_count > 80
    for: 5m
    labels:
      severity: warning
      service: postgresql
    annotations:
      summary: "High database connections"
      description: "Database connections: {{ $value }} out of 100"

  - alert: SlowQueries
    expr: increase(pg_stat_statements_calls{query=~".*", mean_time=">1"}[5m]) > 10
    for: 5m
    labels:
      severity: warning
      service: postgresql
    annotations:
      summary: "Slow queries detected"
      description: "Number of slow queries increased"

  - alert: DatabaseDown
    expr: up{job="postgres"} == 0
    for: 1m
    labels:
      severity: critical
      service: postgresql
    annotations:
      summary: "Database is down"
      description: "PostgreSQL database is not responding"
```

#### Business Alerts

```yaml
# monitoring/alerts/business-alerts.yml
groups:
- name: magflow_business_alerts
  rules:
  - alert: LowInventory
    expr: inventory_stock_quantity < inventory_min_stock_level
    for: 15m
    labels:
      severity: warning
      service: magflow-erp
    annotations:
      summary: "Low inventory alert"
      description: "Item {{ $labels.item_name }} has low stock"

  - alert: SalesDrop
    expr: rate(sales_orders_total[1h]) < 0.5 * rate(sales_orders_total[24h])
    for: 2h
    labels:
      severity: info
      service: magflow-erp
    annotations:
      summary: "Sales drop detected"
      description: "Sales rate dropped significantly"

  - alert: FailedPayments
    expr: rate(payment_failures_total[15m]) > 3
    for: 15m
    labels:
      severity: critical
      service: magflow-erp
    annotations:
      summary: "Payment failures spike"
      description: "Multiple payment failures detected"
```

### Notification Channels

#### Email Notifications

```yaml
# alertmanager/config.yml
route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'email-notifications'

receivers:
- name: 'email-notifications'
  email_configs:
  - to: 'alerts@magflow-erp.com'
    from: 'alertmanager@magflow-erp.com'
    smarthost: 'smtp.gmail.com:587'
    auth_username: 'alerts@magflow-erp.com'
    auth_password: 'your-app-password'
    send_resolved: true
```

#### Slack Notifications

```yaml
# alertmanager/config.yml
receivers:
- name: 'slack-notifications'
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
    channel: '#alerts'
    send_resolved: true
    title: 'MagFlow ERP Alert'
    text: |
      {{ range .Alerts }}{{ .Annotations.summary }}
      {{ .Annotations.description }}
      {{ end }}
```

#### PagerDuty Integration

```yaml
# alertmanager/config.yml
receivers:
- name: 'pagerduty-notifications'
  pagerduty_configs:
  - service_key: 'your-pagerduty-service-key'
    send_resolved: true
    description: |
      {{ range .Alerts }}{{ .Annotations.summary }}
      {{ .Annotations.description }}
      {{ end }}
```

## ⚡ Performance Monitoring

### Application Performance

#### Memory Usage Monitoring

```python
# app/services/performance_monitor.py
import psutil
import os
from typing import Dict, Any

async def get_memory_usage() -> Dict[str, Any]:
    """Get detailed memory usage information."""
    process = psutil.Process(os.getpid())

    memory_info = process.memory_info()
    memory_percent = process.memory_percent()

    return {
        "rss": memory_info.rss / 1024 / 1024,  # MB
        "vms": memory_info.vms / 1024 / 1024,  # MB
        "percent": memory_percent,
        "swap": psutil.swap_memory().percent
    }

async def get_cpu_usage() -> Dict[str, Any]:
    """Get CPU usage information."""
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "cpu_count": psutil.cpu_count(),
        "cpu_count_logical": psutil.cpu_count(logical=True)
    }
```

#### Database Performance

```python
# app/services/database_monitor.py
from sqlalchemy import text
from app.core.database import engine
from typing import Dict, Any

async def get_database_metrics() -> Dict[str, Any]:
    """Get comprehensive database performance metrics."""
    async with engine.begin() as conn:
        # Connection pool stats
        pool_status = await conn.execute(text("""
            SELECT
                COUNT(*) as total_connections,
                COUNT(*) FILTER (WHERE state = 'active') as active_connections,
                COUNT(*) FILTER (WHERE state = 'idle') as idle_connections,
                COUNT(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
            FROM pg_stat_activity
            WHERE datname = current_database()
        """))

        pool_row = pool_status.fetchone()

        # Query performance stats
        query_stats = await conn.execute(text("""
            SELECT
                query,
                calls,
                total_time,
                mean_time,
                rows
            FROM pg_stat_statements
            WHERE calls > 10
            ORDER BY mean_time DESC
            LIMIT 10
        """))

        slow_queries = query_stats.fetchall()

        return {
            "connections": {
                "total": pool_row.total_connections,
                "active": pool_row.active_connections,
                "idle": pool_row.idle_connections,
                "idle_in_transaction": pool_row.idle_in_transaction
            },
            "slow_queries": [
                {
                    "query": row.query[:50] + "...",
                    "calls": row.calls,
                    "total_time": row.total_time,
                    "mean_time": row.mean_time,
                    "rows": row.rows
                }
                for row in slow_queries
            ]
        }
```

### System Monitoring

#### Docker Monitoring

```bash
# Monitor container resource usage
docker stats

# Check container logs
docker-compose logs -f app

# Monitor specific container
docker-compose exec app top

# Check container health
docker inspect magflow-erp_app | jq '.[0].State.Health'
```

#### Kubernetes Monitoring

```bash
# Check pod status
kubectl get pods -o wide

# Check resource usage
kubectl top pods
kubectl top nodes

# Monitor pod logs
kubectl logs -f magflow-erp-xxxxx-yyyyy

# Check pod events
kubectl describe pod magflow-erp-xxxxx-yyyyy

# Monitor horizontal pod autoscaler
kubectl get hpa
kubectl describe hpa magflow-erp-hpa
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Database Connection Issues

```bash
# Check database connectivity
python -c "from app.db.base import engine; print('Database connected')"

# Check PostgreSQL service status
sudo systemctl status postgresql

# Verify database URL
echo $DATABASE_URL

# Check database logs
tail -f /var/log/postgresql/postgresql-15-main.log

# Test manual connection
psql -h localhost -U magflow -d magflow
```

**Solutions:**

- Verify database credentials in `.env`
- Check if PostgreSQL service is running
- Ensure database server is accessible
- Check firewall settings

#### 2. Redis Connection Issues

```bash
# Test Redis connection
redis-cli ping

# Check Redis configuration
redis-cli config get maxmemory
redis-cli info memory

# Monitor Redis logs
tail -f /var/log/redis/redis-server.log
```

**Solutions:**

- Verify Redis URL in `.env`
- Check Redis service status
- Ensure Redis is running on correct port
- Check memory limits and eviction policy

#### 3. Application Startup Issues

```bash
# Check Python syntax
python -m py_compile app/main.py

# Test import
python -c "import app.main"

# Check environment variables
python -c "from app.core.config import settings; print('Config loaded')"

# Test database connection
python -c "from app.db.base import get_db; print('Database ready')"
```

**Solutions:**

- Fix syntax errors in Python files
- Install missing dependencies
- Verify environment configuration
- Check database connectivity

#### 4. Performance Issues

```bash
# Monitor memory usage
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory: {process.memory_info().rss / 1024 / 1024:.1f}MB')
print(f'CPU: {process.cpu_percent()}%')
"

# Check database performance
python scripts/database_metrics.py

# Monitor slow queries
tail -f logs/app.log | grep "response_time"
```

**Solutions:**

- Optimize database queries
- Add proper indexing
- Implement caching
- Scale horizontally

#### 5. Authentication Issues

```bash
# Test login endpoint
curl -X POST "http://localhost:8000/api/v1/auth/access-token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin"

# Check JWT token
python -c "
import jwt
from app.core.config import settings
token = 'your-token-here'
decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
print(decoded)
"
```

**Solutions:**

- Verify user credentials
- Check JWT secret key
- Validate token expiration
- Review authentication middleware

### Debug Mode

#### Enable Debug Logging

```bash
# Set environment variables
export LOG_LEVEL=DEBUG
export SQL_ECHO=1

# Start application with debug
uvicorn app.main:app --reload --log-level debug
```

#### Debug Database Queries

```python
# Enable SQL query logging
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Test specific queries
from app.crud.user import user_crud
from app.db.base import get_db

async def debug_queries():
    async for session in get_db():
        # This will log all SQL queries
        users = await user_crud.get_multi(session)
        break
```

#### Debug API Endpoints

```bash
# Use verbose curl
curl -v -X GET "http://localhost:8000/api/v1/inventory/" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Use HTTPie for better output
http GET localhost:8000/api/v1/inventory/ Authorization:"Bearer YOUR_TOKEN"

# Use browser developer tools
# Visit: http://localhost:8000/docs (Swagger UI)
```

### Development Tools

#### Profiling Tools

```python
# app/debug/profiler.py
import cProfile
import pstats
from functools import wraps

def profile_function(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        pr = cProfile.Profile()
        pr.enable()
        result = func(*args, **kwargs)
        pr.disable()

        stats = pstats.Stats(pr)
        stats.sort_stats('cumulative')
        stats.print_stats(20)
        return result
    return wrapper

# Usage
@profile_function
async def slow_function():
    # Your code here
    pass
```

#### Memory Profiling

```python
# app/debug/memory_profiler.py
import tracemalloc
from typing import Any

async def profile_memory(func):
    """Profile memory usage of async function."""
    tracemalloc.start()

    snapshot1 = tracemalloc.take_snapshot()
    result = await func()
    snapshot2 = tracemalloc.take_snapshot()

    top_stats = snapshot2.compare_to(snapshot1, 'lineno')
    print("[ Memory Usage ]")
    for stat in top_stats[:10]:
        print(stat)

    return result
```

#### Query Analysis

```python
# app/debug/query_analyzer.py
from sqlalchemy import event
from typing import Any

def log_queries():
    """Log all SQL queries."""
    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        print(f"SQL: {statement}")
        print(f"Parameters: {parameters}")

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        print(f"Rows affected: {cursor.rowcount}")
```

## 💾 Backup & Recovery

### Database Backup

#### Automated Backup Script

```bash
#!/bin/bash
# scripts/backup-database.sh

BACKUP_DIR="/var/backups/magflow"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="magflow_backup_$TIMESTAMP.sql.gz"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Create database backup
pg_dump magflow | gzip > $BACKUP_DIR/$FILENAME

# Keep only last 7 days of backups
find $BACKUP_DIR -name "magflow_backup_*.sql.gz" -mtime +7 -delete

# Upload to cloud storage (optional)
aws s3 cp $BACKUP_DIR/$FILENAME s3://magflow-backups/

echo "Backup completed: $FILENAME"
```

#### Kubernetes Backup

```yaml
# deployment/backup/postgres-backup.yml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: postgres-backup
            image: postgres:15
            command: ["/bin/bash", "-c"]
            args:
            - |
              BACKUP_FILE="magflow-$(date +%Y%m%d-%H%M%S).sql"
              pg_dump magflow > /backup/$BACKUP_FILE &&
              gzip /backup/$BACKUP_FILE &&
              aws s3 cp /backup/$BACKUP_FILE.gz s3://magflow-backups/
            volumeMounts:
            - name: backup-volume
              mountPath: /backup
          volumes:
          - name: backup-volume
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
```

### Configuration Backup

#### Backup Configuration Files

```bash
# scripts/backup-config.sh
BACKUP_DIR="/var/backups/magflow/config"
mkdir -p $BACKUP_DIR

# Copy configuration files
cp .env $BACKUP_DIR/
cp config/*.json $BACKUP_DIR/
cp docker-compose*.yml $BACKUP_DIR/
cp deployment/kubernetes/*.yml $BACKUP_DIR/

# Create archive
tar -czf $BACKUP_DIR/config_backup_$(date +%Y%m%d_%H%M%S).tar.gz -C $BACKUP_DIR .

echo "Configuration backup completed"
```

#### Kubernetes Config Backup

```yaml
# deployment/backup/config-backup.yml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: config-backup
spec:
  schedule: "0 1 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: config-backup
            image: bitnami/kubectl:latest
            command: ["/bin/bash", "-c"]
            args:
            - |
              mkdir -p /backup
              kubectl get all -o yaml > /backup/resources.yml
              kubectl get configmap -o yaml > /backup/configmaps.yml
              kubectl get secret -o yaml > /backup/secrets.yml
              tar czf /backup/cluster-backup-$(date +%Y%m%d-%H%M%S).tar.gz /backup/*.yml
            volumeMounts:
            - name: backup-volume
              mountPath: /backup
```

### Recovery Procedures

#### Database Recovery

```bash
# 1. Stop application
docker-compose down

# 2. Restore database
gunzip -c magflow_backup_20240115_020000.sql.gz | psql magflow

# 3. Verify restore
psql magflow -c "SELECT COUNT(*) FROM users;"
psql magflow -c "SELECT COUNT(*) FROM inventory_items;"

# 4. Start application
docker-compose up -d
```

#### Kubernetes Recovery

```bash
# 1. Scale down application
kubectl scale deployment magflow-erp --replicas=0

# 2. Restore database from backup
kubectl apply -f deployment/backup/postgres-restore.yml

# 3. Scale up application
kubectl scale deployment magflow-erp --replicas=3

# 4. Verify recovery
kubectl get pods
kubectl logs -f deployment/magflow-erp
```

## 🔍 Monitoring Tools

### Health Check Dashboard

```bash
# Create simple health check dashboard
while true; do
    echo "=== $(date) ==="

    # Application health
    curl -s http://localhost:8000/health | jq '.status'

    # Database connections
    curl -s http://localhost:8000/health/database | jq '.database.connections.total'

    # Response times
    curl -s http://localhost:8000/health/detailed | jq '.checks.database.response_time'

    echo "---"
    sleep 30
done
```

### Log Analysis Tools

```bash
# Real-time error monitoring
tail -f logs/app.log | grep -E "(ERROR|CRITICAL)" | jq '.'

# Request rate monitoring
tail -f logs/app.log | grep '"endpoint"' | awk -F'"' '{print $4}' | sort | uniq -c

# Performance monitoring
tail -f logs/app.log | jq '.response_time' | awk '{sum+=$1; count++} END {print "Avg response time:", sum/count, "ms"}'
```

### Database Performance Analysis

```bash
# Analyze slow queries
psql magflow -c "SELECT query, calls, total_time, mean_time FROM pg_stat_statements WHERE mean_time > 100 ORDER BY mean_time DESC LIMIT 10;"

# Check index usage
psql magflow -c "SELECT indexname, idx_scan, idx_tup_read, idx_tup_fetch FROM pg_stat_user_indexes ORDER BY idx_scan DESC LIMIT 10;"

# Monitor locks
psql magflow -c "SELECT pid, state, query FROM pg_stat_activity WHERE state != 'idle' ORDER BY query_start;"
```

______________________________________________________________________

**MagFlow ERP Monitoring & Troubleshooting Guide** - Complete Monitoring and Debugging Documentation 📊
