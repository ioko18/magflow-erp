"""eMAG Integration Configuration

This module handles the configuration for the eMAG Marketplace API integration.
"""

import os
from enum import Enum
from functools import lru_cache
from typing import Any, Optional

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmagEnvironment(str, Enum):
    """eMAG API environments."""

    SANDBOX = "sandbox"
    PRODUCTION = "production"


class EmagAccountType(str, Enum):
    """eMAG account types."""

    MAIN = "main"  # Seller-Fulfilled Network (SFN)
    FBE = "fbe"  # Fulfilled by eMAG


class EmagAccountConfig(BaseSettings):
    """Configuration for a single eMAG account."""

    username: str = Field(..., description="API username")
    password: str = Field(..., description="API password")
    warehouse_id: int = Field(..., description="Warehouse ID for this account")
    ip_whitelist_name: str = Field(
        ...,
        description="IP whitelist name for this account",
    )
    callback_base: AnyHttpUrl = Field(..., description="Base URL for callbacks")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


class EmagSettings(BaseSettings):
    """eMAG API settings."""

    # Environment configuration
    env: EmagEnvironment = Field(
        default=EmagEnvironment.SANDBOX,
        description="eMAG API environment (sandbox/production)",
    )

    # API Configuration
    api_base_url: str = Field(
        default="https://marketplace-api.emag.ro/api-3",
        description="Base URL for eMAG API",
    )

    # Credentials
    emag_main_username: str = Field(default="", description="Main account username")
    emag_main_password: str = Field(default="", description="Main account password")
    emag_fbe_username: str = Field(default="", description="FBE account username")
    emag_fbe_password: str = Field(default="", description="FBE account password")

    # Rate limiting
    rate_limit_orders: int = Field(
        default=12,
        description="Max requests per second for orders API (default: 12)",
        ge=1,
        le=12,
    )
    rate_limit_other: int = Field(
        default=3,
        description="Max requests per second for other APIs (default: 3)",
        ge=1,
        le=3,
    )

    # Timeouts (in seconds)
    request_timeout: int = Field(
        default=30,
        description="Request timeout in seconds",
        gt=0,
    )
    connect_timeout: int = Field(
        default=10,
        description="Connection timeout in seconds",
        gt=0,
    )

    # Retry configuration
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed requests",
        ge=0,
        le=5,
    )
    retry_delay: float = Field(
        default=1.0,
        description="Initial delay between retries in seconds",
        gt=0,
    )

    # Circuit breaker configuration
    circuit_breaker_failures: int = Field(
        default=5,
        description="Number of failures before opening the circuit",
        gt=0,
    )
    circuit_breaker_timeout: int = Field(
        default=60,
        description="Circuit breaker timeout in seconds",
        gt=0,
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    log_format: str = Field(default="json", description="Log format (json, text)")

    # Monitoring
    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")
    tracing_enabled: bool = Field(
        default=True,
        description="Enable distributed tracing",
    )

    # Account configurations
    main: Optional[EmagAccountConfig] = None
    fbe: Optional[EmagAccountConfig] = None

    model_config = SettingsConfigDict(
        env_prefix="EMAG_",
        env_file=".env.emag",
        env_file_encoding="utf-8",
        env_nested_delimiter="_",
        extra="ignore",  # Ignore extra fields in the config
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of {valid_levels}")
        return v.upper()

    @field_validator("main", "fbe", mode="before")
    @classmethod
    def load_account_config(cls, v: Any, info: Any) -> Optional[dict]:
        """Load account configuration from environment variables."""
        if v is not None and isinstance(v, dict):
            # If we already have a dict, return it as is
            return v

        # Get the field name (main or fbe)
        field_name = info.field_name

        # Get the environment variables for this account
        prefix = f"EMAG_{field_name.upper()}_"
        env_vars = {
            k[len(prefix) :].lower(): v
            for k, v in os.environ.items()
            if k.startswith(prefix)
        }

        # Map the environment variables to the expected structure
        account_config = {}
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

        # If we have all required fields, return the config
        required_fields = [
            "username",
            "password",
            "warehouse_id",
            "ip_whitelist_name",
            "callback_base",
        ]
        if all(field in account_config for field in required_fields):
            return account_config

        return None

    def get_account_config(self, account_type: EmagAccountType) -> EmagAccountConfig:
        """Get configuration for a specific account type."""
        account = getattr(self, account_type.value)
        if account is None:
            raise ValueError(f"No configuration found for account type: {account_type}")
        return account


@lru_cache
def get_settings() -> EmagSettings:
    """Get cached settings instance."""
    return EmagSettings()


# Create settings instance
settings = EmagSettings()

# Export commonly used settings
ENVIRONMENT = settings.env
RATE_LIMIT_ORDERS = settings.rate_limit_orders
RATE_LIMIT_OTHER = settings.rate_limit_other

__all__ = ["EmagAccountType", "EmagEnvironment", "settings"]
