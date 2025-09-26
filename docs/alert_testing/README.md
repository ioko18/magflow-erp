# Alert Testing Plan

This document outlines the procedures for testing the SLO-based alerting system in the MagFlow application.

## Test Environment Setup

### Prerequisites

- Docker and Docker Compose
- `curl` and `jq` installed
- Access to Grafana and Alertmanager UIs

### Start Test Environment

```bash
# Start the full stack with monitoring
docker-compose -f docker-compose.yml -f docker-compose.observability.yml up -d

# Verify all services are running
docker-compose ps
```

## Test Cases

### 1. HighLatencyFastBurn Alert

**Objective**: Verify that the alert triggers when p95 latency exceeds 300ms for 5 minutes.

**Steps**:

1. Generate artificial latency:
   ```bash
   # In a separate terminal, run the latency generator
   ./tests/alert_testing/generate_latency.sh 500 300
   ```
1. Monitor alerts in Alertmanager UI (http://localhost:9093)
1. Check Grafana dashboard for latency metrics
1. Verify notification delivery

**Expected Result**:

- Alert triggers after 5 minutes
- Notification is received
- Alert appears in Grafana dashboard

### 2. HighLatencySlowBurn Alert

**Objective**: Verify that the alert triggers when p95 latency exceeds 300ms for 1 hour.

**Steps**:

1. Generate sustained latency:
   ```bash
   ./tests/alert_testing/generate_latency.sh 350 3600
   ```
1. Monitor for alert after 1 hour
1. Verify alert details in Alertmanager

**Expected Result**:

- Alert triggers after 1 hour
- Notification is received with correct severity

### 3. HighErrorRateFastBurn Alert

**Objective**: Verify that the alert triggers when error rate exceeds 1.44% for 5 minutes.

**Steps**:

1. Generate errors:
   ```bash
   ./tests/alert_testing/generate_errors.sh 2 300
   ```
1. Monitor error rate in Grafana
1. Check for alert in Alertmanager

**Expected Result**:

- Alert triggers after 5 minutes
- Error rate is visible in dashboard

### 4. HighErrorRateSlowBurn Alert

**Objective**: Verify that the alert triggers when error rate exceeds 0.36% for 1 hour.

**Steps**:

1. Generate sustained errors:
   ```bash
   ./tests/alert_testing/generate_errors.sh 0.5 3600
   ```
1. Monitor for alert after 1 hour
1. Verify alert details

**Expected Result**:

- Alert triggers after 1 hour
- Correct burn rate is calculated

### 5. Alert Suppression

**Objective**: Verify that fast burn alerts are suppressed when slow burn alerts fire.

**Steps**:

1. Start error generation:
   ```bash
   ./tests/alert_testing/generate_errors.sh 1.5 3600
   ```
1. Let fast burn alert trigger
1. Wait for slow burn alert
1. Verify fast burn alert is suppressed

**Expected Result**:

- Fast burn alert is suppressed when slow burn alert is active
- Only one notification is received for the incident

## Test Scripts

### `generate_latency.sh`

```bash
#!/bin/bash
# Usage: ./generate_latency.sh <latency_ms> <duration_sec>

LATENCY_MS=${1:-500}
DURATION=${2:-300}

echo "Generating $LATENCY_MS ms latency for $DURATION seconds..."

for ((i=0; i<DURATION; i++)); do
    curl -s -o /dev/null \
         -H "Content-Type: application/json" \
         -X POST \
         -d "{\"delay_ms\": $LATENCY_MS}" \
         http://localhost:8000/api/v1/test/latency
    sleep 1
done
```

### `generate_errors.sh`

```bash
#!/bin/bash
# Usage: ./generate_errors.sh <error_percent> <duration_sec>

ERROR_PCT=${1:-1}
DURATION=${2:-300}
REQUESTS_PER_SEC=10
TOTAL_REQUESTS=$((REQUESTS_PER_SEC * DURATION))
ERROR_EVERY=$((100 / ERROR_PCT))

if [ $ERROR_EVERY -lt 1 ]; then
    ERROR_EVERY=1
fi

echo "Generating $ERROR_PCT% errors for $DURATION seconds..."

for ((i=1; i<=TOTAL_REQUESTS; i++)); do
    if ((i % ERROR_EVERY == 0)); then
        curl -s -o /dev/null http://localhost:8000/api/v1/test/error
    else
        curl -s -o /dev/null http://localhost:8000/api/v1/test/health
    fi
    
    # Sleep to maintain request rate
    sleep $(bc -l <<< "1/$REQUESTS_PER_SEC")
done
```

## Verification Steps

1. **Alertmanager UI**

   - Navigate to http://localhost:9093
   - Verify alerts appear with correct labels
   - Check alert grouping

1. **Grafana Dashboard**

   - Open SLO dashboard
   - Verify metrics match expected values
   - Check burn rate calculations

1. **Logs**

   ```bash
   # Check application logs
   docker-compose logs --tail=100 app

   # Check Alertmanager logs
   docker-compose logs alertmanager
   ```

## Cleanup

After testing, stop the test environment:

```bash
docker-compose -f docker-compose.yml -f docker-compose.observability.yml down
```

## Test Data

### Expected Alert Labels

```yaml
alertname: HighLatencyFastBurn|HighLatencySlowBurn|HighErrorRateFastBurn|HighErrorRateSlowBurn
severity: page|ticket
alert_type: slo
service: magflow
route: /api/v1/...
method: GET|POST|PUT|DELETE
```

### Expected Annotations

```yaml
description: "High latency detected: {{ $value }}s (threshold: 0.3s)"
summary: "High latency on {{ $labels.route }} ({{ $labels.method }}) - {{ $value | humanize }}s"
runbook_url: "https://github.com/yourorg/magflow/docs/runbooks/SLO_ALERTS.md#highlatencyfastburn"
```
