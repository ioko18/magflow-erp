"""Logging utilities for the application."""

import logging
from typing import Any

from fastapi import Request

# Configure a simple logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("magflow")


def log_request(request: Request, **kwargs: Any) -> None:
    """Log an HTTP request.

    Args:
        request: The incoming request
        **kwargs: Additional context to include in the log

    """
    log_data: dict[str, Any] = {
        "event": "request.received",
        "method": request.method,
        "path": request.url.path,
        "query_params": dict(request.query_params),
        "client": (
            f"{request.client.host}:{request.client.port}" if request.client else None
        ),
        "user_agent": request.headers.get("user-agent"),
    }
    log_data.update(kwargs)
    logger.info(f"Request received: {log_data}")


def log_response(
    request: Request,
    response: Any,
    process_time: float,
    **kwargs: Any,
) -> None:
    """Log an HTTP response.

    Args:
        request: The incoming request
        response: The outgoing response
        process_time: Time taken to process the request in seconds
        **kwargs: Additional context to include in the log

    """
    log_data: dict[str, Any] = {
        "event": "request.completed",
        "method": request.method,
        "path": request.url.path,
        "status_code": getattr(response, "status_code", None),
        "process_time": process_time,
        "client": (
            f"{request.client.host}:{request.client.port}" if request.client else None
        ),
    }
    log_data.update(kwargs)
    logger.info(f"Request completed: {log_data}")


def log_error(
    error: Exception,
    request: Request | None = None,
    **kwargs: Any,
) -> None:
    """Log an error.

    Args:
        error: The exception that was raised
        request: The request that caused the error (if any)
        **kwargs: Additional context to include in the log

    """
    log_data: dict[str, Any] = {
        "event": "error.occurred",
        "error": str(error),
        "error_type": error.__class__.__name__,
    }

    if request:
        log_data.update(
            {
                "method": request.method,
                "path": request.url.path,
                "client": (
                    f"{request.client.host}:{request.client.port}"
                    if request.client
                    else None
                ),
            },
        )

    log_data.update(kwargs)
    logger.error(f"Error occurred: {log_data}")
