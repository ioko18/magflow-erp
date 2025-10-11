"""Correlation ID middleware for FastAPI applications.

This module provides middleware to add and track correlation IDs for requests.
"""

import contextvars
import uuid
from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# Context variable to store the correlation ID for the current request
_correlation_id_ctx_var = contextvars.ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    """Get the current correlation ID from the context.

    Returns:
        Optional[str]: The current correlation ID, or None if not set

    """
    return _correlation_id_ctx_var.get()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add and track correlation IDs for requests.

    This middleware ensures that each request has a unique correlation ID,
    which can be used to trace requests across services and logs.
    """

    def __init__(
        self,
        app: FastAPI,
        header_name: str = "X-Correlation-ID",
        generate_id: Callable[[], str] = lambda: str(uuid.uuid4()),
    ) -> None:
        """Initialize the middleware.

        Args:
            app: The FastAPI application instance
            header_name: The name of the header to use for correlation IDs
            generate_id: A callable that generates a new correlation ID

        """
        super().__init__(app)
        self.header_name = header_name
        self.generate_id = generate_id

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process the request and add a correlation ID.

        Args:
            request: The incoming request
            call_next: The next middleware or request handler

        Returns:
            Response: The response with the correlation ID header added

        """
        # Get the correlation ID from the header or generate a new one
        correlation_id = request.headers.get(self.header_name) or self.generate_id()

        # Set the correlation ID in the context
        token = _correlation_id_ctx_var.set(correlation_id)

        try:
            # Call the next middleware/handler
            response = await call_next(request)

            # Add the correlation ID to the response headers
            response.headers[self.header_name] = correlation_id

            return response
        except Exception as e:
            # Ensure correlation ID is set in error responses
            if hasattr(e, "headers") and isinstance(e.headers, dict):
                e.headers[self.header_name] = correlation_id
            raise
        finally:
            # Clean up the context variable
            _correlation_id_ctx_var.reset(token)


# Context manager for setting correlation ID in background tasks
class CorrelationIdContext:
    """Context manager for setting correlation ID in background tasks."""

    def __init__(self, correlation_id: str):
        self.correlation_id = correlation_id
        self.token = None

    def __enter__(self):
        self.token = _correlation_id_ctx_var.set(self.correlation_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token is not None:
            _correlation_id_ctx_var.reset(self.token)


def with_correlation_id(correlation_id: str) -> CorrelationIdContext:
    """Create a context with the specified correlation ID."""
    return CorrelationIdContext(correlation_id)
