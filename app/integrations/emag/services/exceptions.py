"""Common exceptions for the eMAG integration."""


class EmagError(Exception):
    """Base exception for all eMAG integration errors."""


class EmagAPIError(EmagError):
    """Raised when the eMAG API returns an error response."""


class EmagRateLimitError(EmagError):
    """Raised when rate limited by the eMAG API."""

    def __init__(self, message: str, retry_after: float = None):
        super().__init__(message)
        self.retry_after = retry_after


class EmagAuthenticationError(EmagError):
    """Raised when authentication with the eMAG API fails."""


class EmagValidationError(EmagError):
    """Raised when request validation fails."""


class EmagConnectionError(EmagError):
    """Raised when there are connection issues with the eMAG API."""


class EmagTimeoutError(EmagError):
    """Raised when a request to the eMAG API times out."""


def get_exception_for_status(status_code: int, message: str = None) -> EmagError:
    """Get the appropriate exception for an HTTP status code.

    Args:
        status_code: The HTTP status code
        message: Optional error message

    Returns:
        An appropriate exception instance

    """
    if not message:
        message = f"HTTP {status_code} error occurred"

    if status_code == 400:
        return EmagValidationError(f"Bad Request: {message}")
    if status_code == 401:
        return EmagAuthenticationError(f"Authentication failed: {message}")
    if status_code == 403:
        return EmagAuthenticationError(f"Forbidden: {message}")
    if status_code == 404:
        return EmagResourceNotFoundError(f"Resource not found: {message}")
    if status_code == 409:
        return EmagConflictError(f"Conflict: {message}")
    if status_code == 422:
        return EmagValidationError(f"Validation error: {message}")
    if status_code == 429:
        return EmagRateLimitError(f"Rate limited: {message}")
    if 500 <= status_code < 600:
        return EmagServerError(f"Server error ({status_code}): {message}")
    return EmagAPIError(f"API error ({status_code}): {message}")


# These are defined here to avoid circular imports
class EmagResourceNotFoundError(EmagError):
    """Raised when a requested resource is not found."""


class EmagConflictError(EmagError):
    """Raised when there is a conflict with the current state of the resource."""


class EmagServerError(EmagError):
    """Raised when the eMAG API returns a server error."""
