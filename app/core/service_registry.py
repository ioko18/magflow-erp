"""Service Registry and Factory for MagFlow ERP.

This module provides a centralized service registry that manages service creation,
lifecycle, and dependency injection throughout the application.
"""

import inspect
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar

from app.core.dependency_injection import (
    AuthenticationService,
    CacheService,
    DatabaseService,
    ReportingService,
    ServiceBase,
    ServiceContext,
    get_container,
    initialize_container,
    register_services,
)
from app.core.repositories import (
    AuditLogRepository,
    OrderRepository,
    ProductRepository,
    RepositoryFactory,
    UserRepository,
)

_fallback_order_repository: Optional["_InMemoryOrderRepository"] = None

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceRegistry:
    """Central registry for managing all application services."""

    _instance: Optional["ServiceRegistry"] = None
    _initialized = False

    # Internal flag to ensure singleton construction logic only runs once
    _constructed = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._constructed:
            return

        # Lazily populated during `initialize()`
        self._services: Dict[str, ServiceBase] = {}
        self._repository_factory: Optional[RepositoryFactory] = None
        self._initialized = False
        self._constructed = True

    async def initialize(self, context: ServiceContext):
        """Initialize all services."""
        if self._initialized:
            logger.warning("Service registry already initialized")
            return

        try:
            # Create core services
            db_service = DatabaseService(context)
            cache_service = CacheService(context)
            auth_service = AuthenticationService(context)
            reporting_service = ReportingService(context)

            # Initialize services
            self._services = {
                "database": db_service,
                "cache": cache_service,
                "authentication": auth_service,
                "reporting": reporting_service,
            }

            # Create repository factory
            self._repository_factory = RepositoryFactory(db_service)

            # Initialize all services (await async initializers if needed)
            for name, service in self._services.items():
                initializer = service.initialize()
                if inspect.isawaitable(initializer):
                    await initializer

            logger.info(
                "Service registry initialized with %d services",
                len(self._services),
            )
            self._initialized = True

        except Exception as e:
            logger.error("Failed to initialize service registry: %s", e)
            raise

    async def cleanup(self):
        """Cleanup all services."""
        if not self._initialized:
            return

        try:
            for name, service in self._services.items():
                await service.cleanup()

            self._services.clear()
            self._repository_factory = None
            self._initialized = False

            logger.info("Service registry cleaned up")

        except Exception as e:
            logger.error("Error during service registry cleanup: %s", e)

    def get_service(self, service_name: str) -> ServiceBase:
        """Get service by name."""
        if not self._initialized:
            raise RuntimeError("Service registry not initialized")

        if service_name not in self._services:
            raise KeyError(f"Service '{service_name}' not found")

        return self._services[service_name]

    def get_database_service(self) -> DatabaseService:
        """Get database service."""
        return self.get_service("database")

    def get_cache_service(self) -> CacheService:
        """Get cache service."""
        return self.get_service("cache")

    def get_authentication_service(self) -> AuthenticationService:
        """Get authentication service."""
        return self.get_service("authentication")

    def get_reporting_service(self) -> ReportingService:
        """Get reporting service."""
        return self.get_service("reporting")

    def get_repository_factory(self) -> RepositoryFactory:
        """Get repository factory."""
        if not self._initialized:
            raise RuntimeError("Service registry not initialized")

        if not self._repository_factory:
            raise RuntimeError("Repository factory not available")

        return self._repository_factory

    def get_user_repository(self) -> UserRepository:
        """Get user repository."""
        return self.get_repository_factory().get_user_repository()

    def get_product_repository(self) -> ProductRepository:
        """Get product repository."""
        return self.get_repository_factory().get_product_repository()

    # def get_order_repository(self) -> OrderRepository:
    #     """Get order repository."""
    #     return self.get_repository_factory().get_order_repository()

    def get_audit_log_repository(self) -> AuditLogRepository:
        """Get audit log repository."""
        return self.get_repository_factory().get_audit_log_repository()

    @property
    def is_initialized(self) -> bool:
        """Check if registry is initialized."""
        return self._initialized


# Global service registry instance
_service_registry = ServiceRegistry()


def get_service_registry() -> ServiceRegistry:
    """Get the global service registry."""
    return _service_registry


async def initialize_service_registry(db_session=None):
    """Initialize the global service registry."""
    from app.core.config import get_settings

    settings = get_settings()

    # Initialize dependency container
    initialize_container(db_session)

    # Create service context
    context = ServiceContext(settings=settings, db_session=db_session)

    # Initialize service registry
    await _service_registry.initialize(context)

    # Register services with dependency container
    register_services()

    logger.info("Global service registry initialized")


async def cleanup_service_registry():
    """Cleanup the global service registry."""
    await _service_registry.cleanup()

    # Reset dependency container
    get_container().reset()

    logger.info("Global service registry cleaned up")


# FastAPI dependency providers
def get_database_service() -> DatabaseService:
    """FastAPI dependency provider for DatabaseService."""
    return _service_registry.get_database_service()


def get_cache_service() -> CacheService:
    """FastAPI dependency provider for CacheService."""
    return _service_registry.get_cache_service()


def get_authentication_service() -> AuthenticationService:
    """FastAPI dependency provider for AuthenticationService."""
    return _service_registry.get_authentication_service()


