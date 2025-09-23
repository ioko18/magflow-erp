# MagFlow Observability and SLO Monitoring

This document explains how to set up and use the observability features in MagFlow, including SLO monitoring, metrics, tracing, and logging.

## Prerequisites

- Docker and Docker Compose
- Python 3.8+
- Required Python packages (install with `pip install -r requirements.txt`)

## Architecture

MagFlow uses the following components for observability:

1. **OpenTelemetry** - For collecting and exporting metrics and traces
2. **Prometheus** - For metrics storage, alerting, and SLO monitoring
3. **Grafana** - For visualization, dashboards, and SLO reporting
4. **OpenTelemetry Collector** - For receiving, processing, and exporting telemetry data
5. **Alertmanager** - For handling alerts and notifications

## Service Level Objectives (SLOs)

### Current SLOs

1. **Latency**: 95th percentile of request duration ≤ 300ms
2. **Error Rate**: ≤ 0.1% of requests return 5xx errors
3. **Availability**: 99.9% uptime (excluding planned maintenance)

### Multi-Window Burn Rate Strategy

We use a multi-window, multi-burn rate alerting strategy to detect both fast and slow burns against our SLOs:

1. **Fast Burn Detection (5-minute window)**
   - Window: 5 minutes
   - Burn Rate: 14.4x
   - Error Budget Burn: 1% of 30-day budget in 5 minutes
   - Use Case: Detects sudden, severe degradations

2. **Slow Burn Detection (1-hour window)**
   - Window: 1 hour
   - Burn Rate: 3.6x
   - Error Budget Burn: 5% of 30-day budget in 1 hour
   - Use Case: Catches slower, sustained degradations

### SLIs (Service Level Indicators)

| SLI | Query | Description |
|-----|-------|-------------|
| Request Latency (p95) | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, route, method))` | 95th percentile request duration |
| Error Rate | `sum(rate(http_request_duration_seconds_count{status_code=~"5.."}[5m])) / sum(rate(http_request_duration_seconds_count[5m]))` | Ratio of 5xx responses to total requests |
| Fast Burn Latency | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, route, method)) > 0.3` | p95 latency > 300ms for 5m |
| Slow Burn Latency | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[1h])) by (le, route, method)) > 0.3` | p95 latency > 300ms for 1h |
| Fast Burn Error Rate | `sum(rate(http_request_duration_seconds_count{status_code=~"5.."}[5m])) / sum(rate(http_request_duration_seconds_count[5m])) > 0.0144` | Error rate > 1.44% for 5m |
| Slow Burn Error Rate | `sum(rate(http_request_duration_seconds_count{status_code=~"5.."}[1h])) / sum(rate(http_request_duration_seconds_count[1h])) > 0.0036` | Error rate > 0.36% for 1h |
| Request Rate | `sum(rate(http_request_duration_seconds_count[1m])) by (route, method)` | Requests per second by endpoint |

## Alerting Rules

Alerts are configured in `docker/prometheus/magflow_slo_rules.yml`:

### Latency Alerts
1. **HighLatencyFastBurn (page)**
   - Triggers when: p95 latency > 300ms for 5 minutes (14.4x burn rate)
   - Severity: page
   - Runbook: [Link to Runbook](#)

2. **HighLatencySlowBurn (ticket)**
   - Triggers when: p95 latency > 300ms for 1 hour (3.6x burn rate)
   - Severity: ticket
   - Runbook: [Link to Runbook](#)

### Error Rate Alerts
3. **HighErrorRateFastBurn (page)**
   - Triggers when: Error rate > 1.44% for 5 minutes (14.4x burn rate)
   - Severity: page
   - Runbook: [Link to Runbook](#)

4. **HighErrorRateSlowBurn (ticket)**
   - Triggers when: Error rate > 0.36% for 1 hour (3.6x burn rate)
   - Severity: ticket
   - Runbook: [Link to Runbook](#)

### Service Health
5. **ServiceDegraded**
   - Triggers when: Service is down for 5 minutes
   - Severity: page
   - Runbook: [Link to Runbook](#)

### Alert Suppression
- Fast burn alerts are automatically suppressed if they don't lead to a slow burn alert within 30 minutes
- Alerts are grouped by service and route to prevent alert storms

## SLO Dashboard

The SLO dashboard in Grafana provides an overview of service performance against defined SLOs:

### Burn Rate Analysis
- **Latency Burn Rate**: Shows active latency burn alerts by route and method
- **Error Rate Burn Rate**: Displays error rate over time with SLO threshold (0.1%)
- **Burn Rate Multipliers**: Visualizes 14.4x (5m) and 3.6x (1h) thresholds

### Current Status
- **Latency p95 by Endpoint**: Gauge showing current p95 latency with 300ms threshold
- **Error Rate**: Gauge showing current error rate with 0.1% threshold
- **SLO Compliance**: Percentage of time within SLO over last 30 days

### Detailed Metrics
- **Requests Per Second (RPS)**: Time series of request rate by endpoint
- **Latency p95/p99**: Detailed latency metrics by endpoint
- **Error Rate by Endpoint**: Detailed error rate metrics by endpoint
- **Error Budget Remaining**: Visual representation of remaining error budget

## Setup Instructions

### 1. Environment Variables

Add these to your `.env` file:

```bash
# OpenTelemetry Configuration
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_EXPORTER_OTLP_INSECURE=true
OTEL_SERVICE_NAME=magflow-api
OTEL_RESOURCE_ATTRIBUTES=service.version=1.0,deployment.environment=development

