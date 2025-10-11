"""Error handling middleware for MagFlow ERP API.

This module provides centralized error handling and response formatting
for consistent API error responses across all endpoints.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    ConfigurationError,
    DatabaseServiceError,
    ServiceError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware:
    """Middleware for handling and formatting API errors consistently."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Process the request
        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            # Handle the exception and send error response
            response = await self.handle_exception(exc, scope)
            await send(
                {
                    "type": "http.response.start",
                    "status": response.status_code,
                    "headers": [
                        [b"content-type", b"application/json"],
                    ],
                },
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": response.body,
                },
            )

    async def handle_exception(self, exc: Exception, scope: dict) -> JSONResponse:
        """Handle different types of exceptions and return formatted responses."""
        request = Request(scope, {})

        if isinstance(exc, HTTPException):
            return await self.handle_http_exception(exc, request)

        if isinstance(exc, RequestValidationError):
            return await self.handle_validation_error(exc, request)

        if isinstance(exc, DatabaseServiceError):
            return await self.handle_database_error(exc, request)

        if isinstance(exc, ConfigurationError):
            return await self.handle_configuration_error(exc, request)

        if isinstance(exc, ValidationError):
            return await self.handle_validation_error_custom(exc, request)

        if isinstance(exc, ServiceError):
            return await self.handle_service_error(exc, request)

        return await self.handle_generic_error(exc, request)

    async def handle_http_exception(
        self,
        exc: HTTPException,
        request: Request,
    ) -> JSONResponse:
        """Handle FastAPI HTTP exceptions."""
        logger.warning(f"HTTP Exception: {exc.detail} (Status: {exc.status_code})")

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTPException",
                "message": exc.detail,
                "path": str(request.url.path),
                "method": request.method,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    async def handle_validation_error(
        self,
        exc: RequestValidationError,
        request: Request,
    ) -> JSONResponse:
        """Handle FastAPI request validation errors."""
        errors = []
        for error in exc.errors():
            errors.append(
                {
                    "field": ".".join(str(loc) for loc in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                },
            )

        logger.warning(f"Validation Error: {errors}")

        return JSONResponse(
            status_code=422,
            content={
                "error": "ValidationError",
                "message": "Request validation failed",
                "details": errors,
                "path": str(request.url.path),
                "method": request.method,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    async def handle_database_error(
        self,
        exc: DatabaseServiceError,
        request: Request,
    ) -> JSONResponse:
        """Handle database service errors."""
        logger.error(f"Database Error: {exc}", exc_info=True)

        status_code = getattr(exc, "status_code", 500)
        if not isinstance(status_code, int):
            status_code = 500

        return JSONResponse(
            status_code=status_code,
            content={
                "error": "DatabaseError",
                "message": "Database operation failed",
                "details": exc.details if hasattr(exc, "details") else {},
                "path": str(request.url.path),
                "method": request.method,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    async def handle_configuration_error(
        self,
        exc: ConfigurationError,
        request: Request,
    ) -> JSONResponse:
        """Handle configuration errors."""
        logger.error(f"Configuration Error: {exc}", exc_info=True)

        return JSONResponse(
            status_code=500,
            content={
                "error": "ConfigurationError",
                "message": "Application configuration error",
                "details": exc.details if hasattr(exc, "details") else {},
                "path": str(request.url.path),
                "method": request.method,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    async def handle_validation_error_custom(
        self,
        exc: ValidationError,
        request: Request,
    ) -> JSONResponse:
        """Handle custom validation errors."""
        logger.warning(f"Custom Validation Error: {exc}")

        return JSONResponse(
            status_code=400,
            content={
                "error": "ValidationError",
                "message": str(exc),
                "details": exc.details if hasattr(exc, "details") else {},
                "path": str(request.url.path),
                "method": request.method,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    async def handle_service_error(
        self,
        exc: ServiceError,
        request: Request,
    ) -> JSONResponse:
        """Handle service layer errors."""
        logger.error(f"Service Error: {exc}", exc_info=True)

        status_code = getattr(exc, "status_code", 500)
        if not isinstance(status_code, int):
            status_code = 500

        return JSONResponse(
            status_code=status_code,
            content={
                "error": "ServiceError",
                "message": str(exc),
                "details": exc.details if hasattr(exc, "details") else {},
                "path": str(request.url.path),
                "method": request.method,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    async def handle_generic_error(
        self,
        exc: Exception,
        request: Request,
    ) -> JSONResponse:
        """Handle generic/unknown errors."""
        logger.error(f"Unexpected Error: {exc}", exc_info=True)

        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred",
                "path": str(request.url.path),
                "method": request.method,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )


# Error response models
class ErrorResponse:
    """Base error response model."""

    def __init__(
        self,
        error: str,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        self.error = error
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "error": self.error,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class DatabaseErrorResponse(ErrorResponse):
    """Database error response."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__("DatabaseError", message, details)


class ValidationErrorResponse(ErrorResponse):
    """Validation error response."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__("ValidationError", message, details)


class ServiceErrorResponse(ErrorResponse):
    """Service error response."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__("ServiceError", message, details)


class ConfigurationErrorResponse(ErrorResponse):
    """Configuration error response."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__("ConfigurationError", message, details)


# Utility functions for error handling
def create_error_response(
    error_type: str,
    message: str,
    status_code: int = 500,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    """Create a standardized error response."""
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(error_type, message, details).to_dict(),
    )


def handle_database_exception(exc: Exception) -> JSONResponse:
    """Handle database-related exceptions."""
    if isinstance(exc, DatabaseServiceError):
        return create_error_response(
            "DatabaseError",
            str(exc),
            getattr(exc, "status_code", 500),
            getattr(exc, "details", {}),
        )
    return create_error_response("DatabaseError", "Database operation failed", 500)


def handle_validation_exception(exc: Exception) -> JSONResponse:
    """Handle validation-related exceptions."""
    if isinstance(exc, ValidationError):
        return create_error_response(
            "ValidationError",
            str(exc),
            400,
            getattr(exc, "details", {}),
        )
    return create_error_response(
        "ValidationError",
        "Request validation failed",
        400,
    )


def handle_service_exception(exc: Exception) -> JSONResponse:
    """Handle service layer exceptions."""
    if isinstance(exc, ServiceError):
        return create_error_response(
            "ServiceError",
            str(exc),
            getattr(exc, "status_code", 500),
            getattr(exc, "details", {}),
        )
    return create_error_response("ServiceError", "Service operation failed", 500)
