"""
Prometheus metrics for eMAG synchronization operations.

This module provides custom metrics for monitoring eMAG product and order synchronization.
"""

import logging

logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, Gauge, Histogram

    METRICS_AVAILABLE = True
except ImportError:
    logger.warning("prometheus_client not available, metrics will be disabled")
    METRICS_AVAILABLE = False

    # Create dummy classes
    class Counter:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            pass

    class Histogram:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def observe(self, *args, **kwargs):
            pass

    class Gauge:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def set(self, *args, **kwargs):
            pass


# Sync duration metrics
EMAG_SYNC_DURATION = Histogram(
    "emag_sync_duration_seconds",
    "Duration of eMAG synchronization operations",
    ["account_type", "sync_type", "mode", "status"],
    buckets=(10, 30, 60, 120, 300, 600, 1200, 1800, 3600),  # 10s to 1h
)

# Sync products counter
EMAG_SYNC_PRODUCTS_TOTAL = Counter(
    "emag_sync_products_total",
    "Total number of products synced from eMAG",
    ["account_type", "action"],  # action: created, updated, unchanged, failed
)

# Sync errors counter
EMAG_SYNC_ERRORS_TOTAL = Counter(
    "emag_sync_errors_total",
    "Total number of eMAG synchronization errors",
    ["account_type", "sync_type", "error_type"],
)

# API request metrics
EMAG_API_REQUESTS_TOTAL = Counter(
    "emag_api_requests_total",
    "Total number of eMAG API requests",
    ["account_type", "endpoint", "status_code"],
)

EMAG_API_REQUEST_DURATION = Histogram(
    "emag_api_request_duration_seconds",
    "Duration of eMAG API requests",
    ["account_type", "endpoint"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
)

# Rate limiting metrics
EMAG_RATE_LIMIT_HITS_TOTAL = Counter(
    "emag_rate_limit_hits_total",
    "Total number of rate limit hits",
    ["account_type", "operation_type"],
)

EMAG_RATE_LIMIT_WAIT_TIME = Histogram(
    "emag_rate_limit_wait_seconds",
    "Time spent waiting for rate limits",
    ["account_type", "operation_type"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)

# Current sync status gauge
EMAG_SYNC_IN_PROGRESS = Gauge(
    "emag_sync_in_progress",
    "Number of synchronizations currently in progress",
    ["account_type", "sync_type"],
)

# Products by account gauge
EMAG_PRODUCTS_COUNT = Gauge(
    "emag_products_count",
    "Total number of products by account",
    ["account_type"],
)

# Timeout metrics
EMAG_SYNC_TIMEOUTS_TOTAL = Counter(
    "emag_sync_timeouts_total",
    "Total number of sync timeouts",
    ["account_type", "sync_type"],
)


# Helper functions for recording metrics


def record_sync_duration(
    account_type: str,
    sync_type: str,
    mode: str,
    status: str,
    duration: float,
):
    """Record synchronization duration."""
    EMAG_SYNC_DURATION.labels(
        account_type=account_type,
        sync_type=sync_type,
        mode=mode,
        status=status,
    ).observe(duration)


def record_sync_products(account_type: str, action: str, count: int = 1):
    """Record synced products count."""
    EMAG_SYNC_PRODUCTS_TOTAL.labels(
        account_type=account_type,
        action=action,
    ).inc(count)


def record_sync_error(account_type: str, sync_type: str, error_type: str):
    """Record synchronization error."""
    EMAG_SYNC_ERRORS_TOTAL.labels(
        account_type=account_type,
        sync_type=sync_type,
        error_type=error_type,
    ).inc()


def record_api_request(
    account_type: str,
    endpoint: str,
    status_code: int,
    duration: float,
):
    """Record API request metrics."""
    EMAG_API_REQUESTS_TOTAL.labels(
        account_type=account_type,
        endpoint=endpoint,
        status_code=status_code,
    ).inc()

    EMAG_API_REQUEST_DURATION.labels(
        account_type=account_type,
        endpoint=endpoint,
    ).observe(duration)


def record_rate_limit_hit(account_type: str, operation_type: str, wait_time: float):
    """Record rate limit hit and wait time."""
    EMAG_RATE_LIMIT_HITS_TOTAL.labels(
        account_type=account_type,
        operation_type=operation_type,
    ).inc()

    EMAG_RATE_LIMIT_WAIT_TIME.labels(
        account_type=account_type,
        operation_type=operation_type,
    ).observe(wait_time)


def set_sync_in_progress(account_type: str, sync_type: str, count: int):
    """Set number of syncs in progress."""
    EMAG_SYNC_IN_PROGRESS.labels(
        account_type=account_type,
        sync_type=sync_type,
    ).set(count)


def set_products_count(account_type: str, count: int):
    """Set total products count for account."""
    EMAG_PRODUCTS_COUNT.labels(account_type=account_type).set(count)


def record_sync_timeout(account_type: str, sync_type: str):
    """Record sync timeout."""
    EMAG_SYNC_TIMEOUTS_TOTAL.labels(
        account_type=account_type,
        sync_type=sync_type,
    ).inc()
