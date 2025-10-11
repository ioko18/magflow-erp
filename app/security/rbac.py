"""Enhanced Role-Based Access Control (RBAC) system."""

import functools
from collections.abc import Callable
from enum import Enum
from typing import Any

from fastapi import HTTPException, status

from ..schemas.user import UserInDB


class Permission(str, Enum):
    """Predefined permissions for the system."""

    # User management
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    # Role management
    ROLE_READ = "role:read"
    ROLE_CREATE = "role:create"
    ROLE_UPDATE = "role:update"
    ROLE_DELETE = "role:delete"

    # Product management
    PRODUCT_READ = "product:read"
    PRODUCT_CREATE = "product:create"
    PRODUCT_UPDATE = "product:update"
    PRODUCT_DELETE = "product:delete"

    # Catalog management
    CATALOG_READ = "catalog:read"
    CATALOG_UPDATE = "catalog:update"
    CATALOG_MANAGE = "catalog:manage"

    # eMAG integration
    EMAG_READ = "emag:read"
    EMAG_SYNC = "emag:sync"
    EMAG_MANAGE = "emag:manage"

    # System administration
    SYSTEM_READ = "system:read"
    SYSTEM_UPDATE = "system:update"
    SYSTEM_MANAGE = "system:manage"

    # Audit and monitoring
    AUDIT_READ = "audit:read"
    AUDIT_CREATE = "audit:create"


class Resource(str, Enum):
    """Resources that can be protected by permissions."""

    USER = "user"
    ROLE = "role"
    PRODUCT = "product"
    CATEGORY = "category"
    BRAND = "brand"
    ORDER = "order"
    INVENTORY = "inventory"
    REPORT = "report"
    SYSTEM = "system"
    AUDIT = "audit"


def has_permission(user: UserInDB, permission: str) -> bool:
    """Check if a user has a specific permission."""
    if user.is_superuser:
        return True

    # Check if any of the user's roles have the required permission
    for role in user.roles:
        if not role.is_active:
            continue

        for perm in role.permissions:
            if perm.name == permission:
                return True

    return False


def has_any_permission(user: UserInDB, permissions: list[str]) -> bool:
    """Check if a user has any of the specified permissions."""
    return any(has_permission(user, perm) for perm in permissions)


def has_all_permissions(user: UserInDB, permissions: list[str]) -> bool:
    """Check if a user has all of the specified permissions."""
    return all(has_permission(user, perm) for perm in permissions)


def require_permission(permission: str | list[str]):
    """Decorator to require specific permission(s) for an endpoint."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Get current user from kwargs
            current_user = None
            for arg in args:
                if isinstance(arg, UserInDB):
                    current_user = arg
                    break

            if not current_user:
                # Try to get from kwargs
                current_user = kwargs.get("current_user")

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            # Check permissions
            if isinstance(permission, str):
                if not has_permission(current_user, permission):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission '{permission}' required",
                    )
            elif not has_any_permission(current_user, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"One of the following permissions required: {permission}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_all_permissions(permissions: list[str]):
    """Decorator to require all specified permissions."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Get current user
            current_user = None
            for arg in args:
                if isinstance(arg, UserInDB):
                    current_user = arg
                    break

            if not current_user:
                current_user = kwargs.get("current_user")

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            if not has_all_permissions(current_user, permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"All of the following permissions required: {permissions}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


async def get_user_permissions(user: UserInDB) -> list[str]:
    """Get all permissions for a user."""
    if user.is_superuser:
        # Superusers have all permissions
        return [perm.value for perm in Permission]

    permissions = set()
    for role in user.roles:
        if not role.is_active:
            continue

        for perm in role.permissions:
            permissions.add(perm.name)

    return list(permissions)


async def get_user_roles(user: UserInDB) -> list[str]:
    """Get all role names for a user."""
    return [role.name for role in user.roles if role.is_active]


class RBACMiddleware:
    """Middleware for Role-Based Access Control."""

    def __init__(self, app, exclude_paths: list[str] = None):
        self.app = app
        self.exclude_paths = exclude_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/me",
        ]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Check if path should be excluded from RBAC
        path = scope["path"]
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            await self.app(scope, receive, send)
            return

        # For now, just pass through - RBAC is handled at endpoint level
        # In a more advanced implementation, you could do RBAC at middleware level
        await self.app(scope, receive, send)


# Default roles and permissions
DEFAULT_ROLES = {
    "admin": {
        "description": "System administrator with full access",
        "permissions": [perm.value for perm in Permission],
        "is_active": True,
    },
    "manager": {
        "description": "Manager with access to most features",
        "permissions": [
            Permission.USER_READ,
            Permission.USER_CREATE,
            Permission.USER_UPDATE,
            Permission.ROLE_READ,
            Permission.PRODUCT_READ,
            Permission.PRODUCT_CREATE,
            Permission.PRODUCT_UPDATE,
            Permission.PRODUCT_DELETE,
            Permission.CATALOG_READ,
            Permission.CATALOG_UPDATE,
            Permission.CATALOG_MANAGE,
            Permission.EMAG_READ,
            Permission.EMAG_SYNC,
            Permission.REPORT_READ,
            Permission.SYSTEM_READ,
        ],
        "is_active": True,
    },
    "user": {
        "description": "Regular user with basic access",
        "permissions": [
            Permission.PRODUCT_READ,
            Permission.CATALOG_READ,
            Permission.EMAG_READ,
        ],
        "is_active": True,
    },
    "viewer": {
        "description": "Read-only user",
        "permissions": [
            Permission.PRODUCT_READ,
            Permission.CATALOG_READ,
        ],
        "is_active": True,
    },
}
