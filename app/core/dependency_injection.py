"""Dependency Injection Container and Service Factory for MagFlow ERP.

This module provides a comprehensive dependency injection system that enables
better separation of concerns, testability, and maintainability across the application.
"""

import contextlib
import inspect
import logging
import os
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any, Generic, TypeVar

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_async_session
from app.core.database_resilience import DatabaseHealthChecker
from app.core.exceptions import ConfigurationError

# Type variables for generic dependency injection
T = TypeVar("T")
ServiceType = TypeVar("ServiceType")

logger = logging.getLogger(__name__)


@dataclass
class ServiceContext:
    """Context object for service initialization and configuration."""

    settings: Any
    db_session: AsyncSession | None = None
    cache_service: Any | None = None
    health_checker: DatabaseHealthChecker | None = None
    environment: dict[str, str] | None = None

    def __post_init__(self):
        """Validate context configuration and initialize environment."""
        if not self.settings:
            raise ConfigurationError("Settings are required for service context")

        # Initialize environment variables if not provided
        if self.environment is None:
            self.environment = {}

        # Add environment variables from settings if they exist
        for key, value in os.environ.items():
            if key.startswith(("EMAG_", "DB_")):
                self.environment[key] = value

        logger.debug(
            "ServiceContext initialized with settings: %s and %d environment variables",
            self.settings.APP_ENV,
            len(self.environment),
        )


class ServiceProvider(Generic[T]):
    """Generic service provider that handles service creation and lifecycle."""

    def __init__(self, service_class: type[T], dependencies: dict[str, Any] = None):
        self.service_class = service_class
        self.dependencies = dependencies or {}
        self._instance: T | None = None
        self._singleton = False

    def singleton(self) -> "ServiceProvider[T]":
        """Mark this provider as singleton (single instance per container)."""
        self._singleton = True
        return self

    def get_instance(self, context: ServiceContext) -> T:
        """Get service instance, creating it if necessary."""
        if self._singleton and self._instance:
            return self._instance

        # Create new instance
        instance = self._create_instance(context)

        if self._singleton:
            self._instance = instance

        return instance

    def _create_instance(self, context: ServiceContext) -> T:
        """Create service instance with dependency injection."""
        try:
            # Get constructor parameters
            sig = inspect.signature(self.service_class.__init__)
            params = {}

            # Resolve dependencies
            for param_name, _param in sig.parameters.items():
                if param_name == "self":
                    continue

                # Check if parameter is provided in dependencies
                if param_name in self.dependencies:
                    params[param_name] = self.dependencies[param_name]
                # Check if parameter is available in context
                elif hasattr(context, param_name):
                    params[param_name] = getattr(context, param_name)
                # Try to get from context dict-style
                elif hasattr(context, "__getitem__"):
                    with contextlib.suppress(KeyError):
                        params[param_name] = context[param_name]
                else:
                    # Try to resolve automatically
                    params[param_name] = self._resolve_dependency(param_name, context)

            return self.service_class(**params)

        except Exception as e:
            logger.error(
                "Failed to create service instance for %s: %s",
                self.service_class.__name__,
                e,
            )
            raise ConfigurationError(
                f"Failed to initialize {self.service_class.__name__}: {e}",
            ) from e

    def _resolve_dependency(self, param_name: str, context: ServiceContext) -> Any:
        """Resolve dependency automatically based on type hints."""
        # This could be extended to automatically resolve common dependencies
        # For now, raise an error if dependency cannot be resolved
        raise ConfigurationError(
            f"Cannot resolve dependency '{param_name}' for {self.service_class.__name__}",
        )


