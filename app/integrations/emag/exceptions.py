"""Exceptions for the eMAG integration."""

from typing import Any, Dict, List, Optional, Type


class EmagError(Exception):
    """Base exception for all eMAG integration errors."""

    def __init__(
        self,
        message: str = "An error occurred with the eMAG integration",
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class EmagAPIError(EmagError):
    """Raised when there's an error response from the eMAG API."""

    def __init__(
        self,
        message: str,
        status_code: int,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.error_code = error_code
        super().__init__(
            message=message,
            status_code=status_code,
            details=details or {},
        )


class EmagAuthError(EmagError):
    """Raised when there's an authentication or authorization error with the eMAG API."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message=message, status_code=401)


# Alias for backward compatibility
EmagAuthenticationError = EmagAuthError


class EmagConnectionError(EmagError):
    """Raised when there's a network-related error connecting to the eMAG API."""

    def __init__(self, message: str = "Network connection error"):
        super().__init__(message=message, status_code=503)


class EmagResourceNotFoundError(EmagError):
    """Raised when a requested resource is not found in the eMAG API."""

    def __init__(self, message: str = "Requested resource not found"):
        super().__init__(message=message, status_code=404)


class EmagConflictError(EmagError):
    """Raised when there's a conflict with the current state of the target resource."""

    def __init__(
        self,
        message: str = "Conflict with the current state of the resource",
    ):
        super().__init__(message=message, status_code=409)


class EmagServerError(EmagError):
    """Raised when the eMAG API returns a server error (5xx)."""

    def __init__(self, message: str = "Internal server error in eMAG API"):
        super().__init__(message=message, status_code=500)


class EmagRateLimitError(EmagError):
    """Raised when the rate limit for the eMAG API has been exceeded."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message=message, status_code=429)


class EmagValidationError(EmagError):
    """Raised when there's a validation error with the request data."""

    def __init__(
        self,
        message: str = "Validation error",
        errors: Optional[Dict[str, List[str]]] = None,
    ):
        super().__init__(
            message=message,
            status_code=400,
            details={"errors": errors or {}},
        )


def get_exception_for_status(
    status_code: int,
    message: Optional[str] = None,
) -> Type[EmagError]:
    """Get the appropriate exception class for an HTTP status code.

    Args:
        status_code: HTTP status code
        message: Optional custom error message

    Returns:
        An exception class that should be raised for the given status code

    """
    default_message = message or f"HTTP {status_code} error"

    if status_code == 400:
        return EmagValidationError(message or "Bad request")
    if status_code == 401:
        return EmagAuthError(message or "Authentication failed")
    if status_code == 403:
        return EmagAuthError(message or "Forbidden - insufficient permissions")
    if status_code == 404:
        return EmagResourceNotFoundError(message or "Resource not found")
    if status_code == 409:
        return EmagConflictError(
            message or "Conflict with the current state of the resource",
        )
    if status_code == 429:
        return EmagRateLimitError(message or "Rate limit exceeded")
    if 500 <= status_code < 600:
        return EmagServerError(message or "Internal server error")
    return EmagError(message=default_message, status_code=status_code)


class EmagTimeoutError(EmagError):
    """Raised when a request to the eMAG API times out."""

    def __init__(self, message: str = "Request to eMAG API timed out"):
        super().__init__(message=message, status_code=504)


class EmagNetworkError(EmagError):
    """Raised when there's a network error communicating with the eMAG API."""

    def __init__(self, message: str = "Network error communicating with eMAG API"):
        super().__init__(message=message, status_code=503)


class EmagCircuitBreakerError(EmagError):
    """Raised when the circuit breaker is open for the eMAG API."""

    def __init__(self, message: str = "eMAG API is temporarily unavailable"):
        super().__init__(message=message, status_code=503)


class EmagRetryableError(EmagError):
    """Raised when an operation fails but may succeed if retried."""

    def __init__(
        self,
        message: str = "Operation failed but may succeed if retried",
        status_code: Optional[int] = 503,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, status_code=status_code, details=details)


class EmagNonRetryableError(EmagError):
    """Raised when an operation fails and should not be retried."""

    def __init__(
        self,
        message: str = "Operation failed and should not be retried",
        status_code: Optional[int] = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, status_code=status_code, details=details)
