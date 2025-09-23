# Health Check Implementation

This document outlines the health check implementation for the MagFlow ERP platform, including endpoints, Docker health checks, and Kubernetes probes.

## Health Check Endpoints

### 1. Liveness Probe (`/api/v1/health/live`)
- **Purpose**: Indicates if the service is running
- **Response**:
  ```json
  {
    "status": "alive",
    "timestamp": "2023-01-01T00:00:00.000000"
  }
  ```
- **Status Codes**:
  - `200 OK`: Service is running

### 2. Readiness Probe (`/api/v1/health/ready`)
- **Purpose**: Indicates if the service is ready to handle requests
- **Checks**:
  - Database connectivity
  - Redis connectivity
  - JWKS endpoint availability
- **Response**:
  ```json
  {
    "status": "ready",
    "timestamp": "2023-01-01T00:00:00.000000",
    "dependencies": {
      "database": true,
      "redis": true,
      "jwks": true
    }
  }
  ```
- **Status Codes**:
  - `200 OK`: All dependencies are healthy
  - `503 Service Unavailable`: One or more dependencies are unavailable

### 3. Startup Probe (`/api/v1/health/startup`)
- **Purpose**: Indicates if the service has completed its startup sequence
- **Behavior**:
  - Returns `425 Too Early` during warmup period (first 30 seconds)
  - After warmup, delegates to readiness check
- **Status Codes**:
  - `200 OK`: Service has started and is ready
  - `425 Too Early`: Service is still starting up
  - `503 Service Unavailable`: Service started but not ready

## Docker Health Check

The Docker container includes a health check that runs the `healthcheck.sh` script, which verifies both liveness and readiness:

```bash
HEALTHCHECK --interval=30s \
    --timeout=10s \
    --start-period=5s \
    --retries=3 \
    CMD ["/bin/sh", "-c", "healthcheck.sh"]
```

## Kubernetes Probes

### Liveness Probe
- **Path**: `/api/v1/health/live`
- **Initial Delay**: 30s
- **Period**: 30s
- **Timeout**: 5s
- **Failure Threshold**: 3

### Readiness Probe
- **Path**: `/api/v1/health/ready`
- **Initial Delay**: 10s
- **Period**: 10s
- **Timeout**: 3s
- **Failure Threshold**: 3

### Startup Probe
- **Path**: `/api/v1/health/startup`
- **Initial Delay**: 0s
- **Period**: 10s
- **Timeout**: 1s
- **Failure Threshold**: 30 (5 minutes total)

## Monitoring

Health check metrics are exposed via the `/metrics` endpoint and can be scraped by Prometheus. The following metrics are available:

- `http_requests_total`: Total number of HTTP requests
- `http_request_duration_seconds`: Request duration in seconds
- `health_check_status`: Status of health checks (1 = healthy, 0 = unhealthy)

## Troubleshooting

1. **Service Not Starting**
   - Check container logs: `docker-compose logs app`
   - Verify environment variables are set correctly
   - Check database and Redis connectivity

2. **Readiness Probe Failing**
   - Verify all dependencies are running
   - Check network connectivity between services
   - Review logs for connection errors

3. **Startup Probe Failing**
   - Check application logs for startup errors
   - Verify resource constraints (CPU/memory)
   - Check for deadlocks during initialization

## Security Considerations

- Health check endpoints are not authenticated to allow for system-level monitoring
- Sensitive information is not exposed in health check responses
- Rate limiting is applied to prevent abuse

## Performance Impact

Health checks are designed to be lightweight:
- Liveness checks are minimal and fast
- Readiness checks are cached for 5 seconds to reduce load
- Database queries are optimized and use connection pooling
