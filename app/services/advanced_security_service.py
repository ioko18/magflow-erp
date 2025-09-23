"""Advanced Security Service for MagFlow ERP.

This module provides enterprise-grade security features including
advanced JWT authentication, comprehensive audit trails, and
multi-layered security controls.
"""

import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.dependency_injection import ServiceBase, ServiceContext

logger = logging.getLogger(__name__)


class SecurityEventType(str, Enum):
    """Types of security events for audit logging."""

    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    PASSWORD_CHANGE = "password_change"
    PERMISSION_DENIED = "permission_denied"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SYNC_OPERATION = "sync_operation"
    DATA_EXPORT = "data_export"
    ADMIN_ACTION = "admin_action"
    API_CALL = "api_call"


class SecurityLevel(str, Enum):
    """Security levels for different operations."""

    LOW = "low"  # Basic operations
    MEDIUM = "medium"  # Sensitive operations
    HIGH = "high"  # Critical operations
    CRITICAL = "critical"  # Administrative operations


@dataclass
class SecurityConfig:
    """Advanced security configuration."""

    # JWT Configuration
    jwt_secret_key: str = field(default_factory=lambda: secrets.token_hex(64))
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    jwt_rotation_enabled: bool = True
    max_concurrent_sessions: int = 3

    # Session Management
    session_timeout_minutes: int = 60
    extended_session_timeout_minutes: int = 480  # 8 hours
    max_session_per_user: int = 5

    # Rate Limiting
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    brute_force_window_minutes: int = 15

    # Audit Logging
    audit_log_enabled: bool = True
    audit_log_retention_days: int = 90
    sensitive_data_masking: bool = True

    # IP Security
    ip_whitelist_enabled: bool = False
    ip_whitelist: List[str] = field(default_factory=list)
    ip_blacklist_enabled: bool = False
    ip_blacklist: List[str] = field(default_factory=list)

    # Advanced Features
    mfa_enabled: bool = False
    password_complexity_enabled: bool = True
    suspicious_activity_detection: bool = True
    real_time_threat_detection: bool = True


@dataclass
class AuditEvent:
    """Audit event for security logging."""

    event_id: str
    event_type: SecurityEventType
    user_id: Optional[str]
    resource: str
    action: str
    security_level: SecurityLevel
    timestamp: datetime
    ip_address: str
    user_agent: str
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)
    risk_score: int = 0  # 0-100
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SecurityAlert:
    """Security alert for threat detection."""

    alert_id: str
    alert_type: str
    severity: str  # low, medium, high, critical
    title: str
    description: str
    affected_users: List[str]
    timestamp: datetime
    resolved: bool = False
    resolution_notes: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


