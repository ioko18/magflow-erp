"""eMAG Integration Configuration

This module handles the configuration for the eMAG Marketplace API integration.
"""

import os
from enum import Enum
from functools import lru_cache
from typing import Any, Optional

from pydantic import AnyHttpUrl, Field, field_validator, ConfigDict, BaseModel, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmagEnvironment(str, Enum):
    """eMAG API environments."""

    SANDBOX = "sandbox"
    PRODUCTION = "production"


class EmagAccountType(str, Enum):
    """eMAG account types."""

    MAIN = "main"  # Seller-Fulfilled Network (SFN)
    FBE = "fbe"  # Fulfilled by eMAG


class EmagAccountConfig(BaseModel):
    """Configuration for a single eMAG account."""

    username: str = Field(..., description="API username")
    password: str = Field(..., description="API password")
    warehouse_id: int = Field(..., description="Warehouse ID for this account")
    ip_whitelist_name: str = Field(..., description="IP whitelist name for this account")
    callback_base: AnyHttpUrl = Field(..., description="Base URL for callbacks")

    # Ignore any extra fields that may be present in the environment
    model_config = ConfigDict(extra="ignore")


class EmagSettings(BaseSettings):
    """eMAG API settings."""

    # Environment configuration
    env: EmagEnvironment = Field(
        default=EmagEnvironment.SANDBOX,
        description="eMAG API environment (sandbox/production)",
        env="EMAG_ENV",
    )

    # API Configuration
    api_base_url: str = Field(
        default="https://marketplace-api.emag.ro/api-3",
        description="Base URL for eMAG API",
    )

    # Credentials for main and fbe accounts (used only for validation of presence)

    # Rate limiting
    rate_limit_orders: int = Field(
        default=12,
        description="Max requests per second for orders API (default: 12)",
        ge=1,
        le=12,
        env="EMAG_RATE_LIMIT_ORDERS",
    )
    rate_limit_other: int = Field(
        default=3,
        description="Max requests per second for other APIs (default: 3)",
        ge=1,
        le=3,
        env="EMAG_RATE_LIMIT_OTHER",
    )

    # Timeouts (in seconds)
    request_timeout: int = Field(default=30, description="Request timeout in seconds", gt=0)
    api_timeout: int = Field(
        default=30,
        description="Total API timeout in seconds (deprecated; kept for backward compatibility)",
        gt=0,
    )
    connect_timeout: int = Field(default=10, description="Connection timeout in seconds", gt=0)

    # Retry configuration
    max_retries: int = Field(default=3, description="Maximum number of retries for failed requests", ge=0, le=5)
    retry_delay: float = Field(default=1.0, description="Initial delay between retries in seconds", gt=0)

    # Circuit breaker configuration
    circuit_breaker_failures: int = Field(default=5, description="Number of failures before opening the circuit", gt=0)
    circuit_breaker_timeout: int = Field(default=60, description="Circuit breaker timeout in seconds", gt=0)

    # Logging
    log_level: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    log_format: str = Field(default="json", description="Log format (json, text)")

    # Monitoring
    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")
    tracing_enabled: bool = Field(default=True, description="Enable distributed tracing")

    # Nested account configurations (populated via validator)
    main: Optional[EmagAccountConfig] = None
    fbe: Optional[EmagAccountConfig] = None

    # Settings model config – only variables with EMAG_ prefix are considered
    model_config = SettingsConfigDict(env_prefix="EMAG_", env_file=None, extra="allow")

    @field_validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of {valid_levels}")
        return v.upper()

    @field_validator("main", "fbe", mode="before")
    @classmethod
    def load_account_config(cls, v: Any, info: Any) -> Optional[dict]:
        """Load account configuration from environment variables for a given account type."""
        field_name = info.field_name
        prefix = f"EMAG_{field_name.upper()}_"
        env_vars = {
            k[len(prefix) :].lower(): v
            for k, v in os.environ.items()
            if k.startswith(prefix)
        }
        account_config: dict = {}
        if "username" in env_vars:
            account_config["username"] = env_vars["username"]
        if "password" in env_vars:
            account_config["password"] = env_vars["password"]
        if "warehouse_id" in env_vars:
            try:
                account_config["warehouse_id"] = int(env_vars["warehouse_id"])
            except (ValueError, TypeError):
                pass
        if "ip_whitelist_name" in env_vars:
            account_config["ip_whitelist_name"] = env_vars["ip_whitelist_name"]
        if "callback_base" in env_vars:
            account_config["callback_base"] = env_vars["callback_base"]
        required = ["username", "password", "warehouse_id", "ip_whitelist_name", "callback_base"]
        if all(k in account_config for k in required):
            return account_config
        return None

    @model_validator(mode="after")
    def ensure_timeout_consistency(cls, values: "EmagSettings") -> "EmagSettings":
        """Keep api_timeout and request_timeout in sync for backwards compatibility."""

        if values.api_timeout is None:
            values.api_timeout = values.request_timeout
        elif values.api_timeout != values.request_timeout:
            values.request_timeout = values.api_timeout
        return values

    def get_account_config(self, account_type: EmagAccountType) -> EmagAccountConfig:
        account = getattr(self, account_type.value)
        if account is None:
            raise ValueError(f"No configuration found for account type: {account_type}")
        return account


@lru_cache
def get_settings() -> EmagSettings:
    return EmagSettings()

# Create a cached settings instance for module import
settings = get_settings()

# Export commonly used settings
ENVIRONMENT = settings.env
RATE_LIMIT_ORDERS = settings.rate_limit_orders
RATE_LIMIT_OTHER = settings.rate_limit_other

__all__ = ["EmagAccountType", "EmagEnvironment", "settings"]
