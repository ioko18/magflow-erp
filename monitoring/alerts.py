"""
Monitoring alerts configuration for the MagFlow ERP system.

This module defines alert rules and configurations for monitoring the health
of the application and its dependencies.
"""

import logging

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class AlertRule(BaseModel):
    """Configuration for a single alert rule."""

    name: str = Field(..., description="Unique name for the alert rule")
    metric: str = Field(..., description="The metric to monitor")
    condition: str = Field(
        ..., description="Condition expression (e.g., '> 90%' or '== 0')"
    )
    duration: str = Field(
        "5m", description="Duration the condition must be true before alerting"
    )
    severity: str = Field(
        "warning", description="Alert severity (critical, warning, info)"
    )
    summary: str = Field(..., description="Short description of the alert")
    description: str = Field(..., description="Detailed description of the alert")
    labels: dict[str, str] = Field(
        default_factory=dict, description="Additional labels for the alert"
    )
    annotations: dict[str, str] = Field(
        default_factory=dict, description="Additional annotations for the alert"
    )

    @validator("severity")
    def validate_severity(cls, v):
        if v not in ("critical", "warning", "info"):
            raise ValueError("Severity must be one of: critical, warning, info")
        return v


class AlertGroup(BaseModel):
    """A group of related alert rules."""

    name: str
    rules: list[AlertRule]


# Define default alert rules
DEFAULT_ALERT_RULES = {
    "database": AlertGroup(
        name="database",
        rules=[
            AlertRule(
                name="high_database_latency",
                metric="database_connection_latency_seconds",
                condition="> 1",  # seconds
                duration="5m",
                severity="warning",
                summary="High database latency",
                description="Database response time is higher than 1 second",
                labels={"service": "database", "severity": "warning"},
            ),
            AlertRule(
                name="database_connection_failed",
                metric="database_connection_status",
                condition="== 0",
                duration="1m",
                severity="critical",
                summary="Database connection failed",
                description="Unable to establish database connection",
                labels={"service": "database", "severity": "critical"},
            ),
            AlertRule(
                name="high_connection_pool_usage",
                metric="database_connection_pool_usage_ratio",
                condition="> 0.8",  # 80%
                duration="10m",
                severity="warning",
                summary="High database connection pool usage",
                description="Database connection pool usage is above 80%",
                labels={"service": "database", "severity": "warning"},
            ),
        ],
    ),
    "api": AlertGroup(
        name="api",
        rules=[
            AlertRule(
                name="high_api_error_rate",
                metric='http_requests_total{status=~"5.."} / rate(http_requests_total[5m])',
                condition="> 0.05",  # 5% error rate
                duration="5m",
                severity="warning",
                summary="High API error rate",
                description="More than 5% of API requests are failing with 5xx errors",
                labels={"service": "api", "severity": "warning"},
            ),
            AlertRule(
                name="high_api_latency",
                metric='http_request_duration_seconds_bucket{le="1"} / http_request_duration_seconds_count',
                condition="< 0.95",  # 95th percentile > 1s
                duration="10m",
                severity="warning",
                summary="High API latency",
                description="API latency is high (95th percentile > 1s)",
                labels={"service": "api", "severity": "warning"},
            ),
        ],
    ),
}


def get_alert_rules() -> dict[str, AlertGroup]:
    """Get all configured alert rules.

    Returns:
        Dict mapping group names to AlertGroup objects
    """
    return DEFAULT_ALERT_RULES


def get_alert_rule(name: str) -> AlertRule | None:
    """Get a specific alert rule by name.

    Args:
        name: Name of the alert rule to retrieve

    Returns:
        The matching AlertRule or None if not found
    """
    for group in DEFAULT_ALERT_RULES.values():
        for rule in group.rules:
            if rule.name == name:
                return rule
    return None


def generate_prometheus_rules() -> dict:
    """Generate Prometheus alerting rules from the configured alerts.

    Returns:
        Dict containing Prometheus-compatible alerting rules
    """
    groups = []

    for group_name, group in DEFAULT_ALERT_RULES.items():
        rules = []
        for rule in group.rules:
            prom_rule = {
                "alert": rule.name,
                "expr": f"{rule.metric} {rule.condition}",
                "for": rule.duration,
                "labels": {"severity": rule.severity, **rule.labels},
                "annotations": {
                    "summary": rule.summary,
                    "description": rule.description,
                    **rule.annotations,
                },
            }
            rules.append(prom_rule)

        groups.append({"name": f"{group_name}_alerts", "rules": rules})

    return {"groups": groups}


def validate_alert_config() -> bool:
    """Validate the alert configuration.

    Returns:
        bool: True if configuration is valid, raises ValueError otherwise
    """
    # This will raise ValidationError if any alert rule is invalid
    for group in DEFAULT_ALERT_RULES.values():
        for rule in group.rules:
            # The Pydantic model validation happens on instantiation,
            # so we just need to access the attributes to trigger validation
            _ = rule.name
            _ = rule.metric
            _ = rule.condition
            _ = rule.severity
    return True
