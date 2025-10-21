"""Configuration Management System for MagFlow ERP.

This module provides centralized configuration management with validation,
environment-specific settings, and runtime configuration updates.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, TypeVar

import yaml

from app.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class ConfigurationSection:
    """Base configuration section with validation."""

    def validate(self) -> bool:
        """Validate configuration section."""
        return True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


@dataclass
class DatabaseConfig(ConfigurationSection):
    """Database configuration."""

    host: str = "localhost"
    port: int = 5432
    name: str = "magflow"
    user: str = "postgres"
    password: str = ""
    schema: str = "app"
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False
    autocommit: bool = False
    autoflush: bool = False

    def validate(self) -> bool:
        """Validate database configuration."""
        if self.port <= 0 or self.port > 65535:
            raise ConfigurationError(f"Invalid database port: {self.port}")

        if self.pool_size <= 0:
            raise ConfigurationError("Database pool size must be positive")

        if self.max_overflow < 0:
            raise ConfigurationError("Database max overflow cannot be negative")

        return True


@dataclass
class CacheConfig(ConfigurationSection):
    """Cache configuration."""

    backend: str = "redis"
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = ""
    default_ttl: int = 300
    max_ttl: int = 3600
    key_prefix: str = "magflow"

    def validate(self) -> bool:
        """Validate cache configuration."""
        if self.backend not in ["redis", "memcached", "memory"]:
            raise ConfigurationError(f"Unsupported cache backend: {self.backend}")

        if self.port <= 0 or self.port > 65535:
            raise ConfigurationError(f"Invalid cache port: {self.port}")

        if self.default_ttl <= 0:
            raise ConfigurationError("Default TTL must be positive")

        return True


@dataclass
class SecurityConfig(ConfigurationSection):
    """Security configuration."""

    secret_key: str = ""
    refresh_secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    key_expire_days: int = 30
    keyset_dir: str = "jwt-keys"
    rate_limit_per_minute: int = 60
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15

    def validate(self) -> bool:
        """Validate security configuration."""
        if not self.secret_key:
            raise ConfigurationError("Secret key is required")

        if len(self.secret_key) < 32:
            raise ConfigurationError("Secret key must be at least 32 characters long")

        if self.algorithm not in ["HS256", "HS512", "RS256"]:
            raise ConfigurationError(f"Unsupported JWT algorithm: {self.algorithm}")

        if self.access_token_expire_minutes <= 0:
            raise ConfigurationError("Access token expiry must be positive")

        return True


@dataclass
class APISettings(ConfigurationSection):
    """API configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = False
    debug: bool = False
    title: str = "MagFlow ERP"
    version: str = "1.0.0"
    description: str = "Enterprise Resource Planning System"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list = field(default_factory=lambda: ["*"])
    cors_allow_credentials: bool = True
    cors_allow_methods: list = field(default_factory=lambda: ["*"])
    cors_allow_headers: list = field(default_factory=lambda: ["*"])

    def validate(self) -> bool:
        """Validate API configuration."""
        if self.port <= 0 or self.port > 65535:
            raise ConfigurationError(f"Invalid API port: {self.port}")

        if self.workers <= 0:
            raise ConfigurationError("Worker count must be positive")

        return True


@dataclass
class ExternalServicesConfig(ConfigurationSection):
    """External services configuration."""

    emag_api_base_url: str = "https://api.emag.ro"
    emag_api_username: str = ""
    emag_api_password: str = ""
    api_timeout: int = 30

    def validate(self) -> bool:
        """Validate external services configuration."""
        if self.api_timeout <= 0:
            raise ConfigurationError("API timeout must be positive")

        return True


@dataclass
class LoggingConfig(ConfigurationSection):
    """Logging configuration."""

    level: str = "INFO"
    format: str = "json"
    file_path: str = "logs/app.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    enable_console: bool = True
    enable_file: bool = True

    def validate(self) -> bool:
        """Validate logging configuration."""
        if self.level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ConfigurationError(f"Invalid log level: {self.level}")

        if self.max_file_size <= 0:
            raise ConfigurationError("Max file size must be positive")

        if self.backup_count < 0:
            raise ConfigurationError("Backup count cannot be negative")

        return True


@dataclass
class MonitoringConfig(ConfigurationSection):
    """Monitoring configuration."""

    enabled: bool = True
    health_check_interval: int = 30
    metrics_interval: int = 60
    enable_prometheus: bool = True
    prometheus_port: int = 9090

    def validate(self) -> bool:
        """Validate monitoring configuration."""
        if self.health_check_interval <= 0:
            raise ConfigurationError("Health check interval must be positive")

        if self.metrics_interval <= 0:
            raise ConfigurationError("Metrics interval must be positive")

        if self.prometheus_port <= 0 or self.prometheus_port > 65535:
            raise ConfigurationError(f"Invalid Prometheus port: {self.prometheus_port}")

        return True


