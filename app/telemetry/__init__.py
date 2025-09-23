"""OpenTelemetry configuration and utilities for MagFlow."""

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import DEPLOYMENT_ENVIRONMENT, SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import settings


def setup_telemetry(service_name: str = "magflow-api", app=None):
    """Initialize OpenTelemetry with OTLP exporters.

    Args:
        service_name: Name of the service for resource attributes
        app: Optional FastAPI application to instrument

    """
    # Configure resource
    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            DEPLOYMENT_ENVIRONMENT: settings.ENVIRONMENT,
            "version": settings.VERSION,
        },
    )

    # Initialize tracing
    setup_tracing(resource)

    # Enable auto-instrumentation if app is provided
    if app is not None:
        instrument_app(app)

    # Initialize metrics
    setup_metrics(resource)


def setup_tracing(resource: Resource):
    """Configure OpenTelemetry tracing."""
    # Create OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
        insecure=os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true").lower() == "true",
    )

    # Set up tracer provider
    tracer_provider = TracerProvider(
        resource=resource,
    )

    # Add span processor
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)

    # Set the global tracer provider
    trace.set_tracer_provider(tracer_provider)

    # Enable log correlation
    LoggingInstrumentor().instrument(
        set_logging_format=True,
        log_level=settings.LOG_LEVEL,
        tracer_provider=tracer_provider,
    )


def setup_metrics(resource: Resource):
    """Configure OpenTelemetry metrics."""
    # Create OTLP exporter for metrics
    otlp_metric_exporter = OTLPMetricExporter(
        endpoint=os.getenv(
            "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT",
            os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317"),
        ),
        insecure=os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true").lower() == "true",
    )

    # Also create a console exporter for debugging
    console_exporter = ConsoleMetricExporter()

    # Set up meter provider with both exporters
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[
            PeriodicExportingMetricReader(
                exporter=otlp_metric_exporter,
                export_interval_millis=5000,  # 5 seconds
            ),
            PeriodicExportingMetricReader(
                exporter=console_exporter,
                export_interval_millis=10000,  # 10 seconds
            ),
        ],
    )

    # Set the global meter provider
    set_meter_provider(meter_provider)

    # Create and register metrics
    register_metrics(meter_provider)


def register_metrics(meter_provider):
    """Register application metrics."""
    meter = meter_provider.get_meter("magflow.metrics")

    # HTTP server metrics
    request_counter = meter.create_counter(
        "http.server.requests",
        description="Count of HTTP requests",
        unit="1",
    )

    request_duration = meter.create_histogram(
        "http.server.duration",
        description="Duration of HTTP requests in seconds",
        unit="s",
    )

    # Database metrics
    db_operations = meter.create_counter(
        "db.operations",
        description="Count of database operations",
        unit="1",
    )

    return {
        "request_counter": request_counter,
        "request_duration": request_duration,
        "db_operations": db_operations,
    }


def instrument_app(app):
    """Telemetry module for the application."""
    from opentelemetry.sdk.resources import Resource

    from . import otel_metrics

    # Configure the tracer provider
    resource = Resource(
        attributes={
            "service.name": "magflow",
            "service.version": "1.0.0",
            "deployment.environment": os.getenv("ENVIRONMENT", "development"),
        },
    )

    trace.set_tracer_provider(TracerProvider(resource=resource))

    # Access metrics
    _ = otel_metrics.meter  # Keep reference to ensure metrics are registered

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)

    # Instrument asyncpg connections
    AsyncPGInstrumentor().instrument()

    # Instrument Redis connections
    RedisInstrumentor().instrument()


def get_tracer(name: str = None):
    """Get a tracer instance."""
    return trace.get_tracer(name or __name__)