class DependencyContainer:
    """Central dependency injection container."""

    def __init__(self):
        self._providers: dict[str, ServiceProvider] = {}
        self._instances: dict[str, Any] = {}
        self._context: ServiceContext | None = None

    def register(
        self,
        name: str,
        service_class: type[T],
        dependencies: dict[str, Any] = None,
    ) -> ServiceProvider[T]:
        """Register a service provider."""
        provider = ServiceProvider(service_class, dependencies)
        self._providers[name] = provider
        logger.debug(
            "Registered service provider: %s -> %s",
            name,
            service_class.__name__,
        )
        return provider

    def singleton(
        self,
        name: str,
        service_class: type[T],
        dependencies: dict[str, Any] = None,
    ) -> ServiceProvider[T]:
        """Register a singleton service provider."""
        provider = ServiceProvider(service_class, dependencies).singleton()
        self._providers[name] = provider
        logger.debug(
            "Registered singleton service provider: %s -> %s",
            name,
            service_class.__name__,
        )
        return provider

    def get(self, name: str) -> Any:
        """Get service instance by name."""
        if name not in self._providers:
            raise ConfigurationError(f"Service '{name}' is not registered")

        if self._context is None:
            raise ConfigurationError(
                "ServiceContext not initialized. Call initialize() first.",
            )

        return self._providers[name].get_instance(self._context)

    def initialize(self, context: ServiceContext):
        """Initialize the container with service context."""
        self._context = context
        logger.info("Dependency container initialized with context")

    def reset(self):
        """Reset the container (useful for testing)."""
        self._instances.clear()
        self._context = None
        logger.debug("Dependency container reset")


# Global container instance
_container = DependencyContainer()


def get_container() -> DependencyContainer:
    """Get the global dependency container."""
    return _container


def initialize_container(db_session: AsyncSession = None):
    """Initialize the global dependency container."""
    settings = get_settings()

    # Create service context
    context = ServiceContext(
        settings=settings,
        db_session=db_session,
        health_checker=(
            DatabaseHealthChecker(lambda: db_session) if db_session else None
        ),
    )

    _container.initialize(context)
    logger.info("Global dependency container initialized")


class ServiceBase(ABC):
    """Base class for all services with common functionality."""

    def __init__(self, context: ServiceContext):
        self.context = context
        self.settings = context.settings
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def initialize(self):
        """Initialize the service."""

    @abstractmethod
    async def cleanup(self):
        """Cleanup service resources."""


class DatabaseService(ServiceBase):
    """Centralized database service for session management."""

    def __init__(self, context: ServiceContext):
        super().__init__(context)
        self._session = context.db_session
        self._health_checker = context.health_checker

    async def initialize(self):
        """Initialize database service."""
        if self._health_checker:
            await self._health_checker.ensure_healthy()
        self.logger.info("Database service initialized")

    async def cleanup(self):
        """Cleanup database resources."""
        if self._session:
            await self._session.close()
        self.logger.info("Database service cleaned up")

    async def get_session(self) -> AsyncSession:
        """Get database session."""
        if not self._session:
            raise ConfigurationError("Database session not available")
        return self._session

    async def check_health(self) -> bool:
        """Check database health."""
        if not self._health_checker:
            return False
        return await self._health_checker.check_health()


