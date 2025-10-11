# Compatibility shim for legacy imports
# This module re-exports the public symbols from `dependencies.py` so that
# existing code (including tests) that does `from app.api import deps` continues to work.

from app.db import get_db  # noqa: F401

# Explicit imports instead of wildcard import for better code clarity
from .dependencies import (
    BackgroundTaskManager,
    get_audit_log_repository,
    get_authentication_service,
    get_background_task_manager,
    get_cache_service,
    get_current_active_user,
    get_current_user,
    get_database_health_checker,
    get_database_service,
    get_database_session,
    get_error_handler,
    get_order_repository,
    get_performance_monitor,
    get_product_repository,
    get_reporting_service,
    get_service_context,
    get_service_health_status,
    get_transaction_session,
    get_user_repository,
    require_active_user,
    require_admin_user,
)

__all__ = [
    "get_db",
    "BackgroundTaskManager",
    "get_audit_log_repository",
    "get_authentication_service",
    "get_background_task_manager",
    "get_cache_service",
    "get_current_active_user",
    "get_current_user",
    "get_database_health_checker",
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
