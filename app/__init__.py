"""Initialize the application."""

import os

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
from app.telemetry import get_tracer, setup_tracing

# Initialize OpenTelemetry if enabled
_tracer_provider = None
if settings.OTLP_ENABLED and os.getenv("DOCKER_CONTAINER"):
    try:
        _tracer_provider = setup_tracing(
            service_name=settings.SERVICE_NAME,
            app=None,
        )
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(
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
    "user",
    "user_schemas",
]
