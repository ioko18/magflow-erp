"""Logging middleware for FastAPI to log requests and responses in a structured format."""

import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.logging_setup import clear_request_context, set_request_context
from app.utils.logger import log_error, log_request, log_response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests and responses with structured logging."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # Generate a unique request ID if not present
        request_id = request.headers.get("X-Request-ID")

        # Set up request context for logging
        set_request_context(request_id)

        # Log request
        start_time = time.time()
        log_request(request, request_id=request_id)

        # Process the request
        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            # Log response
            log_response(
                request=request,
                response=response,
                process_time=process_time,
                request_id=request_id,
            )

            return response

        except Exception as e:
            # Log unhandled exceptions
            process_time = time.time() - start_time
            log_error(
                error=e,
                request=request,
                process_time=process_time,
                request_id=request_id,
            )
            raise

        finally:
            # Clear request context
            clear_request_context()


def setup_logging_middleware(app: ASGIApp) -> ASGIApp:
    """Set up logging middleware for the FastAPI application.

    Args:
        app: The FastAPI application

    Returns:
        The FastAPI application with logging middleware

    """
    app.add_middleware(LoggingMiddleware)
    return app
