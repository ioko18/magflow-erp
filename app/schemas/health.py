"""Health check response models."""

from datetime import datetime
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field

class HealthCheckResult(BaseModel):
    """Single health check result."""
    status: Literal["healthy", "unhealthy", "disabled"] = Field(
        ...,
        description="Status of the health check"
    )
    message: str = Field(
        ...,
        description="Human-readable status message"
    )
    check_type: str = Field(
        ...,
        description="Type of health check (e.g., 'database', 'jwks')"
    )
    timestamp: datetime = Field(
        ...,
        description="When the check was performed"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional check-specific metadata"
    )

class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: str = Field(
        ...,
        description="Overall service status"
    )
    timestamp: datetime = Field(
        ...,
        description="When the health check was performed"
    )
    checks: Dict[str, HealthCheckResult] = Field(
        ...,
        description="Individual health check results"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional service details"
    )

class StartupProbeResponse(BaseModel):
    """Startup probe response model."""
    status: str = Field(
        ...,
        description="Current status of the service during startup"
    )
    message: str = Field(
        ...,
        description="Detailed message about the startup status"
    )
    timestamp: datetime = Field(
        ...,
        description="When the startup check was performed"
    )
    startup_time: datetime = Field(
        ...,
        description="When the service started up"
    )
    uptime_seconds: float = Field(
        ...,
        description="How long the service has been running in seconds"
    )
    warmup_period_seconds: int = Field(
        ...,
        description="Configured warmup period in seconds"
    )
    ready: bool = Field(
        ...,
        description="Whether the service is ready to handle requests"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