def get_reporting_service() -> ReportingService:
    """FastAPI dependency provider for ReportingService."""
    return _service_registry.get_reporting_service()


def get_user_repository() -> UserRepository:
    """FastAPI dependency provider for UserRepository."""
    return _service_registry.get_user_repository()


def get_product_repository() -> ProductRepository:
    """FastAPI dependency provider for ProductRepository."""
    return _service_registry.get_product_repository()


def get_order_repository() -> OrderRepository:
    """FastAPI dependency provider for OrderRepository.

    Returns a real repository when the service registry has been initialized.
    Falls back to a lightweight in-memory implementation for contexts (like
    unit tests) where the full infrastructure is not available.
    """

    global _fallback_order_repository  # pylint: disable=global-statement

    if _service_registry.is_initialized:
        try:
            return _service_registry.get_repository_factory().get_order_repository()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to retrieve OrderRepository from registry: %s", exc)

    if _fallback_order_repository is None:
        _fallback_order_repository = _InMemoryOrderRepository()

    return _fallback_order_repository


class _InMemoryOrderRepository:  # pragma: no cover - simple fallback
    """Minimal in-memory OrderRepository used for tests without a DB."""

    def __init__(self):
        self._orders: Dict[str, Any] = {}

    async def get_session(self):  # mimic async interface of real repositories
        raise RuntimeError("In-memory repository has no database session")

    async def get_by_id(self, order_id: Any):
        return self._orders.get(order_id)

    async def get_all(self, skip: int = 0, limit: int = 100):
        orders = list(self._orders.values())
        return orders[skip : skip + limit]

    async def get_by_customer_id(
        self, customer_id: Any, skip: int = 0, limit: int = 100
    ):
        filtered = [
            o for o in self._orders.values() if o.get("customer_id") == customer_id
        ]
        return filtered[skip : skip + limit]

    async def get_by_status(self, status: str, skip: int = 0, limit: int = 100):
        filtered = [o for o in self._orders.values() if o.get("status") == status]
        return filtered[skip : skip + limit]

    async def create(self, data: Dict[str, Any]):
        order_id = data.get("id")
        if order_id is None:
            order_id = str(len(self._orders) + 1)
        stored = {"id": order_id, **data}
        self._orders[order_id] = stored
        return stored

    async def update(self, order_id: Any, data: Dict[str, Any]):
        if order_id not in self._orders:
            return None
        self._orders[order_id].update(data)
        return self._orders[order_id]

    async def delete(self, order_id: Any):
        return self._orders.pop(order_id, None) is not None


def get_security_service():
    """Stub function for SecurityService - not implemented yet."""

    # Create a simple mock service class
    class MockSecurityService:
        def __init__(self):
            pass

        async def get_audit_log(self, *args, **kwargs):
            return {"events": [], "total": 0}

    return MockSecurityService()


def get_audit_log_repository() -> AuditLogRepository:
    """FastAPI dependency provider for AuditLogRepository."""
    return _service_registry.get_audit_log_repository()


# Service health check utilities
async def check_service_health() -> Dict[str, Any]:
    """Check health of all services."""
    if not _service_registry.is_initialized:
        return {"status": "error", "message": "Service registry not initialized"}

    health_status = {"status": "healthy", "services": {}}

    try:
        # Check database service
        db_service = _service_registry.get_database_service()
        health_status["services"]["database"] = await db_service.check_health()

        # Check other services
        health_status["services"]["cache"] = "initialized"
        health_status["services"]["authentication"] = "initialized"
        health_status["services"]["reporting"] = "initialized"

    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)
        logger.error("Service health check failed: %s", e)

    return health_status


# Service metrics collection
def collect_service_metrics() -> Dict[str, Any]:
    """Collect metrics from all services."""
    if not _service_registry.is_initialized:
        return {"error": "Service registry not initialized"}

    metrics = {"timestamp": datetime.utcnow().isoformat(), "services": {}}

    # Collect metrics from each service
    for service_name, service in _service_registry._services.items():
        metrics["services"][service_name] = {
            "class": service.__class__.__name__,
            "initialized": True,
        }

    return metrics


# Service lifecycle management
class ServiceLifecycleManager:
    """Manager for handling service lifecycle events."""

    def __init__(self):
        self._listeners: Dict[str, List[callable]] = {
            "before_startup": [],
            "after_startup": [],
            "before_shutdown": [],
            "after_shutdown": [],
        }

    def add_listener(self, event: str, listener: callable):
        """Add listener for service lifecycle event."""
        if event not in self._listeners:
            raise ValueError(f"Unknown lifecycle event: {event}")

        self._listeners[event].append(listener)
        logger.debug("Added %s listener: %s", event, listener.__name__)

    async def trigger_event(self, event: str, *args, **kwargs):
        """Trigger lifecycle event."""
        if event not in self._listeners:
            return

        for listener in self._listeners[event]:
            try:
                if inspect.iscoroutinefunction(listener):
                    await listener(*args, **kwargs)
                else:
                    listener(*args, **kwargs)
            except Exception as e:
                logger.error("Error in %s listener %s: %s", event, listener.__name__, e)


# Global lifecycle manager
_lifecycle_manager = ServiceLifecycleManager()


def get_lifecycle_manager() -> ServiceLifecycleManager:
    """Get the global lifecycle manager."""
    return _lifecycle_manager
