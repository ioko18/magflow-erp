"""FastAPI dependency providers for MagFlow ERP services.

This module provides FastAPI dependency injection providers that integrate
with the service registry system for clean API endpoint implementation.
"""

from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database_resilience import DatabaseHealthChecker
from app.core.dependency_injection import ServiceContext
from app.core.service_registry import get_service_registry, initialize_service_registry
from app.db.models import User
from app.security.jwt import oauth2_scheme


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session.

    FIXED: Now uses the shared session factory from app.db.session
    instead of creating a separate engine. This prevents memory leaks
    from multiple connection pools.
    """
    # Import from the canonical source - single connection pool
    from app.db.session import get_async_db

    # Delegate to the standard session provider
    async for session in get_async_db():
        yield session


async def get_service_context(
    db_session: AsyncSession = Depends(get_database_session),
) -> ServiceContext:
    """FastAPI dependency for service context."""
    # Initialize service registry if not already done
    if not get_service_registry().is_initialized:
        await initialize_service_registry(db_session)

    # Get context from service registry
    context = get_service_registry()._context
    if not context:
        raise RuntimeError("Service context not initialized")

    return context


# Service dependency providers
async def get_reporting_service(
    context: ServiceContext = Depends(get_service_context),
) -> "ReportingService":  # noqa: F821
    """FastAPI dependency for ReportingService."""
    from app.services.reporting_service import ReportingService

    return ReportingService(context)


async def get_database_service(
    context: ServiceContext = Depends(get_service_context),
) -> "DatabaseService":  # noqa: F821
    """FastAPI dependency for DatabaseService."""
    from app.core.dependency_injection import DatabaseService

    return DatabaseService(context)


async def get_cache_service(
    context: ServiceContext = Depends(get_service_context),
) -> "CacheService":  # noqa: F821
    """FastAPI dependency for CacheService."""
    from app.core.dependency_injection import CacheService

    return CacheService(context)


async def get_authentication_service(
    context: ServiceContext = Depends(get_service_context),
) -> "AuthenticationService":  # noqa: F821
    """FastAPI dependency for AuthenticationService."""
    from app.core.dependency_injection import AuthenticationService

    return AuthenticationService(context)


# Repository dependency providers
async def get_user_repository(
    context: ServiceContext = Depends(get_service_context),
) -> "UserRepository":  # noqa: F821
    """FastAPI dependency for UserRepository."""
    from app.core.dependency_injection import DatabaseService
    from app.core.repositories import UserRepository

    db_service = DatabaseService(context)
    return UserRepository(db_service)


async def get_product_repository(
    context: ServiceContext = Depends(get_service_context),
) -> "ProductRepository":  # noqa: F821
    """FastAPI dependency for ProductRepository."""
    from app.core.dependency_injection import DatabaseService
    from app.core.repositories import ProductRepository

    db_service = DatabaseService(context)
    return ProductRepository(db_service)


async def get_order_repository(
    context: ServiceContext = Depends(get_service_context),
) -> "OrderRepository":  # noqa: F821
    """FastAPI dependency for OrderRepository."""
    from app.core.dependency_injection import DatabaseService
    from app.core.repositories import OrderRepository

    db_service = DatabaseService(context)
    return OrderRepository(db_service)


async def get_audit_log_repository(
    context: ServiceContext = Depends(get_service_context),
) -> "AuditLogRepository":  # noqa: F821
    """FastAPI dependency for AuditLogRepository."""
    from app.core.dependency_injection import DatabaseService
    from app.core.repositories import AuditLogRepository

    db_service = DatabaseService(context)
    return AuditLogRepository(db_service)


# Health check dependency
async def get_database_health_checker(
    db_session: AsyncSession = Depends(get_database_session),
) -> DatabaseHealthChecker:
    """FastAPI dependency for DatabaseHealthChecker."""
    return DatabaseHealthChecker(lambda: db_session)


# Authentication and authorization dependencies
async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
) -> User:
    """Get current authenticated user from JWT token."""
    from app.security.jwt import get_current_user as jwt_get_current_user

    return await jwt_get_current_user(request=request, token=token)


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Service health and metrics
async def get_service_health_status() -> dict:
    """Get overall service health status."""
    registry = get_service_registry()
    if not registry.is_initialized:
        return {"status": "unhealthy", "reason": "Service registry not initialized"}

    try:
        health_status = await registry.get_database_service().check_health()
        return {
            "status": "healthy" if health_status else "unhealthy",
            "database": health_status,
            "services_initialized": True,
        }
    except Exception as e:
        return {"status": "unhealthy", "reason": str(e), "services_initialized": True}


# Background task helpers
class BackgroundTaskManager:
    """Manager for handling background tasks."""

    def __init__(self):
        self.tasks = []

    def add_task(self, func, *args, **kwargs):
        """Add a background task."""
        self.tasks.append((func, args, kwargs))

    async def execute_tasks(self):
        """Execute all pending background tasks."""
        for func, args, kwargs in self.tasks:
            try:
                if callable(func):
                    await func(*args, **kwargs)
            except Exception as e:
                # Log error but don't fail the request
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Background task failed: {e}")

        self.tasks.clear()


# Dependency for background task manager
def get_background_task_manager() -> BackgroundTaskManager:
    """FastAPI dependency for BackgroundTaskManager."""
    return BackgroundTaskManager()


# Utility functions for common dependencies
def require_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Require admin user for endpoint access."""
    if not current_user.is_superuser:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Require active user for endpoint access."""
    if not current_user.is_active:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="User account is inactive")
    return current_user


# Database transaction helpers
async def get_transaction_session(
    db_session: AsyncSession = Depends(get_database_session),
) -> AsyncSession:
    """Get database session with transaction management."""
    # This would implement transaction management
    # For now, just return the session
    return db_session


# Error handling dependencies
async def get_error_handler():
    """Get error handler for consistent error responses."""

    def handle_error(error: Exception, status_code: int = 500):
        from fastapi import HTTPException

        raise HTTPException(status_code=status_code, detail=str(error))

    return handle_error


# Performance monitoring dependencies
async def get_performance_monitor():
    """Get performance monitor for tracking endpoint performance."""

    class PerformanceMonitor:
        def __init__(self):
            self.metrics = {}

        def start_timer(self, endpoint: str):
            """Start timing an endpoint."""
            import time

            self.metrics[endpoint] = time.time()

        def end_timer(self, endpoint: str) -> float:
            """End timing and return duration."""
            import time

            if endpoint in self.metrics:
                start_time = self.metrics.pop(endpoint)
                return time.time() - start_time
            return 0.0

    return PerformanceMonitor()


# Export common dependencies for easy importing
__all__ = [
    "get_audit_log_repository",
    "get_authentication_service",
    "get_background_task_manager",
    "get_cache_service",
    "get_current_active_user",
    "get_current_user",
    "get_database_service",
    "get_database_session",
    "get_error_handler",
    "get_order_repository",
    "get_performance_monitor",
    "get_product_repository",
    "get_reporting_service",
    "get_service_context",
    "get_service_health_status",
    "get_transaction_session",
    "get_user_repository",
    "require_active_user",
    "require_admin_user",
]
