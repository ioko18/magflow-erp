"""OpenTelemetry metrics configuration for the application."""

import logging
import os

from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource

# Set up logger
logger = logging.getLogger(__name__)


def setup_metrics():
    """Initialize and configure OpenTelemetry metrics."""
    # Create resource with service information
    resource = Resource.create(
        {
            "service.name": "magflow",
            "service.version": "1.0.0",
            "deployment.environment": os.getenv("ENVIRONMENT", "development"),
        },
    )

    # Create a meter provider with Prometheus exporter
    prometheus_reader = PrometheusMetricReader()

    # Configure the meter provider
    readers = [prometheus_reader]

    # Add console exporter in development
    if os.getenv("ENVIRONMENT") == "development":
        readers.append(
            PeriodicExportingMetricReader(
                ConsoleMetricExporter(),
                export_interval_millis=60000,  # 1 minute
            ),
        )

    meter_provider = MeterProvider(resource=resource, metric_readers=readers)

    # Set the global meter provider
    metrics.set_meter_provider(meter_provider)

    # Create and return the meter
    return metrics.get_meter("magflow.monitoring")


# Initialize metrics
meter = setup_metrics()

# Define metrics
HEALTH_STATUS = meter.create_observable_gauge(
    name="magflow_health_status",
    description="Health status of the service (1=healthy, 0=unhealthy)",
    unit="1",
    callbacks=[],  # Will be populated by health checks
)

# Create counter with proper label support
HEALTH_CHECKS_TOTAL = meter.create_counter(
    name="magflow_health_checks_total",
    description="Total number of health check requests",
    unit="1",
)

# Define the attributes that will be used for health checks
HEALTH_CHECK_ATTRS = {"endpoint": "", "status": ""}

# HTTP Request Metrics
HTTP_REQUEST_DURATION = meter.create_histogram(
    name="http_request_duration_seconds",
    description="Duration of HTTP requests in seconds",
    unit="s",
)

HTTP_REQUESTS_TOTAL = meter.create_counter(
    name="http_requests_total",
    description="Total number of HTTP requests",
    unit="1",
)

HTTP_ERRORS_TOTAL = meter.create_counter(
    name="http_errors_total",
    description="Total number of HTTP errors",
    unit="1",
)

# Database Metrics
DB_CONNECTIONS_ACTIVE = meter.create_gauge(
    name="db_connections_active",
    description="Number of active database connections",
    unit="1",
)

DB_CONNECTIONS_IDLE = meter.create_gauge(
    name="db_connections_idle",
    description="Number of idle database connections",
    unit="1",
)

DB_CONNECTIONS_TOTAL = meter.create_gauge(
    name="db_connections_total",
    description="Total number of database connections",
    unit="1",
)

DB_QUERY_DURATION = meter.create_histogram(
    name="db_query_duration_seconds",
    description="Database query duration in seconds",
    unit="s",
)

# Cache Metrics
CACHE_HITS_TOTAL = meter.create_counter(
    name="cache_hits_total",
    description="Total number of cache hits",
    unit="1",
)

CACHE_MISSES_TOTAL = meter.create_counter(
    name="cache_misses_total",
    description="Total number of cache misses",
    unit="1",
)

CACHE_HIT_RATIO = meter.create_gauge(
    name="cache_hit_ratio",
    description="Cache hit ratio (0.0 to 1.0)",
    unit="1",
)

# Background Task Metrics
BACKGROUND_TASKS_QUEUED = meter.create_gauge(
    name="background_tasks_queued",
    description="Number of background tasks in queue",
    unit="1",
)

BACKGROUND_TASKS_RUNNING = meter.create_gauge(
    name="background_tasks_running",
    description="Number of background tasks currently running",
    unit="1",
)

BACKGROUND_TASKS_COMPLETED = meter.create_counter(
    name="background_tasks_completed_total",
    description="Total number of completed background tasks",
    unit="1",
)

BACKGROUND_TASKS_FAILED = meter.create_counter(
    name="background_tasks_failed_total",
    description="Total number of failed background tasks",
    unit="1",
)

# System Metrics
MEMORY_USAGE = meter.create_gauge(
    name="memory_usage_bytes",
    description="Memory usage in bytes",
    unit="By",
)

CPU_USAGE = meter.create_gauge(
    name="cpu_usage_percent",
    description="CPU usage percentage",
    unit="%",
)


def record_health_check(endpoint: str, status: str):
    """Record a health check event with the given endpoint and status.

    Args:
        endpoint: The health check endpoint (e.g., 'liveness', 'readiness')
        status: The status of the health check ('success' or 'failure')

    """
    try:
        HEALTH_CHECKS_TOTAL.add(1, {"endpoint": endpoint, "status": status})
    except Exception as e:
        logger.warning(f"Failed to record health check metric: {e}")


# Define common HTTP attributes
HTTP_ATTRS = {
    "http.method": "",
    "http.route": "",
    "http.status_code": 0,
    "http.status_class": "",
}


def get_metrics_router():
    """Return a router with metrics endpoint."""
    import time
    from collections.abc import Awaitable, Callable

    from fastapi import APIRouter, Request, Response
    from fastapi.responses import Response as FastAPIResponse
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    from .custom_metrics import (
        get_metrics_registry,
        record_error,
        record_request_metrics,
    )

    router = APIRouter(prefix="/metrics", tags=["monitoring"])

    @router.get("/")
    async def get_metrics():
        """Return Prometheus metrics."""
        return Response(
            content=generate_latest(registry=get_metrics_registry()),
            media_type=CONTENT_TYPE_LATEST,
        )

    async def metrics_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[FastAPIResponse]],
    ) -> FastAPIResponse:
        """Middleware to track request metrics.

        Records:
        - Request latency
        - Request count
        - Error count
        """
        start_time = time.time()
        method = request.method
        endpoint = request.url.path

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            # Record request metrics
            record_request_metrics(
                method=method,
                endpoint=endpoint,
                status_code=response.status_code,
                duration=process_time,
            )

            # Add Server-Timing header
            response.headers["Server-Timing"] = f"total;dur={process_time * 1000:.2f}"
            return response

        except Exception as e:
            # Record error metrics
            process_time = time.time() - start_time
            error_type = type(e).__name__
            record_error(error_type=error_type, endpoint=endpoint)
            logger.error(
                "Error processing request to %s after %.4f seconds: %s",
                endpoint,
                process_time,
                e,
                exc_info=True,
            )
            raise

    return router, metrics_middleware
