"""Custom exceptions for MagFlow ERP.

This module defines application-specific exceptions that provide
better error handling and debugging capabilities.
"""

from typing import Any

from fastapi import HTTPException, status


class MagFlowBaseException(Exception):
    """Base exception for all MagFlow application errors."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        error_code: str | None = None,
    ):
        self.message = message
        self.details = details or {}
        self.error_code = error_code or self.__class__.__name__
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class DatabaseError(MagFlowBaseException):
    """Database-related errors."""


class DatabaseServiceError(DatabaseError):
    """Database service-specific errors."""


class ServiceError(MagFlowBaseException):
    """General service layer errors."""


class ValidationError(MagFlowBaseException):
    """Data validation errors."""


class AuthenticationError(MagFlowBaseException):
    """Authentication and authorization errors."""


class ConnectionServiceError(MagFlowBaseException):
    """Connection service-specific errors."""


class ConfigurationError(MagFlowBaseException):
    """Configuration-related errors."""


class ExternalServiceError(MagFlowBaseException):
    """External service integration errors."""


class ResourceNotFoundError(MagFlowBaseException):
    """Resource not found errors."""


# HTTP status mappings for MagFlow exceptions
STATUS_CODE_MAP: dict[type[MagFlowBaseException], int] = {
    ValidationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    ResourceNotFoundError: status.HTTP_404_NOT_FOUND,
    ConfigurationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    DatabaseError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ConnectionServiceError: status.HTTP_503_SERVICE_UNAVAILABLE,
    ExternalServiceError: status.HTTP_502_BAD_GATEWAY,
    MagFlowBaseException: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


# HTTP Exception mappings
def create_http_exception(exc: MagFlowBaseException) -> HTTPException:
    """Convert MagFlow exceptions to HTTP exceptions."""
    for exc_type, code in STATUS_CODE_MAP.items():
        if isinstance(exc, exc_type):
            return HTTPException(status_code=code, detail=exc.to_dict())

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=exc.to_dict(),
    )
