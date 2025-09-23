import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as OTLPHTTPSpanExporter,
)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import DEPLOYMENT_ENVIRONMENT, SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

from .core.config import settings

logger = logging.getLogger(__name__)


def get_tracer_provider(
    service_name: str,
    environment: str = "development",
) -> TracerProvider:
    """Initialize and configure OpenTelemetry TracerProvider.

    Args:
        service_name: Name of the service to be used in traces
        environment: Deployment environment (e.g., development, production)

    Returns:
        Configured TracerProvider instance

    """
    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            DEPLOYMENT_ENVIRONMENT: environment,
            "version": "0.1.0",
        },
    )
    return TracerProvider(resource=resource)


def get_otlp_exporter(use_http: bool = False):
    """Get OTLP exporter based on configuration.

    Args:
        use_http: If True, use HTTP exporter, otherwise use gRPC

    Returns:
        Configured OTLP exporter

    """
    if use_http:
        return OTLPHTTPSpanExporter()
    return OTLPSpanExporter()


def init_tracing(service_name: str, environment: str = "development"):
    """Initialize OpenTelemetry tracing.

    Args:
        service_name: Name of the service to be used in traces
        environment: Deployment environment (e.g., development, production)

    """
    try:
        # Configure tracer provider
        tracer_provider = get_tracer_provider(service_name, environment)
        trace.set_tracer_provider(tracer_provider)

        # Configure exporters based on environment
        if settings.otlp_endpoint:
            use_http = settings.otlp_endpoint.startswith(
                "http://",
            ) or settings.otlp_endpoint.startswith("https://")
            otlp_exporter = get_otlp_exporter(use_http=use_http)
            span_processor = BatchSpanProcessor(otlp_exporter)
            tracer_provider.add_span_processor(span_processor)
            logger.info(
                f"Initialized OTLP exporter to {settings.otlp_endpoint} "
                f"using {'HTTP' if use_http else 'gRPC'}",
            )
        else:
            # Fallback to console exporter if no OTLP endpoint is configured
            console_exporter = ConsoleSpanExporter()
            span_processor = SimpleSpanProcessor(console_exporter)
            tracer_provider.add_span_processor(span_processor)
            logger.warning(
                "No OTLP endpoint configured. Using console exporter for tracing.",
            )

        # Enable auto-instrumentation for common libraries
        FastAPIInstrumentor.instrument()
        RequestsInstrumentor().instrument()
        SQLAlchemyInstrumentor().instrument()

        logger.info("Tracing initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize tracing: {e}", exc_info=True)
        # Fallback to a no-op tracer provider
        trace.set_tracer_provider(trace.NoOpTracerProvider())


def instrument_fastapi(app):
    """Instrument FastAPI application with OpenTelemetry.

    Args:
        app: FastAPI application instance

    """
    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("Instrumented FastAPI application")
    except Exception as e:
        logger.error(f"Failed to instrument FastAPI: {e}", exc_info=True)


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance.

    Args:
        name: Name of the tracer (usually __name__)

    Returns:
        Tracer instance

    """
    return trace.get_tracer_provider().get_tracer(name)


# Initialize tracing when module is imported
init_tracing(
    service_name=settings.otel_service_name,
    environment=settings.environment,
)