# Prometheus Configuration
PROMETHEUS_ENABLED=true

# Grafana Configuration (for reference, used in docker-compose)
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin
```

### 2. Start Observability Stack

Start the observability services using Docker Compose:

```bash
docker-compose -f docker-compose.observability.yml up -d
```

This will start:
- Prometheus on http://localhost:9090
- Grafana on http://localhost:3000
- OpenTelemetry Collector on http://localhost:4317

### 3. Start the Application

Start the MagFlow API with observability enabled:

```bash
# In one terminal
make up

# In another terminal, run the application with auto-reload
make dev
```

## Accessing Dashboards

### Grafana
- URL: http://localhost:3000
- Username: admin (or value of GRAFANA_ADMIN_USER)
- Password: admin (or value of GRAFANA_ADMIN_PASSWORD)

Pre-configured dashboards:
- **MagFlow API Dashboard**: Overview of request rates, response times, and error rates
- **Node Exporter**: System metrics

### Prometheus
- URL: http://localhost:9090
- No authentication by default

## Available Metrics

### HTTP Server Metrics
- `http_server_requests_total`: Total HTTP requests
- `http_server_duration_seconds`: Request duration in seconds
- `http_server_request_size_bytes`: Request size in bytes
- `http_server_response_size_bytes`: Response size in bytes

### Database Metrics
- `db_operations_total`: Total database operations
- `db_query_duration_seconds`: Query duration in seconds

### System Metrics
- `process_cpu_seconds_total`: CPU usage
- `process_resident_memory_bytes`: Memory usage
- `python_gc_objects_collected_total`: Garbage collection stats

## Tracing

Traces are exported to the OpenTelemetry Collector and can be viewed in a compatible backend like Jaeger or Zipkin.

### Viewing Traces

1. Start Jaeger all-in-one:
   ```bash
   docker run -d --name jaeger \
     -e COLLECTOR_OTLP_ENABLED=true \
     -p 16686:16686 \
     -p 4317:4317 \
     -p 4318:4318 \
     jaegertracing/all-in-one:latest
   ```

2. Access the Jaeger UI at http://localhost:16686

## Logging

Logs are structured in JSON format and include trace context. They can be collected and processed by any log aggregation system.

### Log Fields
- `timestamp`: ISO 8601 timestamp
- `level`: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `message`: Log message
- `service`: Service name
- `environment`: Deployment environment
- `trace_id`: OpenTelemetry trace ID
- `span_id`: OpenTelemetry span ID
- `request_id`: Request correlation ID

## Troubleshooting

### No Metrics in Prometheus
1. Check if the application is running and accessible
2. Verify the `/metrics` endpoint returns data: `curl http://localhost:8000/metrics`
3. Check Prometheus targets: http://localhost:9090/targets

### No Traces in Jaeger
1. Verify the OpenTelemetry Collector is running
2. Check application logs for export errors
3. Ensure the correct OTLP endpoint is configured

## Customization

### Adding Custom Metrics

```python
from opentelemetry import metrics

# Get the meter
meter = metrics.get_meter("your.meter.name")

# Create a counter
custom_counter = meter.create_counter(
    "custom.counter",
    description="A custom counter metric",
    unit="1",
)

# Increment the counter
custom_counter.add(1, {"key": "value"})
```

### Adding Custom Spans

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("custom-operation") as span:
    # Your code here
    span.set_attribute("custom.attribute", "value")
```

## Performance Considerations

- The OpenTelemetry collector buffers and batches data to reduce overhead
- Metrics are collected asynchronously and should have minimal impact on performance
- For production, consider using a dedicated observability backend

## Security

- The `/metrics` endpoint is exposed by default. In production, restrict access to this endpoint.
- Use HTTPS for all external communications
- Rotate API keys and credentials regularly
