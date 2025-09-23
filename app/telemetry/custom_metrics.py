from prometheus_client import Counter, Gauge, Histogram
from prometheus_client.registry import REGISTRY

# Request metrics
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint", "status_code"],
)

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status_code"],
)

# Database metrics
DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type"],
)

DB_QUERY_COUNT = Counter(
    "db_queries_total",
    "Total number of database queries",
    ["query_type", "status"],
)

# Application specific metrics
ACTIVE_USERS = Gauge("active_users", "Number of active users")

# Error metrics
ERROR_COUNT = Counter(
    "app_errors_total",
    "Total number of application errors",
    ["error_type", "endpoint"],
)


def record_request_metrics(
    method: str,
    endpoint: str,
    status_code: int,
    duration: float,
):
    """Record HTTP request metrics."""
    REQUEST_LATENCY.labels(
        method=method,
        endpoint=endpoint,
        status_code=status_code,
    ).observe(duration)
    REQUEST_COUNT.labels(
        method=method,
        endpoint=endpoint,
        status_code=status_code,
    ).inc()


def record_db_query(query_type: str, duration: float, success: bool = True):
    """Record database query metrics."""
    status = "success" if success else "error"
    DB_QUERY_DURATION.labels(query_type=query_type).observe(duration)
    DB_QUERY_COUNT.labels(query_type=query_type, status=status).inc()


def record_error(error_type: str, endpoint: str):
    """Record error metrics."""
    ERROR_COUNT.labels(error_type=error_type, endpoint=endpoint).inc()


def set_active_users(count: int):
    """Set the number of active users."""
    ACTIVE_USERS.set(count)


def get_metrics_registry():
    """Return the metrics registry."""
    return REGISTRY
