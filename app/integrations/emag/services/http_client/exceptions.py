"""Exceptions for the eMAG API client.

This module re-exports exceptions from the main exceptions module for backward compatibility.
"""

# Import from the main exceptions module to avoid circular imports
from ...exceptions import (
    EmagAPIError,
    EmagAuthenticationError,
    EmagConflictError,
    EmagConnectionError,
    EmagError,
    EmagRateLimitError,
    EmagResourceNotFoundError,
    EmagServerError,
    EmagTimeoutError,
    EmagValidationError,
)
from ...exceptions import (
    get_exception_for_status as base_get_exception_for_status,
)

# Re-export all exceptions for backward compatibility
__all__ = [
    "EmagAPIError",
    "EmagAuthenticationError",
    "EmagConflictError",
    "EmagConnectionError",
    "EmagError",
    "EmagRateLimitError",
    "EmagResourceNotFoundError",
    "EmagServerError",
    "EmagTimeoutError",
    "EmagValidationError",
    "get_exception_for_status",
]

# Map HTTP status codes to exception classes
STATUS_CODE_TO_EXCEPTION = {
    400: EmagError,
    401: EmagAuthenticationError,
    403: EmagAuthenticationError,
    404: EmagResourceNotFoundError,
    409: EmagConflictError,
    422: EmagValidationError,
    429: EmagRateLimitError,
}


def get_exception_for_status(status_code: int, default=EmagError):
    """Get the appropriate exception class for an HTTP status code."""
    return base_get_exception_for_status(status_code, default)
