"""RBAC Service - Re-export from security module."""

from app.services.security.rbac_service import (
    Permission,
    RBACService,
    Role,
    check_permission,
)

__all__ = [
    "RBACService",
    "Permission",
    "Role",
    "check_permission",
]
