"""Dependency injection container for the application."""

from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.crud import (
    CRUDUser,
    # CRUDRole,  # Commented out due to Permission model removal
    # CRUDPermission,  # Commented out due to Permission model removal
    # Commented out inventory CRUDs due to circular import issues
    # CRUDWarehouse, CRUDInventoryItem, CRUDStockMovement, CRUDStockReservation, CRUDStockTransfer
)
from app.services.background_service import BackgroundTaskService
from app.services.catalog_service import CatalogService


class DatabaseContainer(containers.DeclarativeContainer):
    """Database dependency injection container."""

    # Database engine
    engine = providers.Singleton(
        create_async_engine,
        settings.DB_URI,
        settings.DB_ECHO,
        future=True,
    )

    # Session factory
    session_factory = providers.Singleton(
        sessionmaker,
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Database session (scoped to request)
    db_session = providers.Factory(
        session_factory,
    )


class CRUDContainer(containers.DeclarativeContainer):
    """CRUD operations dependency injection container."""

    db = providers.DependenciesContainer()

    # User CRUD operations
    user_crud = providers.Singleton(
        CRUDUser,
        db=db.db_session,
    )

    # Role CRUD operations
    # role_crud = providers.Singleton(  # Commented out due to Permission model removal
    #     CRUDRole,
    #     db=db.db_session,
    # )

    # Permission CRUD operations
    # permission_crud = providers.Singleton(  # Commented out due to Permission model removal
    #     CRUDPermission,
    #     db=db.db_session,
    # )

    # Inventory CRUD operations - commented out due to circular import issues
    # warehouse_crud = providers.Singleton(
    #     CRUDWarehouse,
    #     db=db.db_session,
    # )

    # inventory_item_crud = providers.Singleton(
    #     CRUDInventoryItem,
    #     db=db.db_session,
    # )

    # stock_movement_crud = providers.Singleton(
    #     CRUDStockMovement,
    #     db=db.db_session,
    # )

    # stock_reservation_crud = providers.Singleton(
    #     CRUDStockReservation,
    #     db=db.db_session,
    # )

    # stock_transfer_crud = providers.Singleton(
    #     CRUDStockTransfer,
    #     db=db.db_session,
    # )


class ServiceContainer(containers.DeclarativeContainer):
    """Business services dependency injection container."""

    db = providers.DependenciesContainer()
    crud = providers.DependenciesContainer()

    # Catalog service
    catalog_service = providers.Singleton(
        CatalogService,
        db=db.db_session,
    )

    # Background task service
    background_service = providers.Singleton(
        BackgroundTaskService,
        max_concurrent_tasks=5,
    )


class ApplicationContainer(containers.DeclarativeContainer):
    """Main application dependency injection container."""

    # Sub-containers
    db = providers.Container(DatabaseContainer)
    crud = providers.Container(CRUDContainer, db=db)
    services = providers.Container(ServiceContainer, db=db, crud=crud)


# Global container instance
container = ApplicationContainer()
container.wire(
    modules=[
        "app.api.deps",
        "app.api.v1.endpoints.auth",
        "app.api.v1.endpoints.emag",
        "app.api.v1.endpoints.health",
        # "app.routers.auth",
        # "app.routers.categories",
        # "app.routers.products",
        "app.services.catalog_service",
        "app.services.background_service",
        # Inventory modules
        # "app.api.v1.endpoints.inventory",
        # "app.routers.inventory",
        # Sales modules
        # "app.api.v1.endpoints.sales",
        # "app.routers.sales",
        # Purchase modules
        # "app.api.v1.endpoints.purchase",
        # "app.routers.purchase",
    ],
)
