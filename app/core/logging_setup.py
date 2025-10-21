"""Structured logging configuration with OpenTelemetry and request correlation.

This module provides a structured logging setup with the following features:
- JSON-formatted logs for machine parsing
- Request correlation with OpenTelemetry
- Contextual logging with request details
- Performance metrics
- Environment-aware configuration
"""

import logging
import os
import socket
import sys
from datetime import UTC, datetime
from logging import Filter, LogRecord
from typing import Any

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Configure OpenTelemetry
try:
    resource = Resource.create(
        {
            "service.name": "magflow-api",
            "service.version": os.getenv("APP_VERSION", "1.0.0"),
            "deployment.environment": os.getenv("ENV", "development"),
            "host.name": socket.gethostname(),
        },
    )

    trace.set_tracer_provider(TracerProvider(resource=resource))

    # Add OTLP exporter if configured
    if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        otlp_exporter = OTLPSpanExporter()
        span_processor = BatchSpanProcessor(otlp_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)

except Exception as e:
    # Use stderr for early logging before logger is configured
    import logging
    logging.basicConfig(level=logging.WARNING)
    logging.warning(f"Failed to configure OpenTelemetry: {e}")


class RequestIdFilter(Filter):
    """Logging filter to add request_id to log records."""

    def filter(self, record: LogRecord) -> bool:
        request_id = getattr(record, "request_id", None)
        if not hasattr(record, "request_id") and hasattr(record, "request"):
            request = record.request
            request_id = (
                request.headers.get("X-Request-ID")
                if hasattr(request, "headers")
                else None
            )
            record.request_id = request_id
        return True


# Context variable for request context
request_context = {}


def get_request_context() -> dict[str, Any]:
    """Get the current request context."""
    return request_context.copy()


def set_request_context(**kwargs) -> None:
    """Set request context variables."""
    global request_context
    request_context.update(kwargs)


def clear_request_context() -> None:
    """Clear request context."""
    global request_context
    request_context = {}


def get_trace_info() -> dict[str, str]:
    """Get OpenTelemetry trace and span IDs if available."""
    span = trace.get_current_span()
    if not span or not span.get_span_context().is_valid:
        return {}

    ctx = span.get_span_context()
    return {
        "trace_id": f"{ctx.trace_id:032x}",
        "span_id": f"{ctx.span_id:016x}",
        "trace_flags": f"{ctx.trace_flags:02x}",
        "service.name": "magflow-api",
        "service.version": "1.0.0",
        "service.environment": "development",
    }


def add_request_context(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add request context to log records."""
    # Add request context if available
    request_ctx = get_request_context()
    if request_ctx:
        event_dict.update(
            {
                k: v
                for k, v in request_ctx.items()
                if v is not None and k not in event_dict
            },
        )

    # Add trace context
    trace_info = get_trace_info()
    if trace_info:
        event_dict.update(trace_info)

    # Add standard fields
    event_dict.update(
        {
            "@timestamp": datetime.now(UTC).isoformat(),
            "logger": logger.name,
            "level": method_name.upper(),
            "service": "magflow-api",
        },
    )

    # Ensure message is present
    if "event" not in event_dict:
        event_dict["event"] = method_name

    # Clean up any None values
    return {k: v for k, v in event_dict.items() if v is not None}


def setup_logging(service_name: str, log_level: str = "INFO") -> None:
    """Configure structured logging with structlog.

    This function sets up a comprehensive logging configuration with the following features:
    - JSON-formatted logs for machine parsing
    - Request correlation with OpenTelemetry
    - Contextual logging with request details
    - Performance metrics
    - Environment-aware configuration

    Args:
        service_name: Name of the service for log identification
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    """
    # Convert string log level to logging constant
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure the root logger
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Configure structlog processors
    processors = [
        # Add context from contextvars (for request context)
        structlog.contextvars.merge_contextvars,
        # Add log level and logger name
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        # Add request context (IP, user agent, etc.)
        add_request_context,
        # Handle log levels and filtering
        structlog.stdlib.filter_by_level,
        # Add stack info and format exceptions
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # Format stack traces when needed
        structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ],
        ),
        # Final formatting
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Clear any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Add JSON formatter
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.addFilter(RequestIdFilter())
    logger.addHandler(handler)

    # Configure log level for specific loggers
    logging.getLogger("uvicorn").handlers.clear()
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.error").handlers.clear()

    # Get logger for this module
    log = structlog.get_logger(service_name)
    log.info("Structured logging configured", log_level=log_level)
