"""Admin dashboard schemas for MagFlow ERP."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class DashboardStats(BaseModel):
    """Dashboard statistics model."""

    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Number of active users")
    total_products: int = Field(..., description="Total number of products")
    total_orders: int = Field(..., description="Total number of orders")
    total_revenue: float = Field(..., description="Total revenue")
    monthly_growth: float = Field(..., description="Monthly growth percentage")
    system_health: str = Field(..., description="System health status")
    recent_activities: list[dict[str, Any]] = Field(
        ...,
        description="Recent system activities",
    )

    model_config = ConfigDict(from_attributes=True)


class UserSummary(BaseModel):
    """User summary for admin dashboard."""

    id: int = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    full_name: str | None = Field(None, description="User full name")
    is_active: bool = Field(..., description="Whether user is active")
    is_superuser: bool = Field(..., description="Whether user is superuser")
    last_login: datetime | None = Field(None, description="Last login time")
    created_at: datetime = Field(..., description="User creation time")
    role_names: list[str] = Field(..., description="User role names")
    failed_login_attempts: int = Field(..., description="Failed login attempts")

    model_config = ConfigDict(from_attributes=True)


class SystemMetrics(BaseModel):
    """System metrics for monitoring."""

    cpu_usage: float = Field(..., description="CPU usage percentage")
    memory_usage: float = Field(..., description="Memory usage percentage")
    disk_usage: float = Field(..., description="Disk usage percentage")
    database_connections: int = Field(..., description="Active database connections")
    cache_hit_rate: float = Field(..., description="Cache hit rate percentage")
    response_time_avg: float = Field(..., description="Average response time (ms)")
    error_rate: float = Field(..., description="Error rate percentage")
    uptime: str = Field(..., description="System uptime")

    model_config = ConfigDict(from_attributes=True)


class AuditLogSummary(BaseModel):
    """Audit log summary for dashboard."""

    id: int = Field(..., description="Audit log ID")
    user_id: int | None = Field(None, description="User ID")
    user_email: str | None = Field(None, description="User email")
    action: str = Field(..., description="Action performed")
    resource: str = Field(..., description="Resource affected")
    timestamp: datetime = Field(..., description="Action timestamp")
    success: bool = Field(..., description="Whether action was successful")
    ip_address: str | None = Field(None, description="IP address")

    model_config = ConfigDict(from_attributes=True)


class AdminUserCreate(BaseModel):
    """Admin user creation request."""

    email: EmailStr = Field(..., description="User email")
    full_name: str | None = Field(None, description="User full name")
    password: str = Field(..., min_length=8, description="User password")
    is_active: bool = Field(True, description="Whether user is active")
    is_superuser: bool = Field(False, description="Whether user is superuser")
    role_ids: list[int] = Field(..., description="Role IDs to assign")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


class AdminUserUpdate(BaseModel):
    """Admin user update request."""

    email: EmailStr | None = Field(None, description="User email")
    full_name: str | None = Field(None, description="User full name")
    is_active: bool | None = Field(None, description="Whether user is active")
    is_superuser: bool | None = Field(None, description="Whether user is superuser")
    role_ids: list[int] | None = Field(None, description="Role IDs to assign")
    reset_password: bool = Field(False, description="Whether to reset user password")


class RoleSummary(BaseModel):
    """Role summary for admin dashboard."""

    id: int = Field(..., description="Role ID")
    name: str = Field(..., description="Role name")
    description: str | None = Field(None, description="Role description")
    is_system_role: bool = Field(..., description="Whether this is a system role")
    user_count: int = Field(..., description="Number of users with this role")
    permission_count: int = Field(..., description="Number of permissions")
    created_at: datetime = Field(..., description="Role creation time")

    model_config = ConfigDict(from_attributes=True)


class PermissionSummary(BaseModel):
    """Permission summary for admin dashboard."""

    id: int = Field(..., description="Permission ID")
    name: str = Field(..., description="Permission name")
    description: str | None = Field(None, description="Permission description")
    resource: str = Field(..., description="Resource name")
    action: str = Field(..., description="Action name")
    role_count: int = Field(..., description="Number of roles with this permission")
    created_at: datetime = Field(..., description="Permission creation time")

    model_config = ConfigDict(from_attributes=True)


class DashboardAlert(BaseModel):
    """System alert for dashboard."""

    id: str = Field(..., description="Alert ID")
    type: str = Field(..., description="Alert type (info, warning, error, critical)")
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    timestamp: datetime = Field(..., description="Alert timestamp")
    acknowledged: bool = Field(False, description="Whether alert is acknowledged")
    user_id: int | None = Field(None, description="User who acknowledged")

    model_config = ConfigDict(from_attributes=True)


class SystemHealth(BaseModel):
    """System health status."""

    status: str = Field(..., description="Overall system status")
    database: str = Field(..., description="Database status")
    cache: str = Field(..., description="Cache status")
    api: str = Field(..., description="API status")
    last_check: datetime = Field(..., description="Last health check time")
    issues: list[str] = Field(..., description="List of current issues")

    model_config = ConfigDict(from_attributes=True)


class AdminActivityLog(BaseModel):
    """Admin activity log for tracking admin actions."""

    id: int = Field(..., description="Activity log ID")
    admin_id: int = Field(..., description="Admin user ID")
    admin_email: str = Field(..., description="Admin email")
    action: str = Field(..., description="Action performed")
    target_type: str = Field(
        ...,
        description="Target type (user, role, permission, etc.)",
    )
    target_id: str | None = Field(None, description="Target ID")
    details: str | None = Field(None, description="Action details")
    timestamp: datetime = Field(..., description="Action timestamp")
    ip_address: str | None = Field(None, description="IP address")

    model_config = ConfigDict(from_attributes=True)
