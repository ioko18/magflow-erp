"""Comprehensive audit logging system."""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from fastapi import Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings


class AuditEventType(str, Enum):
    """Types of audit events."""

    # Authentication events
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    LOGIN_FAILED = "auth.login_failed"
    TOKEN_REFRESH = "auth.token_refresh"

    # User management
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_ROLE_CHANGED = "user.role_changed"

    # Permission events
    PERMISSION_GRANTED = "permission.granted"
    PERMISSION_REVOKED = "permission.revoked"
    ROLE_CREATED = "role.created"
    ROLE_UPDATED = "role.updated"
    ROLE_DELETED = "role.deleted"

    # Data access
    DATA_ACCESSED = "data.accessed"
    DATA_CREATED = "data.created"
    DATA_UPDATED = "data.updated"
    DATA_DELETED = "data.deleted"

    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    CONFIGURATION_CHANGED = "system.config_changed"

    # Security events
    SUSPICIOUS_ACTIVITY = "security.suspicious"
    SECURITY_VIOLATION = "security.violation"
    RATE_LIMIT_EXCEEDED = "security.rate_limit_exceeded"

    # Business events
    BUSINESS_OPERATION = "business.operation"
    INTEGRATION_EVENT = "integration.event"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""

    LOW = "low"  # Normal operations
    MEDIUM = "medium"  # Important operations
    HIGH = "high"  # Sensitive operations
    CRITICAL = "critical"  # Security/critical operations


class AuditEvent(BaseModel):
    """Audit event model."""

    id: str
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: str | None = None
    username: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    resource: str | None = None  # e.g., "user:123", "product:456"
    action: str | None = None  # e.g., "create", "update", "delete", "read"
    details: dict[str, Any] = {}
    before_state: dict[str, Any] | None = None
    after_state: dict[str, Any] | None = None
    correlation_id: str | None = None
    session_id: str | None = None
    timestamp: datetime
    success: bool = True
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert audit event to dictionary for storage."""
        return {
            "id": self.id,
            "event_type": self.event_type,
            "severity": self.severity,
            "user_id": self.user_id,
            "username": self.username,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "resource": self.resource,
            "action": self.action,
            "details": self.details,
            "before_state": self.before_state,
            "after_state": self.after_state,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "error_message": self.error_message,
        }


class AuditLogger:
    """Service for logging audit events."""

    def __init__(self):
        self.logger = logging.getLogger("audit")
        self._handlers: list[AuditHandler] = []
        self._setup_logger()

    def _setup_logger(self):
        """Setup audit logger with appropriate configuration."""
        if not self.logger.handlers:
            # Use a default log file if settings are not available
            log_file = getattr(settings, "AUDIT_LOG_FILE", "logs/audit.log")
            # Create file handler for audit logs
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)

            # Create formatter for audit logs
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
            file_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)
            self.logger.setLevel(logging.INFO)

    def add_handler(self, handler: "AuditHandler"):
        """Add an audit handler."""
        self._handlers.append(handler)

    def remove_handler(self, handler: "AuditHandler"):
        """Remove an audit handler."""
        if handler in self._handlers:
            self._handlers.remove(handler)

    async def log_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        user_id: str | None = None,
        username: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        resource: str | None = None,
        action: str | None = None,
        details: dict[str, Any] | None = None,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        session_id: str | None = None,
        success: bool = True,
        error_message: str | None = None,
    ):
        """Log an audit event."""
        event = AuditEvent(
            id=str(uuid4()),
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            resource=resource,
            action=action,
            details=details or {},
            before_state=before_state,
            after_state=after_state,
            correlation_id=correlation_id,
            session_id=session_id,
            timestamp=datetime.now(),
            success=success,
            error_message=error_message,
        )

        # Log to standard logger
        log_data = {
            "event_id": event.id,
            "event_type": event.event_type,
            "severity": event.severity,
            "user_id": event.user_id,
            "username": event.username,
            "resource": event.resource,
            "action": event.action,
            "success": event.success,
        }

        if event.details:
            log_data["details"] = json.dumps(event.details, default=str)

        if event.error_message:
            log_data["error"] = event.error_message

        self.logger.info(json.dumps(log_data, default=str), extra=log_data)

        # Notify handlers
        for handler in self._handlers:
            try:
                await handler.handle_event(event)
            except Exception as e:
                self.logger.error(
                    f"Error in audit handler {handler.__class__.__name__}: {e}",
                )


class AuditHandler:
    """Base class for audit event handlers."""

    async def handle_event(self, event: AuditEvent):
        """Handle an audit event. Override in subclasses."""


class DatabaseAuditHandler(AuditHandler):
    """Audit handler that stores events in database."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def handle_event(self, event: AuditEvent):
        """Store audit event in database."""
        # In a real implementation, you'd have an AuditLog model
        # and store the event there
        # For now, just log that we would store it


class SecurityAuditHandler(AuditHandler):
    """Audit handler for security events."""

    async def handle_event(self, event: AuditEvent):
        """Handle security-related audit events."""
        if event.severity in [AuditSeverity.HIGH, AuditSeverity.CRITICAL]:
            # In a real implementation, you might:
            # - Send alerts to security team
            # - Trigger security monitoring
            # - Block suspicious IPs
            # - Escalate to incident response
            pass


# Global audit logger instance
audit_logger = AuditLogger()


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    return audit_logger


async def audit_log(
    event_type: AuditEventType,
    severity: AuditSeverity,
    user_id: str | None = None,
    username: str | None = None,
    request: Request | None = None,
    **kwargs,
):
    """Convenience function for logging audit events."""
    ip_address = None
    user_agent = None
    correlation_id = None

    if request:
        client = getattr(request.client, "host", None) if request.client else None
        ip_address = client or "unknown"
        user_agent = request.headers.get("user-agent", "")
        correlation_id = getattr(request.state, "correlation_id", None)

    await audit_logger.log_event(
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        username=username,
        ip_address=ip_address,
        user_agent=user_agent,
        correlation_id=correlation_id,
        **kwargs,
    )


# Convenience functions for common audit events
async def audit_login(username: str, success: bool, request: Request):
    """Log a login attempt."""
    event_type = AuditEventType.LOGIN if success else AuditEventType.LOGIN_FAILED
    severity = AuditSeverity.LOW if success else AuditSeverity.MEDIUM

    await audit_log(
        event_type=event_type,
        severity=severity,
        username=username,
        request=request,
        success=success,
    )


async def audit_user_action(
    action: str,
    resource: str,
    user_id: str,
    username: str,
    before_state: dict | None = None,
    after_state: dict | None = None,
    request: Request | None = None,
    success: bool = True,
):
    """Log a user action on a resource."""
    severity = AuditSeverity.MEDIUM
    if action in ["delete", "update"]:
        severity = AuditSeverity.HIGH

    await audit_log(
        event_type=AuditEventType.BUSINESS_OPERATION,
        severity=severity,
        user_id=user_id,
        username=username,
        resource=resource,
        action=action,
        before_state=before_state,
        after_state=after_state,
        request=request,
        success=success,
    )


async def audit_security_event(
    event_type: AuditEventType,
    severity: AuditSeverity,
    details: dict[str, Any],
    request: Request,
):
    """Log a security event."""
    await audit_log(
        event_type=event_type,
        severity=severity,
        request=request,
        details=details,
    )