@dataclass
class AppConfig:
    """Main application configuration."""

    # Core settings
    environment: str = "development"
    debug: bool = False
    testing: bool = False

    # Section configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    api: APISettings = field(default_factory=APISettings)
    external_services: ExternalServicesConfig = field(
        default_factory=ExternalServicesConfig,
    )
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)

    def validate(self) -> bool:
        """Validate entire configuration."""
        try:
            # Validate all sections
            self.database.validate()
            self.cache.validate()
            self.security.validate()
            self.api.validate()
            self.external_services.validate()
            self.logging.validate()
            self.monitoring.validate()

            # Environment-specific validation
            self._validate_environment()

            return True

        except ConfigurationError:
            raise

    def _validate_environment(self):
        """Validate environment-specific settings."""
        if self.environment == "production":
            # Production-specific validations
            if self.debug:
                raise ConfigurationError(
                    "Debug mode should not be enabled in production",
                )

            if self.api.cors_origins == ["*"]:
                logger.warning(
                    "Wildcard CORS origins in production - consider restricting",
                )

            if (
                not self.security.secret_key
                or self.security.secret_key == "change-this-in-production"
            ):
                raise ConfigurationError(
                    "Production secret key must be properly configured",
                )

            if self.database.host == "localhost":
                raise ConfigurationError("Production database should not use localhost")

        elif self.environment == "testing":
            self.testing = True
            self.debug = True
            self.logging.level = "DEBUG"

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        result = {
            "environment": self.environment,
            "debug": self.debug,
            "testing": self.testing,
        }

        # Convert section configurations
        for section_name in [
            "database",
            "cache",
            "security",
            "api",
            "external_services",
            "logging",
            "monitoring",
        ]:
            section = getattr(self, section_name)
            result[section_name] = section.to_dict()

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        """Create configuration from dictionary."""
        config = cls()

        # Update core settings
        for key in ["environment", "debug", "testing"]:
            if key in data:
                setattr(config, key, data[key])

        # Update section configurations
        for section_name in [
            "database",
            "cache",
            "security",
            "api",
            "external_services",
            "logging",
            "monitoring",
        ]:
            if section_name in data:
                section_data = data[section_name]
                section = getattr(config, section_name)

                for key, value in section_data.items():
                    if hasattr(section, key):
                        setattr(section, key, value)

        return config

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create configuration from environment variables."""
        config = cls()

        # Environment settings
        config.environment = os.getenv("APP_ENV", "development")
        config.debug = os.getenv("DEBUG", "false").lower() == "true"
        config.testing = os.getenv("TESTING", "false").lower() == "true"

        # Database settings
        config.database.host = os.getenv("DB_HOST", "localhost")
        config.database.port = int(os.getenv("DB_PORT", "5432"))
        config.database.name = os.getenv("DB_NAME", "magflow")
        config.database.user = os.getenv("DB_USER", "postgres")
        config.database.password = os.getenv("DB_PASS", "")
        config.database.schema = os.getenv("DB_SCHEMA", "app")

        # Security settings
        config.security.secret_key = os.getenv("SECRET_KEY", "")
        config.security.refresh_secret_key = os.getenv("REFRESH_SECRET_KEY", "")
        config.security.algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        config.security.access_token_expire_minutes = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"),
        )
        config.security.refresh_token_expire_days = int(
            os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"),
        )

        # API settings
        config.api.host = os.getenv("API_HOST", "0.0.0.0")
        config.api.port = int(os.getenv("API_PORT", "8000"))
        config.api.debug = config.debug

        # External services
        config.external_services.emag_api_base_url = os.getenv(
            "EMAG_API_BASE_URL",
            "https://api.emag.ro",
        )
        config.external_services.emag_api_username = os.getenv("EMAG_API_USERNAME", "")
        config.external_services.emag_api_password = os.getenv("EMAG_API_PASSWORD", "")

        return config


class ConfigurationManager:
    """Manager for handling configuration loading and validation."""

    def __init__(self):
        self._config: AppConfig | None = None
        self._config_files: dict[str, str] = {
            "development": "config/development.yaml",
            "production": "config/production.yaml",
            "testing": "config/testing.yaml",
        }

    def load_configuration(self, environment: str | None = None) -> AppConfig:
        """Load configuration for specified environment."""
        env = environment or os.getenv("APP_ENV", "development")

        config = AppConfig.from_env()

        # Try to load configuration file
        config_file = self._config_files.get(env)
        if config_file and Path(config_file).exists():
            file_config = self._load_config_file(config_file)
            config = AppConfig.from_dict({**config.to_dict(), **file_config})

        # Set environment
        config.environment = env

        # Validate configuration
        config.validate()

        self._config = config
        logger.info("Configuration loaded for environment: %s", env)

        return config

    def _load_config_file(self, file_path: str) -> dict[str, Any]:
        """Load configuration from file."""
        path = Path(file_path)

        if not path.exists():
            raise ConfigurationError(f"Configuration file not found: {file_path}")

        try:
            if path.suffix == ".json":
                with open(path) as f:
                    return json.load(f)
            elif path.suffix in [".yaml", ".yml"]:
                with open(path) as f:
                    return yaml.safe_load(f)
            else:
                raise ConfigurationError(
                    f"Unsupported configuration file format: {path.suffix}",
                )

        except Exception as e:
            raise ConfigurationError(
                f"Failed to load configuration file {file_path}: {e}",
            ) from e

    def get_config(self) -> AppConfig:
        """Get current configuration."""
        if not self._config:
            raise ConfigurationError("Configuration not loaded")
        return self._config

    def reload_config(self) -> AppConfig:
        """Reload configuration."""
        env = os.getenv("APP_ENV", "development")
        return self.load_configuration(env)

    def update_config(self, updates: dict[str, Any]):
        """Update configuration at runtime."""
        if not self._config:
            raise ConfigurationError("Configuration not loaded")

        # Update configuration
        for key, value in updates.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
            else:
                # Check if it's a nested configuration
                for section in [
                    "database",
                    "cache",
                    "security",
                    "api",
                    "external_services",
                    "logging",
                    "monitoring",
                ]:
                    section_config = getattr(self._config, section)
                    if hasattr(section_config, key):
                        setattr(section_config, key, value)
                        break

        # Re-validate
        self._config.validate()

        logger.info("Configuration updated with %d changes", len(updates))


# Global configuration manager
_config_manager = ConfigurationManager()


@lru_cache
def get_config() -> AppConfig:
    """Get cached application configuration."""
    return _config_manager.get_config()


def load_config(environment: str | None = None) -> AppConfig:
    """Load application configuration."""
    return _config_manager.load_configuration(environment)


def reload_config() -> AppConfig:
    """Reload application configuration."""
    return _config_manager.reload_config()


def update_config(updates: dict[str, Any]):
    """Update configuration at runtime."""
    _config_manager.update_config(updates)


# Configuration validation utilities
def validate_production_config(config: AppConfig) -> bool:
    """Validate production configuration."""
    if config.environment != "production":
        return True

    # Additional production-specific validations
    errors = []

    if len(config.security.secret_key) < 64:
        errors.append("Production secret key should be at least 64 characters")

    if config.database.host == "localhost":
        errors.append("Production database should not use localhost")

    if config.api.cors_origins == ["*"]:
        logger.warning("Wildcard CORS origins in production")

    if errors:
        raise ConfigurationError(
            f"Production configuration errors: {', '.join(errors)}",
        )

    return True


def validate_database_connection(config: AppConfig) -> bool:
    """Validate database connection."""
    # This would test actual database connectivity
    # For now, just validate configuration
    config.database.validate()
    return True


# Configuration export utilities
def export_config_to_file(config: AppConfig, file_path: str, format: str = "yaml"):
    """Export configuration to file."""
    data = config.to_dict()

    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if format == "json":
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        elif format in ["yaml", "yml"]:
            with open(path, "w") as f:
                yaml.dump(data, f, default_flow_style=False)
        else:
            raise ConfigurationError(f"Unsupported export format: {format}")

        logger.info("Configuration exported to %s", file_path)

    except Exception as e:
        raise ConfigurationError(f"Failed to export configuration: {e}") from e


# Environment detection utilities
def is_development() -> bool:
    """Check if running in development environment."""
    return get_config().environment == "development"


def is_production() -> bool:
    """Check if running in production environment."""
    return get_config().environment == "production"


def is_testing() -> bool:
    """Check if running in testing environment."""
    return get_config().environment == "testing"


# Configuration logging
def log_configuration(config: AppConfig, level: str = "INFO"):
    """Log configuration for debugging."""
    logger.log(getattr(logging, level), "Application Configuration:")
    logger.log(getattr(logging, level), "=" * 50)

    for key, value in config.to_dict().items():
        if isinstance(value, dict):
            logger.log(getattr(logging, level), f"{key}:")
            for sub_key, sub_value in value.items():
                logger.log(getattr(logging, level), f"  {sub_key}: {sub_value}")
        else:
            logger.log(getattr(logging, level), f"{key}: {value}")

    logger.log(getattr(logging, level), "=" * 50)
