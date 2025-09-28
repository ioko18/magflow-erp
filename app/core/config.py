"""Application configuration settings.

This module contains all configuration settings for the application,
loaded from environment variables with sensible defaults.
"""

import logging
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Application settings
    APP_ENV: str = "development"
    ENVIRONMENT: str = "development"  # Alias for APP_ENV for compatibility
    APP_NAME: str = "MagFlow ERP"
    SERVICE_NAME: str = (
        "magflow-service"  # Used for logging, metrics, and service identification
    )
    PROJECT_NAME: str = (
        "MagFlow ERP"  # Used for OpenAPI documentation and other places where the project name is needed
    )
    APP_PORT: int = 8000
    APP_DEBUG: bool = True
    DEBUG: bool = True  # Alias for APP_DEBUG for compatibility
    SQL_ECHO: bool = False
    TESTING: bool = False  # Flag to indicate if the application is running in test mode
    DOCS_ENABLED: bool = True  # Control FastAPI documentation visibility
    APP_SECRET: str = "change-this-in-production"
    APP_VERSION: str = "1.0.0"

    # Database settings
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASS: str = "password"
    DB_NAME: str = "magflow"
    DB_SCHEMA: str = "app"

    # Connection pool settings
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 30
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600
    DB_POOL_PRE_PING: bool = True
    DB_ECHO: bool = False
    DB_AUTOCOMMIT: bool = False
    DB_AUTOFLUSH: bool = False
    DB_COMMAND_TIMEOUT: int = 30

    @computed_field
    @property
    def DB_URI(self) -> str:
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            return database_url
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return self.DB_URI

    @computed_field
    @property
    def alembic_url(self) -> str:
        return self.DB_URI.replace("asyncpg", "psycopg2")

    # Feature flag for OpenTelemetry
    ENABLE_OTEL: bool = False

    @property
    def search_path(self) -> str:
        return self.DB_SCHEMA

    # Lower‑case aliases for JWT settings (used by legacy tests)
    @property
    def jwt_algorithm(self) -> str:
        return self.JWT_ALGORITHM

    @property
    def access_token_expire_minutes(self) -> int:
        return self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES

    @property
    def refresh_token_expire_days(self) -> int:
        return self.JWT_REFRESH_TOKEN_EXPIRE_DAYS

    @property
    def secret_key(self) -> str:
        return self.JWT_SECRET_KEY

    @property
    def jwt_issuer(self) -> str:
        return getattr(self, "JWT_ISSUER", "magflow-service")

    @property
    def jwt_audience(self) -> str:
        return getattr(self, "JWT_AUDIENCE", "magflow-api")

    @property
    def jwt_supported_algorithms(self) -> list[str]:
        # Provide both HS256 and RS256 as supported algorithms
        return ["HS256", "RS256"]

    @property
    def jwt_keyset_dir(self) -> str:
        return getattr(self, "JWT_KEYSET_DIR", "jwt-keys")

    @property
    def db_schema_safe(self) -> str:
        """Return a sanitized schema name safe for SQL usage."""
        schema = (self.DB_SCHEMA or "").strip()
        sanitized = "".join(ch for ch in schema if ch.isalnum() or ch == "_")

        if not sanitized:
            logger.warning(
                "DB_SCHEMA is empty after sanitization; defaulting to 'public' schema",
            )
            return "public"

        if sanitized != schema:
            logger.warning(
                "DB_SCHEMA value '%s' contained unsafe characters; using sanitized '%s'",
                schema,
                sanitized,
            )

        return sanitized

    # Redis settings
    REDIS_ENABLED: bool = True
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_SSL: bool = False
    REDIS_SSL_CERT_REQS: Optional[str] = None
    REDIS_SOCKET_TIMEOUT: int = 5  # seconds
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5  # seconds
    REDIS_RETRY_ON_TIMEOUT: bool = True
    REDIS_POOL_SIZE: int = 20
    REDIS_POOL_TIMEOUT: int = 10  # seconds
    REDIS_MAX_CONNECTIONS: int = 100

    # Redis URL for connection
    @property
    def REDIS_URL(self) -> str:
        """Construct Redis URL from individual components or use REDIS_URL if set."""
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            return redis_url
        # Fallback to individual components
        auth_part = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        scheme = "rediss" if self.REDIS_SSL else "redis"
        return (
            f"{scheme}://{auth_part}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        )

    # Cache settings
    CACHE_ENABLED: bool = True
    CACHE_DEFAULT_TTL: int = 3600  # 1 hour in seconds

    # Rate limiting settings
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/minute"  # Default rate limit (requests per minute)
    RATE_LIMIT_STORAGE_URI: str = (
        "redis://localhost:6379/0"  # Redis URL for rate limiting storage
    )

    # eMAG API settings
    EMAG_API_BASE_URL: str = "https://marketplace.emag.ro/api"
    EMAG_API_USER: str = ""  # Should be set via environment variables
    EMAG_API_KEY: str = ""  # Should be set via environment variables
    EMAG_API_TIMEOUT: int = 30  # seconds
    EMAG_MAX_RETRIES: int = 3
    EMAG_RETRY_DELAY: int = 1  # second
    EMAG_RATE_LIMIT: int = 10  # requests per second
    EMAG_CACHE_TTL: int = 86400  # 24 hours in seconds
    emag_main_username: str = ""
    emag_main_password: str = ""
    emag_fbe_username: str = ""
    emag_fbe_password: str = ""

    # Feature flags
    EMAG_INTEGRATION_ENABLED: bool = False

    # Vault settings
    VAULT_ENABLED: bool = False
    VAULT_ADDR: str = "http://vault.vault.svc:8200"
    VAULT_ROLE: str = "magflow"
    VAULT_NAMESPACE: str = "magflow"
    VAULT_SECRET_PATH: str = "magflow"
    VAULT_KV_MOUNT: str = "kv"

    # API settings
    API_PREFIX: str = "/api/v1"
    API_V1_STR: str = "/api/v1"  # For JWT token URL configuration

    # Aliases for compatibility with code/tests using different naming
    @property
    def api_v1_str(self) -> str:
        return self.API_V1_STR

    @property
    def VERSION(self) -> str:
        return self.APP_VERSION

    # OAuth2 settings
    OAUTH2_ENABLED: bool = False
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    FRONTEND_URL: str = "http://localhost:3000"  # For OAuth2 redirects
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_MAX_AGE: int = 600  # 10 minutes
    CORS_ALLOW_METHODS: list[str] = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]
    CORS_EXPOSE_HEADERS: list[str] = ["Content-Length", "Content-Type", "X-Request-ID"]

    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_TO_FILE: bool = True
    LOG_DIR: str = "logs"
    LOG_FILE: str = "app.log"
    LOG_FORMAT: str = "json"  # or 'text'
    LOGS_DIR: str = "logs"
    LOG_ROTATION: str = "1 day"
    LOG_RETENTION: str = "30 days"
    # Additional logging settings
    LOG_MAX_SIZE: int = 10485760  # 10MB
    LOG_BACKUP_COUNT: int = 5

    # Error handling settings
    ERROR_INCLUDE_TRACEBACK: bool = False
    ERROR_SHOW_DETAILS: bool = True
    ERROR_RESPONSE_FORMAT: str = "json"  # or 'text'

    # OpenTelemetry settings
    OTLP_ENABLED: bool = False
    OTLP_ENDPOINT: str = "otel-collector:4317"  # Default to local collector
    OTLP_INSECURE: bool = True  # Set to False in production with proper TLS

    # CORS origins setting for compatibility
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Environment-based CORS settings
    CORS_CONFIG: Dict[str, Dict[str, Any]] = {
        "development": {
            "allow_origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
            "allow_credentials": True,
            "max_age": 600,  # 10 minutes
        },
        "production": {
            "allow_origins": ["https://your-production-domain.com"],
            "allow_credentials": True,
            "max_age": 86400,  # 24 hours
        },
        "testing": {"allow_origins": ["*"], "allow_credentials": False, "max_age": 0},
    }

    # Security headers
    SECURITY_HEADERS: dict = {
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Content-Security-Policy": "default-src 'self'",
    }

    # Server settings
    SERVER_NAME: str = "magflow-service"
    SERVER_HOST: str = "http://localhost:8000"
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # OpenAPI and documentation settings
    DOCS_ENABLED: bool = True
    OPENAPI_URL: str = "/openapi.json"
    DOCS_URL: str = "/docs"

    # Additional eMAG settings
    EMAG_CLIENT_ID: str = ""
    EMAG_USERNAME: str = ""
    EMAG_PASSWORD: str = ""
    EMAG_BASE_URL: str = "https://marketplace-api.emag.ro/api-3"
    EMAG_ACCOUNT_TYPE: str = "main"
    EMAG_ENVIRONMENT: str = "development"

    # eMAG Rate Limiting
    EMAG_RATE_LIMIT_ORDERS: int = 12
    EMAG_RATE_LIMIT_OFFERS: int = 3
    EMAG_RATE_LIMIT_RMA: int = 5
    EMAG_RATE_LIMIT_INVOICES: int = 3
    EMAG_RATE_LIMIT_OTHER: int = 3

    # eMAG API Timeouts
    EMAG_REQUEST_TIMEOUT: int = 30
    EMAG_CONNECT_TIMEOUT: int = 10
    EMAG_READ_TIMEOUT: int = 30

    # Metrics and monitoring settings
    METRICS_PATH: str = "/metrics"
    METRICS_PORT: int = 8001
    PROMETHEUS_MULTIPROC_DIR: str = "/tmp/prometheus"

    # Health check settings
    HEALTH_CHECK_PATHS: str = "/health,/health/,/api/v1/health"

    # Rate limiting settings
    RATE_LIMIT_PER_WINDOW: int = 100  # Number of requests allowed per window
    RATE_LIMIT_WINDOW: int = 60  # Window size in seconds (1 minute)
    RATE_LIMIT_ADMIN_LIMIT: int = 120  # Admin endpoints allowed per window
    RATE_LIMIT_ADMIN_WINDOW: int = 60  # Window size for admin rate limiting

    # Security settings
    SECRET_KEY: str = "change_me_secure"
    REFRESH_SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 7  # Access tokens default 15 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # Refresh tokens default 7 days
    JWT_KEY_EXPIRE_DAYS: int = 30  # JWT keys expire after 30 days

    # Additional settings for tests
    ALLOWED_HOSTS: List[str] = ["*"]
    REQUEST_ID_HEADER: str = "X-Request-ID"
    GENERATE_REQUEST_ID_IF_NOT_IN_HEADER: bool = True

    # JWT Authentication (lowercase aliases expected by tests)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    secret_key: str = "your-super-secure-secret-key-change-this-in-production-2025"
    jwt_issuer: str = "magflow-service"
    jwt_audience: str = "magflow-api"
    jwt_supported_algorithms: List[str] = ["HS256", "RS256", "EDDSA"]
    jwt_keyset_dir: str = "jwt-keys"
    jwt_rotate_days: float = 7.0
    jwt_key_expire_days: float = 30.0

    # JWT Authentication settings (uppercase for compatibility)
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 7
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_SECRET_KEY: str = "your-super-secure-secret-key-change-this-in-production-2025"
    JWT_ISSUER: str = "magflow-service"
    JWT_AUDIENCE: str = "magflow-api"
    JWT_LEEWAY: int = 60
    JWT_MAX_ACTIVE_KEYS: int = 2
    JWKS_CACHE_MAX_AGE: int = 3600
    JWT_SUPPORTED_ALGORITHMS: List[str] = ["HS256", "RS256", "EDDSA"]
    JWT_KEYSET_DIR: str = "jwt-keys"
    AUDIT_LOG_FILE: str = "logs/audit.log"
    AUDIT_LOG_LEVEL: str = "INFO"

    # JWKS / OIDC settings (safe defaults to avoid AttributeError in health checks)
    JWKS_URL: str = "http://localhost/.well-known/jwks.json"
    JWKS_TIMEOUT: float = 2.0
    JWKS_MIN_KEYS: int = 1

    def validate_configuration(self) -> None:
        """Validate configuration settings at startup."""
        errors = []

        # Validate required settings
        required_settings = {
            "SECRET_KEY": self.SECRET_KEY,
            "DB_NAME": self.DB_NAME,
            "DB_USER": self.DB_USER,
        }
        # DB_HOST is optional; validation does not enforce it.


        for setting_name, setting_value in required_settings.items():
            if not setting_value or setting_value in [
                "change-this-in-production",
                "change_me_secure",
            ]:
                errors.append(
                    f"Required setting {setting_name} is not properly configured",
                )

        # Validate database connection settings
        if self.APP_ENV == "production":
            if self.DB_HOST in ["localhost", "127.0.0.1"]:
                errors.append(
                    "Production environment should not use localhost for database",
                )

            if not self.DB_PASS or len(self.DB_PASS) < 8:
                errors.append(
                    "Production database password should be at least 8 characters",
                )

        # Validate JWT settings
        if self.SECRET_KEY == "change_me_secure":
            errors.append("JWT secret key must be changed from default value")

        # Validate CORS settings
        if self.APP_ENV == "production" and "*" in self.CORS_ORIGINS:
            errors.append("Production environment should not allow all CORS origins")

        # Validate Redis settings
        if self.REDIS_ENABLED and not self.REDIS_HOST:
            errors.append("Redis is enabled but no Redis host configured")

        if errors:
            error_message = f"Configuration validation failed: {'; '.join(errors)}"
            logger.error(error_message)
            raise ConfigurationError(
                error_message,
                details={"validation_errors": errors},
            )

        logger.info("Configuration validation passed successfully")

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",  # Allow extra fields in environment
    )

    @property
    def db_pool_size(self) -> int:
        return self.DB_POOL_SIZE

    @property
    def db_max_overflow(self) -> int:
        return self.DB_MAX_OVERFLOW

    @property
    def db_pool_timeout(self) -> int:
        return self.DB_POOL_TIMEOUT

    @property
    def db_pool_recycle(self) -> int:
        return self.DB_POOL_RECYCLE

    @property
    def db_pool_pre_ping(self) -> bool:
        return self.DB_POOL_PRE_PING

    @property
    def db_command_timeout(self) -> int:
        return self.DB_COMMAND_TIMEOUT

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into a list of origins."""
        return [
            origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()
        ]

    @property
    def backend_cors_origins_list(self) -> List[str]:
        """Parse BACKEND_CORS_ORIGINS string into a list of origins."""
        return [
            origin.strip()
            for origin in self.BACKEND_CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    def get_cors_config(self, env: Optional[str] = None) -> Dict[str, Any]:
        """Get CORS configuration for the specified environment.

        Args:
            env: Environment name (defaults to current APP_ENV)

        Returns:
            Dict containing CORS configuration

        """
        env = env or self.APP_ENV.lower()
        return self.CORS_CONFIG.get(env, self.CORS_CONFIG["development"])

    @property
    def health_check_paths(self) -> Set[str]:
        """Get health check paths as a set."""
        return {path.strip() for path in self.HEALTH_CHECK_PATHS.split(",")}

    @property
    def skip_paths(self) -> Set[str]:
        """Get paths that should be excluded from request logging."""
        # Parse health check paths directly to avoid circular dependency
        health_paths = {path.strip() for path in self.HEALTH_CHECK_PATHS.split(",")}
        return {
            self.METRICS_PATH,
            "/favicon.ico",
            *health_paths,
        }

    @property
    def rate_limit_per_window(self) -> int:
        return self.RATE_LIMIT_PER_WINDOW

    @property
    def rate_limit_window(self) -> int:
        return self.RATE_LIMIT_WINDOW


@lru_cache
def get_settings() -> Settings:
    """Get application settings, cached for performance.

    Returns:
        Settings: The application settings

    """
    settings = Settings()
    settings.validate_configuration()
    return settings


# Create settings instance
settings = get_settings()
