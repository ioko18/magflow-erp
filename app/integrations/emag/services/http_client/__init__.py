"""eMAG HTTP Client

This module re-exports exceptions from the main exceptions module for backward compatibility.
"""

# Import from the main exceptions module to avoid circular imports
from ...exceptions import (
    EmagAPIError,
    EmagConflictError,
    EmagError,
    EmagRateLimitError,
    EmagResourceNotFoundError,
    EmagServerError,
    EmagTimeoutError,
    EmagValidationError,
)
from ...exceptions import (
    EmagAuthError as EmagAuthenticationError,
)
from ...exceptions import (
    EmagNetworkError as EmagConnectionError,
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


def get_exception_for_status(status_code: int, default=EmagError):
    """Get the appropriate exception class for an HTTP status code."""
    return base_get_exception_for_status(status_code, default)
