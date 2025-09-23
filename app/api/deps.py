"""Common FastAPI dependencies for the MagFlow API.

This module provides the dependencies that endpoint modules import via
``from app.api import deps``. It re‑exports the database session getter and the
authentication helpers defined elsewhere in the project.

The DI package ``dependency_injector`` is optional at runtime; when it is not
installed, we provide lightweight shims for ``Provide`` and ``inject`` so that
imports do not fail and the application can still start (with DI-based
dependencies acting as no-ops).
"""

from typing import Any, Callable

try:
    from dependency_injector.wiring import Provide, inject  # type: ignore
except Exception:  # pragma: no cover - optional dependency not available
    # Fallback shims: no-op decorator and a Provide placeholder
    def inject(func: Callable | None = None, **_: Any):  # type: ignore
        if func is None:

            def wrapper(f: Callable) -> Callable:
                return f

            return wrapper
        return func

    class _ProvideShim:
        def __getitem__(self, _key: Any) -> Any:
            return None

    Provide = _ProvideShim()

# Try to import the DI ApplicationContainer; if dependency_injector is missing,
# provide a minimal stub to keep imports working.
try:  # pragma: no cover - optional dependency path
    from app.core.container import ApplicationContainer  # type: ignore
except Exception:  # pragma: no cover

    class _StubContainer:
        class crud:
            user_crud = None

        class services:
            catalog_service = None

    ApplicationContainer = _StubContainer  # type: ignore
from app.core.database import get_async_session as get_db
from app.security.jwt import (
    get_current_active_superuser,
    get_current_active_user,
    get_current_user,
)

__all__ = [
    "get_db",
    "get_current_user",
    "get_current_active_user",
    "get_current_active_superuser",
    # New DI-based dependencies
    "get_user_crud",
    # "get_role_crud",  # Commented out due to Permission model removal
    # "get_permission_crud",  # Commented out due to Permission model removal
    "get_catalog_service",
    # Inventory CRUDs - commented out due to circular import issues
    # "get_warehouse_crud",
    # "get_inventory_item_crud",
    # "get_stock_movement_crud",
    # "get_stock_reservation_crud",
    # "get_stock_transfer_crud",
]


@inject
def get_user_crud(
    user_crud=Provide[ApplicationContainer.crud.user_crud],
) -> object:
    """Get user CRUD operations.

    Args:
        user_crud: Injected user CRUD instance

    Returns:
        User CRUD instance

    """
    return user_crud


# @inject  # Commented out due to Permission model removal
# def get_role_crud(
#     role_crud=Provide[ApplicationContainer.crud.role_crud],
# ) -> object:
#     """Get role CRUD operations.
#
#     Args:
#         role_crud: Injected role CRUD instance
#
#     Returns:
#         Role CRUD instance
#     """
#     return role_crud


# @inject  # Commented out due to Permission model removal
# def get_permission_crud(
#     permission_crud=Provide[ApplicationContainer.crud.permission_crud],
# ) -> object:
#     """Get permission CRUD operations.
#
#     Args:
#         permission_crud: Injected permission CRUD instance
#
#     Returns:
#         Permission CRUD instance
#     """
#     return permission_crud


@inject
def get_catalog_service(
    catalog_service=Provide[ApplicationContainer.services.catalog_service],
) -> object:
    """Get catalog service.

    Args:
        catalog_service: Injected catalog service instance

    Returns:
        Catalog service instance

    """
    return catalog_service


# Inventory CRUD dependencies - commented out due to circular import issues
# @inject
# def get_warehouse_crud(
#     warehouse_crud=Provide[ApplicationContainer.crud.warehouse_crud],
# ) -> object:
#     """Get warehouse CRUD operations.
#
#     Args:
#         warehouse_crud: Injected warehouse CRUD instance
#
#     Returns:
#         Warehouse CRUD instance
#     """
#     return warehouse_crud


# @inject
# def get_inventory_item_crud(
#     inventory_item_crud=Provide[ApplicationContainer.crud.inventory_item_crud],
# ) -> object:
#     """Get inventory item CRUD operations.
#
#     Args:
#         inventory_item_crud: Injected inventory item CRUD instance
#
#     Returns:
#         Inventory item CRUD instance
#     """
#     return inventory_item_crud


# @inject
# def get_stock_movement_crud(
#     stock_movement_crud=Provide[ApplicationContainer.crud.stock_movement_crud],
# ) -> object:
#     """Get stock movement CRUD operations.
#
#     Args:
#         stock_movement_crud: Injected stock movement CRUD instance
#
#     Returns:
#         Stock movement CRUD instance
#     """
#     return stock_movement_crud


# @inject
# def get_stock_reservation_crud(
#     stock_reservation_crud=Provide[ApplicationContainer.crud.stock_reservation_crud],
# ) -> object:
#     """Get stock reservation CRUD operations.
#
#     Args:
#         stock_reservation_crud: Injected stock reservation CRUD instance
#
#     Returns:
#         Stock reservation CRUD instance
#     """
#     return stock_reservation_crud


# @inject
# def get_stock_transfer_crud(
#     stock_transfer_crud=Provide[ApplicationContainer.crud.stock_transfer_crud],
# ) -> object:
#     """Get stock transfer CRUD operations.
#
#     Args:
#         stock_transfer_crud: Injected stock transfer CRUD instance
#
#     Returns:
#         Stock transfer CRUD instance
#     """
#     return stock_transfer_crud