class AdvancedSecurityService(ServiceBase):
    """Advanced security service with enterprise features."""

    def __init__(self, context: ServiceContext):
        super().__init__(context)
        self.security_config = SecurityConfig()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.failed_login_attempts: Dict[str, List[datetime]] = {}
        self.audit_events: List[AuditEvent] = []
        self.security_alerts: List[SecurityAlert] = []
        self._load_security_config()

    def _load_security_config(self):
        """Load security configuration from settings."""
        settings = self.context.settings

        # JWT Configuration
        if hasattr(settings, "jwt_secret_key"):
            self.security_config.jwt_secret_key = settings.jwt_secret_key
        if hasattr(settings, "jwt_algorithm"):
            self.security_config.jwt_algorithm = settings.jwt_algorithm
        if hasattr(settings, "access_token_expire_minutes"):
            self.security_config.access_token_expire_minutes = (
                settings.access_token_expire_minutes
            )

        # Session Configuration
        if hasattr(settings, "max_concurrent_sessions"):
            self.security_config.max_concurrent_sessions = (
                settings.max_concurrent_sessions
            )
        if hasattr(settings, "session_timeout_minutes"):
            self.security_config.session_timeout_minutes = (
                settings.session_timeout_minutes
            )

        # Security Features
        if hasattr(settings, "mfa_enabled"):
            self.security_config.mfa_enabled = settings.mfa_enabled
        if hasattr(settings, "audit_log_enabled"):
            self.security_config.audit_log_enabled = settings.audit_log_enabled

        logger.info("Advanced Security Service configured")

    async def log_audit_event(
        self,
        event_type: SecurityEventType,
        user_id: Optional[str],
        resource: str,
        action: str,
        security_level: SecurityLevel,
        success: bool,
        ip_address: str = "unknown",
        user_agent: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
        risk_score: int = 0,
    ) -> str:
        """Log security audit event."""
        try:
            event_id = secrets.token_hex(16)

            audit_event = AuditEvent(
                event_id=event_id,
                event_type=event_type,
                user_id=user_id,
                resource=resource,
                action=action,
                security_level=security_level,
                timestamp=datetime.utcnow(),
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                metadata=metadata or {},
                risk_score=risk_score,
            )

            self.audit_events.append(audit_event)

            # Keep only recent events (last 30 days)
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            self.audit_events = [
                event for event in self.audit_events if event.timestamp > cutoff_date
            ]

            # Detect suspicious patterns
            await self._analyze_audit_event(audit_event)

            # Log based on security level
            if security_level in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
                logger.warning(
                    f"High security event: {event_type} - {resource} - {action}",
                )
            elif security_level == SecurityLevel.MEDIUM or not success:
                logger.info(f"Security event: {event_type} - {resource} - {action}")
            else:
                logger.debug(f"Security event: {event_type} - {resource}")

            return event_id

        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            return ""

    async def _analyze_audit_event(self, event: AuditEvent):
        """Analyze audit event for suspicious patterns."""
        if not self.security_config.suspicious_activity_detection:
            return

        try:
            # Check for multiple failed login attempts
            if event.event_type == SecurityEventType.LOGIN_FAILED:
                await self._check_failed_login_pattern(event)

            # Check for unusual access patterns
            if event.event_type == SecurityEventType.API_CALL:
                await self._check_unusual_api_access(event)

            # Check for high-risk operations
            if event.security_level in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
                await self._check_high_risk_operations(event)

        except Exception as e:
            logger.error(f"Failed to analyze audit event: {e}")

    async def _check_failed_login_pattern(self, event: AuditEvent):
        """Check for brute force login attempts."""
        try:
            if event.user_id not in self.failed_login_attempts:
                self.failed_login_attempts[event.user_id] = []

            self.failed_login_attempts[event.user_id].append(event.timestamp)

            # Keep only recent attempts (last 15 minutes)
            cutoff_time = datetime.utcnow() - timedelta(
                minutes=self.security_config.brute_force_window_minutes,
            )
            self.failed_login_attempts[event.user_id] = [
                attempt
                for attempt in self.failed_login_attempts[event.user_id]
                if attempt > cutoff_time
            ]

            # Check if threshold exceeded
            recent_failures = len(self.failed_login_attempts[event.user_id])

            if recent_failures >= self.security_config.max_login_attempts:
                await self._create_security_alert(
                    alert_type="brute_force_attack",
                    severity="high",
                    title="Multiple Failed Login Attempts",
                    description=f"User {event.user_id} has {recent_failures} failed login attempts in {self.security_config.brute_force_window_minutes} minutes",
                    affected_users=[event.user_id],
                )

        except Exception as e:
            logger.error(f"Failed to check failed login pattern: {e}")

    async def _check_unusual_api_access(self, event: AuditEvent):
        """Check for unusual API access patterns."""
        try:
            # This is a simplified implementation
            # In production, would use ML models to detect anomalies

            suspicious_patterns = [
                "/admin",  # Admin endpoints
                "/export",  # Data export
                "/sync/all",  # Bulk operations
                "/delete",  # Delete operations
            ]

            if any(pattern in event.resource for pattern in suspicious_patterns):
                await self._create_security_alert(
                    alert_type="unusual_api_access",
                    severity="medium",
                    title="Unusual API Access Detected",
                    description=f"Suspicious API access to {event.resource}",
                    affected_users=[event.user_id] if event.user_id else [],
                )

        except Exception as e:
            logger.error(f"Failed to check unusual API access: {e}")

    async def _check_high_risk_operations(self, event: AuditEvent):
        """Check for high-risk operations."""
        try:
            high_risk_operations = [
                "bulk_delete",
                "system_config_change",
                "user_permission_change",
                "data_export",
            ]

            if any(op in event.action for op in high_risk_operations):
                await self._create_security_alert(
                    alert_type="high_risk_operation",
                    severity="high",
                    title="High-Risk Operation Performed",
                    description=f"User performed high-risk operation: {event.action}",
                    affected_users=[event.user_id] if event.user_id else [],
                )

        except Exception as e:
            logger.error(f"Failed to check high-risk operations: {e}")

    async def _create_security_alert(
        self,
        alert_type: str,
        severity: str,
        title: str,
        description: str,
        affected_users: List[str],
    ) -> str:
        """Create security alert."""
        try:
            alert_id = secrets.token_hex(16)

            security_alert = SecurityAlert(
                alert_id=alert_id,
                alert_type=alert_type,
                severity=severity,
                title=title,
                description=description,
                affected_users=affected_users,
                timestamp=datetime.utcnow(),
            )

            self.security_alerts.append(security_alert)

            logger.warning(
                f"Security Alert [{severity.upper()}]: {title} - {description}",
            )

            return alert_id

        except Exception as e:
            logger.error(f"Failed to create security alert: {e}")
            return ""

    async def validate_user_session(
        self,
        user_id: str,
        session_token: str,
        ip_address: str = "unknown",
    ) -> Dict[str, Any]:
        """Validate user session with security checks."""
        try:
            # Check if user has active sessions
            user_sessions = [
                session
                for session in self.active_sessions.values()
                if session.get("user_id") == user_id
            ]

            if not user_sessions:
                await self.log_audit_event(
                    SecurityEventType.PERMISSION_DENIED,
                    user_id,
                    "session_validation",
                    "no_active_session",
                    SecurityLevel.MEDIUM,
                    False,
                    ip_address,
                    metadata={"reason": "no_active_session"},
                )
                return {"valid": False, "reason": "no_active_session"}

            # Check session limits
            if len(user_sessions) >= self.security_config.max_concurrent_sessions:
                await self.log_audit_event(
                    SecurityEventType.PERMISSION_DENIED,
                    user_id,
                    "session_validation",
                    "too_many_sessions",
                    SecurityLevel.MEDIUM,
                    False,
                    ip_address,
                    metadata={"active_sessions": len(user_sessions)},
                )
                return {"valid": False, "reason": "too_many_sessions"}

            # Check IP restrictions
            if self.security_config.ip_whitelist_enabled:
                if ip_address not in self.security_config.ip_whitelist:
                    await self.log_audit_event(
                        SecurityEventType.PERMISSION_DENIED,
                        user_id,
                        "session_validation",
                        "ip_not_whitelisted",
                        SecurityLevel.HIGH,
                        False,
                        ip_address,
                        metadata={"whitelisted_ips": self.security_config.ip_whitelist},
                    )
                    return {"valid": False, "reason": "ip_not_whitelisted"}

            # Check IP blacklist
            if self.security_config.ip_blacklist_enabled:
                if ip_address in self.security_config.ip_blacklist:
                    await self.log_audit_event(
                        SecurityEventType.PERMISSION_DENIED,
                        user_id,
                        "session_validation",
                        "ip_blacklisted",
                        SecurityLevel.HIGH,
                        False,
                        ip_address,
                        metadata={"reason": "IP is blacklisted"},
                    )
                    return {"valid": False, "reason": "ip_blacklisted"}

            await self.log_audit_event(
                SecurityEventType.API_CALL,
                user_id,
                "session_validation",
                "session_validated",
                SecurityLevel.LOW,
                True,
                ip_address,
            )

            return {"valid": True, "sessions": user_sessions}

        except Exception as e:
            logger.error(f"Failed to validate user session: {e}")
            return {"valid": False, "reason": "validation_error"}

    async def get_security_dashboard(self, hours: int = 24) -> Dict[str, Any]:
        """Get security dashboard data."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            # Filter events by time
            recent_events = [
                event for event in self.audit_events if event.timestamp > cutoff_time
            ]

            # Calculate metrics
            total_events = len(recent_events)
            failed_events = [e for e in recent_events if not e.success]
            high_risk_events = [
                e
                for e in recent_events
                if e.security_level in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]
            ]

            # Event type breakdown
            event_types = {}
            for event in recent_events:
                event_type = event.event_type
                event_types[event_type] = event_types.get(event_type, 0) + 1

            # Security levels breakdown
            security_levels = {}
            for event in recent_events:
                level = event.security_level
                security_levels[level] = security_levels.get(level, 0) + 1

            # Risk analysis
            risk_scores = [e.risk_score for e in recent_events if e.risk_score > 0]
            avg_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0

            # Active alerts
            active_alerts = [
                alert for alert in self.security_alerts if not alert.resolved
            ]

            return {
                "period_hours": hours,
                "summary": {
                    "total_events": total_events,
                    "failed_events": len(failed_events),
                    "high_risk_events": len(high_risk_events),
                    "average_risk_score": avg_risk_score,
                    "active_alerts": len(active_alerts),
                },
                "event_breakdown": event_types,
                "security_levels": security_levels,
                "recent_events": [
                    {
                        "event_id": e.event_id,
                        "event_type": e.event_type,
                        "user_id": e.user_id,
                        "resource": e.resource,
                        "action": e.action,
                        "security_level": e.security_level,
                        "timestamp": e.timestamp.isoformat(),
                        "success": e.success,
                        "risk_score": e.risk_score,
                    }
                    for e in recent_events[-50:]  # Last 50 events
                ],
                "active_alerts": [
                    {
                        "alert_id": a.alert_id,
                        "alert_type": a.alert_type,
                        "severity": a.severity,
                        "title": a.title,
                        "description": a.description,
                        "affected_users": a.affected_users,
                        "timestamp": a.timestamp.isoformat(),
                    }
                    for a in active_alerts
                ],
                "generated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get security dashboard: {e}")
            raise

    async def cleanup_expired_sessions(self):
        """Clean up expired sessions and old audit events."""
        try:
            current_time = datetime.utcnow()

            # Clean up expired sessions
            expired_sessions = []
            for session_id, session in self.active_sessions.items():
                last_activity = session.get("last_activity", current_time)
                session_timeout = session.get(
                    "timeout_minutes",
                    self.security_config.session_timeout_minutes,
                )

                if isinstance(last_activity, str):
                    last_activity = datetime.fromisoformat(last_activity)

                if current_time - last_activity > timedelta(minutes=session_timeout):
                    expired_sessions.append(session_id)

            for session_id in expired_sessions:
                session = self.active_sessions.pop(session_id, {})
                await self.log_audit_event(
                    SecurityEventType.LOGOUT,
                    session.get("user_id"),
                    "session_cleanup",
                    "session_expired",
                    SecurityLevel.LOW,
                    True,
                    metadata={"session_id": session_id},
                )

            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")

    async def mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive data in logs and responses."""
        if not self.security_config.sensitive_data_masking:
            return data

        try:
            masked_data = {}

            for key, value in data.items():
                if isinstance(value, dict):
                    masked_data[key] = await self.mask_sensitive_data(value)
                elif isinstance(value, str) and any(
                    sensitive in key.lower()
                    for sensitive in [
                        "password",
                        "token",
                        "secret",
                        "key",
                        "auth",
                        "credential",
                    ]
                ):
                    # Mask sensitive string data
                    masked_data[key] = "***MASKED***"
                elif isinstance(value, list):
                    # Recursively mask list items
                    masked_data[key] = [
                        (
                            await self.mask_sensitive_data(item)
                            if isinstance(item, dict)
                            else (
                                "***MASKED***"
                                if isinstance(item, str)
                                and any(
                                    s in key.lower()
                                    for s in ["password", "token", "secret"]
                                )
                                else item
                            )
                        )
                        for item in value
                    ]
                else:
                    masked_data[key] = value

            return masked_data

        except Exception as e:
            logger.error(f"Failed to mask sensitive data: {e}")
            return data
