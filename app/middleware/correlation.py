"""Correlation ID Middleware for FastAPI

This middleware ensures that each request has a unique correlation ID for tracing
purposes. The correlation ID is added to the request state and response headers.
"""

import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from ..core.logging_config import get_logger

logger = get_logger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation ID to each request and response."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process the request and add correlation ID."""
        # Get correlation ID from headers or generate a new one
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

        # Add correlation ID to request state
        request.state.correlation_id = correlation_id

        # Process the request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        # Log the request with correlation ID
        logger.info(
            "Request processed",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
            },
        )

        return response


# Helper function to get the current correlation ID
def get_correlation_id(request: Request) -> str:
    """Get the correlation ID from the request state."""
    return getattr(request.state, "correlation_id", "")
