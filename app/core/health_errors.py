"""Custom exceptions for health check functionality."""

from typing import Any, Dict, Optional

from fastapi import status


class HealthCheckError(Exception):
    """Base exception for all health check related errors."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE,
        details: Optional[Dict[str, Any]] = None,
        component: Optional[str] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.component = component
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to a dictionary for JSON response."""
        return {
            "error": {
                "code": self.__class__.__name__,
                "message": self.message,
                "component": self.component,
                **self.details,
            },
        }


class DatabaseHealthError(HealthCheckError):
    """Raised when database health check fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
            component="database",
        )


class DatabaseConnectionError(DatabaseHealthError):
    """Raised when unable to connect to the database."""

    def __init__(self, error: Exception):
        super().__init__(
            message="Failed to connect to database",
            details={"error": str(error), "type": error.__class__.__name__},
        )


class DatabaseQueryError(DatabaseHealthError):
    """Raised when a database query fails."""

    def __init__(self, error: Exception):
        super().__init__(
            message="Database query failed",
            details={"error": str(error), "type": error.__class__.__name__},
        )


class DatabaseTimeoutError(DatabaseHealthError):
    """Raised when a database operation times out."""

    def __init__(self, timeout: float):
        super().__init__(
            message=f"Database operation timed out after {timeout} seconds",
            details={"timeout_seconds": timeout},
        )


class ExternalServiceError(HealthCheckError):
    """Raised when an external service health check fails."""

    def __init__(self, service_name: str, error: Exception):
        super().__init__(
            message=f"{service_name} service is unavailable",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={
                "service": service_name,
                "error": str(error),
                "type": error.__class__.__name__,
            },
            component=service_name.lower(),
        )


class HealthCheckTimeoutError(HealthCheckError):
    """Raised when a health check times out."""

    def __init__(self, component: str, timeout: float):
        super().__init__(
            message=f"Health check for {component} timed out after {timeout} seconds",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            details={"timeout_seconds": timeout},
            component=component,
        )


class ServiceNotReadyError(HealthCheckError):
    """Raised when the service is not yet ready to handle requests."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_425_TOO_EARLY,
            details=details,
            component="service",
        )


class CircuitBreakerOpenError(HealthCheckError):
    """Raised when the circuit breaker is open and blocks the request."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details or {},
            component="circuit_breaker",
        )


class ServiceUnavailableError(HealthCheckError):
    """Raised when a service is temporarily unavailable."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details or {},
            component="service",
        )


class ConfigurationError(HealthCheckError):
    """Raised when there is a configuration error affecting health checks."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            component="configuration",
        )
