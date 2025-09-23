"""Middleware for OpenTelemetry integration with FastAPI."""

import time

from fastapi import Request, Response
from opentelemetry import trace
from opentelemetry.metrics import get_meter_provider
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp


def get_trace_context():
    """Get current trace context for logging."""
    span = trace.get_current_span()
    if not span:
        return {}

    ctx = span.get_span_context()
    if not ctx:
        return {}

    return {
        "trace_id": f"{ctx.trace_id:032x}",
        "span_id": f"{ctx.span_id:016x}",
        "trace_flags": str(ctx.trace_flags),
    }


class RequestIdMiddleware:
    """Middleware to add request ID and trace context to logs."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope, receive, send):
        from structlog.contextvars import bind_contextvars

        # Get trace context
        trace_ctx = get_trace_context()

        # Bind context for logging
        bind_contextvars(
            request_id=trace_ctx.get("trace_id", ""),
            trace_id=trace_ctx.get("trace_id", ""),
            span_id=trace_ctx.get("span_id", ""),
        )

        await self.app(scope, receive, send)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP request metrics."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # Get meter and create metrics
        meter = get_meter_provider().get_meter("magflow.http")
        request_counter = meter.create_counter(
            "http.server.request_count",
            description="Number of HTTP requests",
            unit="1",
        )

        request_duration = meter.create_histogram(
            "http.server.duration",
            description="Duration of HTTP requests in seconds",
            unit="s",
        )

        # Process request with timing
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # Record metrics
        labels = {
            "method": request.method,
            "route": request.url.path,
            "status_code": response.status_code,
        }

        request_counter.add(1, labels)
        request_duration.record(process_time, labels)

        # Add server timing header
        response.headers["Server-Timing"] = f"total;dur={process_time * 1000:.2f}"

        return response


def instrument_application(app: ASGIApp) -> ASGIApp:
    """Instrument the FastAPI application with OpenTelemetry middleware."""
    # Add request ID and trace context middleware
    app = RequestIdMiddleware(app)

    # Add metrics middleware
    app = MetricsMiddleware(app)

    return app
