"""Initialize the application."""

import logging
import os
from contextlib import nullcontext
from typing import Optional

# Import models to ensure they are registered with SQLAlchemy
from app import models

# Import core utilities
from app.core import security
from app.core.config import settings

# Import CRUD operations
from app.crud import user

# Import database models and session
from app.db import base_class

# Import schemas
from app.schemas import user as user_schemas

logger = logging.getLogger(__name__)

_telemetry_get_tracer = None
_telemetry_setup_tracing = None
_telemetry_enabled = False

if settings.OTLP_ENABLED:
    try:
        from app.telemetry import get_tracer as _configured_get_tracer
        from app.telemetry import setup_tracing as _configured_setup_tracing

        _telemetry_get_tracer = _configured_get_tracer
        _telemetry_setup_tracing = _configured_setup_tracing
        _telemetry_enabled = True
    except Exception as telemetry_exc:
        logger.warning(
            "Telemetry integration disabled due to import error: %s",
            telemetry_exc,
            exc_info=True,
        )


def setup_tracing(service_name: Optional[str] = None, app=None):
    """Initialize OpenTelemetry tracing when available."""

    if _telemetry_enabled and _telemetry_setup_tracing:
        return _telemetry_setup_tracing(
            service_name=service_name or settings.SERVICE_NAME,
            app=app,
        )

    return None


def get_tracer(name: Optional[str] = None):
    """Return a tracer, falling back to a no-op tracer when telemetry is unavailable."""

    if _telemetry_enabled and _telemetry_get_tracer:
        return _telemetry_get_tracer(name)

    try:
        from opentelemetry import trace

        return trace.get_tracer(name or __name__)
    except Exception:
        # Provide a minimal no-op tracer compatible with context manager usage.
        class _NoOpSpan:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                return False

        class _NoOpTracer:
            def start_as_current_span(self, _name, *args, **kwargs):
                return nullcontext(_NoOpSpan())

            def start_span(self, _name, *args, **kwargs):
                return _NoOpSpan()

        return _NoOpTracer()


# Initialize OpenTelemetry if enabled and running inside a container
_tracer_provider = None
if _telemetry_enabled and os.getenv("DOCKER_CONTAINER"):
    try:
        _tracer_provider = setup_tracing(app=None)
    except Exception as e:
        logger.error(
            "Failed to initialize OpenTelemetry: %s",
            str(e),
            exc_info=True,
        )


# Re-export commonly used items
__all__ = [
    "base_class",
    "get_tracer",
    "models",
    "security",
    "setup_tracing",
    "user",
    "user_schemas",
]
