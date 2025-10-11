"""System-related API endpoints."""

# from .health import router as health_router  # Health router is in app.api.health
from .admin import router as admin_router
from .auth import users_router as auth_users_router
from .database import router as database_router
from .migration_management import router as migration_management_router
from .notifications import router as notifications_router
from .performance_metrics import router as performance_metrics_router
from .session_management import router as session_management_router
from .sms_notifications import router as sms_notifications_router

# from .mfa import router as mfa_router  # Corrupted file - needs to be recreated
from .test_auth import router as test_auth_router
from .websocket_notifications import router as websocket_notifications_router
from .websocket_sync import router as websocket_sync_router

__all__ = [
    # "health_router",  # Health router is in app.api.health
    "performance_metrics_router",
    "session_management_router",
    "migration_management_router",
    "notifications_router",
    "sms_notifications_router",
    "websocket_notifications_router",
    "websocket_sync_router",
    "database_router",
    "admin_router",
    "auth_users_router",
    # "mfa_router",  # Corrupted file - needs to be recreated
    "test_auth_router",
]
