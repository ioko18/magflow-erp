"""Base service class for all services in the MagFlow application.

This module provides a base class that all service classes should inherit from.
It includes common functionality like logging, error handling, and service context.
"""

from typing import Any, Dict, Optional

from app.core.logging import get_logger
from app.services.service_context import ServiceContext


class BaseService:
    """Base class for all service classes in the application.

    Provides common functionality and utilities that all services might need.
    """

    def __init__(self, context: Optional[ServiceContext] = None):
        """Initialize the base service with an optional service context.

        Args:
            context: The service context containing dependencies like database session, cache, etc.
        """
        self.context = context or ServiceContext()
        self.logger = get_logger(self.__class__.__module__)

    async def initialize(self) -> None:
        """Initialize the service and its dependencies.

        This method should be overridden by subclasses to perform any
        initialization that requires async operations.
        """
        pass

    async def close(self) -> None:
        """Clean up resources used by the service.

        This method should be overridden by subclasses to perform any
        cleanup that requires async operations.
        """
        pass

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def _format_error(
        self, message: str, error: Optional[Exception] = None, **kwargs
    ) -> Dict[str, Any]:
        """Format an error message with additional context.

        Args:
            message: The main error message.
            error: Optional exception that caused the error.
            **kwargs: Additional context to include in the error details.

        Returns:
            A dictionary containing the formatted error information.
        """
        error_info = {"message": message, "details": dict(kwargs)}

        if error is not None:
            error_info["error"] = str(error)
            error_info["error_type"] = error.__class__.__name__

        return error_info
