"""Logging utilities for the application."""

import logging
from typing import Any, Dict, Optional

from fastapi import Request


def log_request(request: Request, **kwargs: Any) -> None:
    """Log an HTTP request."""
    log_data: Dict[str, Any] = {
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
    logger = logging.getLogger("magflow")
    logger.info(f"Request received: {log_data}")


def log_response(
    request: Request,
    response: Any,
    process_time: float,
    **kwargs: Any,
) -> None:
    """Log an HTTP response."""
    log_data: Dict[str, Any] = {
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
    logger = logging.getLogger("magflow")
    logger.info(f"Request completed: {log_data}")


def log_error(
    error: Exception,
    request: Optional[Request] = None,
    **kwargs: Any,
) -> None:
    """Log an error."""
    log_data: Dict[str, Any] = {
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
    logger = logging.getLogger("magflow")
    logger.error(f"Error occurred: {log_data}")
