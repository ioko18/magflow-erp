"""Middleware for request context and logging."""

import contextvars
import logging
import time
import uuid
from collections.abc import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.logging_setup import clear_request_context, set_request_context

# Context variable for request ID
request_id_ctx = contextvars.ContextVar("request_id", default="system")

# Get logger
logger = structlog.get_logger(__name__)


def get_request_id() -> str:
    """Get the current request ID from context."""
    return request_id_ctx.get()


class RequestContextLogMiddleware(BaseHTTPMiddleware):
    """Middleware to add request context to logs."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        logger: logging.Logger = None,
        header_name: str = "X-Request-ID",
        force_standard_logger: bool = False,
    ) -> None:
        super().__init__(app)
        self.logger = logger or structlog.get_logger(__name__)
        self.header_name = header_name

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # Get or generate request ID
        request_id = request.headers.get(self.header_name.lower())
        if not request_id:
            request_id = str(uuid.uuid4())

        # Set up request context for logging
        set_request_context(request_id=request_id)

        try:
            # Log request start - handle both structlog and standard logging
            request_info = {
                "method": request.method,
                "path": request.url.path,
                "query": dict(request.query_params),
            }

            if isinstance(self.logger, structlog.stdlib.BoundLogger):
                # structlog logger
                self.logger.info("request_started", http_request=request_info)
            else:
                # Standard Python logger - format the message as a string
                log_msg = f"Request started: {request.method} {request.url.path}"
                self.logger.log(
                    logging.INFO,
                    log_msg,
                    extra={"request_info": request_info},
                )

            # Process the request
            start_time = time.time()
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000

            # Add request ID to response headers
            response.headers[self.header_name] = request_id

            # Log the request completion
            log_data = {
                "status_code": response.status_code,
                "process_time": f"{process_time:.2f}ms",
            }

            # Use the appropriate logger method
            if isinstance(self.logger, structlog.stdlib.BoundLogger):
                # structlog logger
                self.logger.info("request_completed", **log_data)
            else:
                # Standard Python logger
                log_msg = (
                    f"Request completed - Status: {response.status_code} "
                    f"in {process_time:.2f}ms"
                )
                self.logger.log(
                    logging.INFO,
                    log_msg,
                    extra={"response_info": log_data},
                )

            return response

        except Exception as exc:
            # Log the error with proper error handling
            error_info = {
                "type": exc.__class__.__name__,
                "message": str(exc),
            }

            # Log the error using the appropriate method based on logger type
            if isinstance(self.logger, structlog.stdlib.BoundLogger):
                # structlog logger
                self.logger.error("request_failed", error=error_info, exc_info=True)
            else:
                # Standard Python logger
                self.logger.log(
                    logging.ERROR,
                    f"Request failed: {error_info['message']}",
                    extra={"error": error_info},
                    exc_info=True,
                )

            # Re-raise the exception
            raise

        finally:
            # Clear the request context
            clear_request_context()


class LoggingMiddleware:
    """Middleware to configure logging for each request.

    This middleware ensures that all logs include request context and are properly formatted.
    It should be one of the first middlewares in the stack.
    """

    def __init__(
        self,
        app: ASGIApp,
        logger=None,
    ) -> None:
        self.app = app
        self.logger = logger or structlog.get_logger(__name__)

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        request = Request(scope, receive=receive)
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Set up logging context
        with structlog.contextvars.bound_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        ):
            # Add trace context if available
            span = getattr(request.state, "span", None)
            if span and hasattr(span, "trace_id"):
                structlog.contextvars.bind_contextvars(
                    trace_id=span.trace_id.hex(),
                    span_id=span.span_id.hex(),
                )

            # Process request
            await self.app(scope, receive, send)


def configure_logging_middleware(app: ASGIApp) -> ASGIApp:
    """Configure logging middleware with proper ordering."""
    # Get root logger
    logger = logging.getLogger()

    # Add middleware in correct order
    app = LoggingMiddleware(app, logger=logger)
    app = RequestContextLogMiddleware(app, logger=logger)

    return app
