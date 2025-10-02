"""
eMAG API Error Handling.

Custom exceptions and retry logic for eMAG API integration conforming to v4.4.8 specifications.
"""

import asyncio
import logging
from typing import Optional, Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)


class EmagApiError(Exception):
    """Base exception for eMAG API errors."""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
        response_data: Optional[dict] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(self.message)

    def __str__(self):
        parts = [self.message]
        if self.code:
            parts.append(f"Code: {self.code}")
        if self.status_code:
            parts.append(f"Status: {self.status_code}")
        return " | ".join(parts)


class RateLimitError(EmagApiError):
    """Rate limit exceeded error."""

    def __init__(self, remaining_seconds: int = 60, message: Optional[str] = None):
        self.remaining_seconds = remaining_seconds
        msg = message or f"Rate limit exceeded. Retry in {remaining_seconds}s"
        super().__init__(
            message=msg,
            code="RATE_LIMIT_EXCEEDED",
            status_code=429
        )


class AuthenticationError(EmagApiError):
    """Authentication failed error."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            code="AUTH_FAILED",
            status_code=401
        )


class ValidationError(EmagApiError):
    """Data validation failed error."""

    def __init__(self, message: str, validation_errors: Optional[list] = None):
        self.validation_errors = validation_errors or []
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            response_data={"errors": self.validation_errors}
        )


class ResourceNotFoundError(EmagApiError):
    """Resource not found error."""

    def __init__(self, resource_type: str, resource_id: str):
        message = f"{resource_type} not found: {resource_id}"
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404
        )


class BusinessLogicError(EmagApiError):
    """Business logic validation error."""

    def __init__(self, message: str, code: str = "BUSINESS_ERROR"):
        super().__init__(
            message=message,
            code=code,
            status_code=422
        )


class NetworkError(EmagApiError):
    """Network communication error."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.original_error = original_error
        super().__init__(
            message=message,
            code="NETWORK_ERROR",
            status_code=503
        )


class TimeoutError(EmagApiError):
    """Request timeout error."""

    def __init__(self, message: str = "Request timed out"):
        super().__init__(
            message=message,
            code="TIMEOUT",
            status_code=504
        )


async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 64.0,
    exponential: bool = True,
    retry_on: tuple = (RateLimitError, NetworkError, TimeoutError)
) -> Any:
    """
    Retry function with exponential backoff conforming to eMAG API guidelines.
    
    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (default: 2s)
        max_delay: Maximum delay in seconds (default: 64s)
        exponential: Use exponential backoff (default: True)
        retry_on: Tuple of exception types to retry on
        
    Returns:
        Result of the function call
        
    Raises:
        The last exception if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except retry_on as e:
            last_exception = e

            if attempt == max_retries:
                logger.error(f"All {max_retries} retry attempts failed: {e}")
                raise

            # Calculate delay
            if isinstance(e, RateLimitError):
                # Use the remaining_seconds from rate limit error
                delay = min(e.remaining_seconds, max_delay)
            elif exponential:
                # Exponential backoff: 2s, 4s, 8s, 16s, 32s, 64s
                delay = min(base_delay * (2 ** attempt), max_delay)
            else:
                # Linear backoff
                delay = min(base_delay * (attempt + 1), max_delay)

            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                f"Retrying in {delay:.1f}s..."
            )
            await asyncio.sleep(delay)
        except Exception as e:
            # Don't retry on other exceptions
            logger.error(f"Non-retryable error: {e}")
            raise

    # This should never be reached, but just in case
    if last_exception:
        raise last_exception


def retry_on_error(
    max_retries: int = 3,
    base_delay: float = 2.0,
    exponential: bool = True
):
    """
    Decorator for automatic retry with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        exponential: Use exponential backoff
        
    Example:
        @retry_on_error(max_retries=3, base_delay=2.0)
        async def fetch_orders():
            return await emag_api.get_orders()
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_with_backoff(
                lambda: func(*args, **kwargs),
                max_retries=max_retries,
                base_delay=base_delay,
                exponential=exponential
            )
        return wrapper
    return decorator


class ErrorHandler:
    """Centralized error handler for eMAG API operations."""

    @staticmethod
    def handle_http_error(status_code: int, response_data: dict) -> EmagApiError:
        """
        Convert HTTP error response to appropriate exception.
        
        Args:
            status_code: HTTP status code
            response_data: Response data from API
            
        Returns:
            Appropriate EmagApiError subclass
        """
        message = response_data.get("message", "Unknown error")
        code = response_data.get("code")

        if status_code == 400:
            errors = response_data.get("errors", [])
            return ValidationError(message, validation_errors=errors)
        elif status_code == 401:
            return AuthenticationError(message)
        elif status_code == 404:
            return ResourceNotFoundError("Resource", response_data.get("id", "unknown"))
        elif status_code == 422:
            return BusinessLogicError(message, code=code or "BUSINESS_ERROR")
        elif status_code == 429:
            retry_after = response_data.get("retry_after", 60)
            return RateLimitError(remaining_seconds=retry_after, message=message)
        elif status_code >= 500:
            return NetworkError(message)
        else:
            return EmagApiError(message, code=code, status_code=status_code)

    @staticmethod
    def is_retryable(error: Exception) -> bool:
        """
        Check if an error is retryable.
        
        Args:
            error: Exception to check
            
        Returns:
            True if error should be retried
        """
        return isinstance(error, (RateLimitError, NetworkError, TimeoutError))

    @staticmethod
    def get_retry_delay(error: Exception, attempt: int, base_delay: float = 2.0) -> float:
        """
        Calculate retry delay for an error.
        
        Args:
            error: Exception that occurred
            attempt: Current attempt number (0-indexed)
            base_delay: Base delay in seconds
            
        Returns:
            Delay in seconds before retry
        """
        if isinstance(error, RateLimitError):
            return error.remaining_seconds

        # Exponential backoff: 2s, 4s, 8s, 16s, 32s, 64s
        return min(base_delay * (2 ** attempt), 64.0)


def log_error(error: EmagApiError, context: Optional[dict] = None):
    """
    Log error with context information.
    
    Args:
        error: EmagApiError instance
        context: Additional context information
    """
    context = context or {}
    logger.error(
        f"eMAG API Error: {error}",
        extra={
            "error_code": error.code,
            "status_code": error.status_code,
            "response_data": error.response_data,
            **context
        }
    )
