"""Custom exceptions for MagFlow ERP.

This module defines application-specific exceptions that provide
better error handling and debugging capabilities.
"""

from typing import Any, Dict, Optional

from fastapi import HTTPException, status


class MagFlowBaseException(Exception):
    """Base exception for all MagFlow application errors."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
    ):
        self.message = message
        self.details = details or {}
        self.error_code = error_code or self.__class__.__name__
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
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


# HTTP Exception mappings
def create_http_exception(exc: MagFlowBaseException) -> HTTPException:
    """Convert MagFlow exceptions to HTTP exceptions."""
    status_code_map = {
        "ValidationError": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "AuthenticationError": status.HTTP_401_UNAUTHORIZED,
        "ResourceNotFoundError": status.HTTP_404_NOT_FOUND,
        "ConfigurationError": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "DatabaseError": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "ConnectionServiceError": status.HTTP_503_SERVICE_UNAVAILABLE,
        "ExternalServiceError": status.HTTP_502_BAD_GATEWAY,
    }

    status_code = status_code_map.get(
        exc.error_code,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

    return HTTPException(status_code=status_code, detail=exc.to_dict())