class CacheService(ServiceBase):
    """Centralized caching service."""

    def __init__(self, context: ServiceContext):
        super().__init__(context)
        self._cache_backend = None  # Will be set by configuration

    async def initialize(self):
        """Initialize cache service."""
        from app.core.cache import get_redis

        try:
            self._redis = await get_redis()
            self.logger.info("Cache service initialized with Redis")
        except Exception as e:
            self.logger.error(f"Failed to initialize cache: {e}")
            self._redis = None

    async def cleanup(self):
        """Cleanup cache resources."""
        from app.core.cache import close_redis

        try:
            await close_redis()
            self.logger.info("Cache service cleaned up")
        except Exception as e:
            self.logger.error(f"Error cleaning up cache: {e}")

    async def get(self, key: str) -> Any:
        """Get value from cache."""
        if not self._redis:
            return None
        try:
            import pickle

            value = await self._redis.get(key)
            if value:
                return pickle.loads(value)
            return None
        except Exception as e:
            self.logger.error(f"Cache get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache."""
        if not self._redis:
            return False
        try:
            import pickle

            serialized = pickle.dumps(value)
            await self._redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            self.logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self._redis:
            return False
        try:
            await self._redis.delete(key)
            return True
        except Exception as e:
            self.logger.error(f"Cache delete error for key {key}: {e}")
            return False


class AuthenticationService(ServiceBase):
    """Centralized authentication service."""

    def __init__(self, context: ServiceContext):
        super().__init__(context)

    async def initialize(self):
        """Initialize authentication service."""
        # TODO: Initialize JWT keys, etc.
        self.logger.info("Authentication service initialized")

    async def cleanup(self):
        """Cleanup authentication resources."""
        self.logger.info("Authentication service cleaned up")

    async def authenticate_user(self, email: str, password: str) -> dict[str, Any]:
        """Authenticate user credentials."""
        # TODO: Implement user authentication logic
        return {"user_id": 1, "email": email, "authenticated": True}

    async def generate_token(self, user_data: dict[str, Any]) -> str:
        """Generate JWT token for user."""
        # TODO: Implement JWT token generation
        return "jwt_token_here"

    async def validate_token(self, token: str) -> dict[str, Any]:
        """Validate JWT token."""
        # TODO: Implement JWT token validation
        return {"user_id": 1, "valid": True}


class ReportingService(ServiceBase):
    """Centralized reporting service."""

    def __init__(self, context: ServiceContext):
        super().__init__(context)

    async def initialize(self):
        """Initialize reporting service."""
        self.logger.info("Reporting service initialized")

    async def cleanup(self):
        """Cleanup reporting resources."""
        self.logger.info("Reporting service cleaned up")

    async def generate_report(
        self,
        report_type: str,
        filters: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """Generate report data."""
        # TODO: Implement report generation logic
        return {
            "report_type": report_type,
            "data": {},
            "generated_at": "2024-01-01T00:00:00Z",
        }


# Dependency injection providers
def get_database_service() -> DatabaseService:
    """Dependency provider for DatabaseService."""
    return _container.get("database_service")


def get_cache_service() -> CacheService:
    """Dependency provider for CacheService."""
    return _container.get("cache_service")


def get_authentication_service() -> AuthenticationService:
    """Dependency provider for AuthenticationService."""
    return _container.get("authentication_service")


def get_reporting_service() -> ReportingService:
    """Dependency provider for ReportingService."""
    return _container.get("reporting_service")


def get_service_context() -> ServiceContext:
    """Dependency provider for ServiceContext."""
    if not _container._context:
        raise ConfigurationError("ServiceContext not initialized")
    return _container._context


# FastAPI dependency injection helpers
def inject_database_service(
    session: AsyncSession = Depends(get_async_session),
) -> DatabaseService:
    """FastAPI dependency for DatabaseService with session injection."""
    # This will be implemented when we integrate with FastAPI


def inject_cache_service() -> CacheService:
    """FastAPI dependency for CacheService."""
    return get_cache_service()


def inject_auth_service() -> AuthenticationService:
    """FastAPI dependency for AuthenticationService."""
    return get_authentication_service()


def inject_reporting_service() -> ReportingService:
    """FastAPI dependency for ReportingService."""
    return get_reporting_service()


# Service registration helper
def register_services():
    """Register all services with the dependency container."""
    container = get_container()

    # Register services as singletons
    container.singleton("database_service", DatabaseService)
    container.singleton("cache_service", CacheService)
    container.singleton("authentication_service", AuthenticationService)
    container.singleton("reporting_service", ReportingService)

    logger.info("All services registered with dependency container")


# Utility decorator for service methods
def with_database_session(func: Callable):
    """Decorator to inject database session into service methods."""

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        if not isinstance(self, ServiceBase):
            raise ConfigurationError(
                "Service method decorator can only be used on ServiceBase subclasses",
            )

        session = await self.get_session() if hasattr(self, "get_session") else None
        if session:
            kwargs["_session"] = session

        return await func(self, *args, **kwargs)

    return wrapper


def with_transaction(func: Callable):
    """Decorator to wrap service method in database transaction."""

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        if not isinstance(self, ServiceBase):
            raise ConfigurationError(
                "Transaction decorator can only be used on ServiceBase subclasses",
            )

        session = kwargs.get("_session")
        if not session:
            raise ConfigurationError("Database session required for transaction")

        try:
            result = await func(self, *args, **kwargs)
            await session.commit()
            return result
        except Exception as e:
            await session.rollback()
            raise e

    return wrapper


# Error handling utilities for services
class ServiceError(Exception):
    """Base exception for service-related errors."""

    def __init__(self, message: str, details: dict[str, Any] = None):
        super().__init__(message)
        self.details = details or {}


class DatabaseServiceError(ServiceError):
    """Exception for database service errors."""


class CacheServiceError(ServiceError):
    """Exception for cache service errors."""


class AuthenticationServiceError(ServiceError):
    """Exception for authentication service errors."""


# Initialize logging for this module
logging.basicConfig(level=logging.INFO)
logger.setLevel(logging.INFO)
