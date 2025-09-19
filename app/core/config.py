"""
Application configuration settings.

This module contains all configuration settings for the application,
loaded from environment variables with sensible defaults.
"""

from functools import lru_cache
from typing import Any, Dict, List, Optional, Set
from pydantic import computed_field

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application settings
    APP_ENV: str = "development"
    ENVIRONMENT: str = "development"  # Alias for APP_ENV for compatibility
    APP_NAME: str = "MagFlow ERP"
    SERVICE_NAME: str = "magflow-service"  # Used for logging, metrics, and service identification
    PROJECT_NAME: str = "MagFlow ERP"  # Used for OpenAPI documentation and other places where the project name is needed
    APP_PORT: int = 8000
    APP_DEBUG: bool = True
    DEBUG: bool = True  # Alias for APP_DEBUG for compatibility
    SQL_ECHO: bool = False
    TESTING: bool = False  # Flag to indicate if the application is running in test mode
    DOCS_ENABLED: bool = True  # Control FastAPI documentation visibility
    APP_SECRET: str = "change-this-in-production"
    APP_VERSION: str = "1.0.0"
    
    # Database settings
    DB_USER: str = "postgres"
    DB_PASS: str = "postgres"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "magflow"
    DB_SCHEMA: str = "public"
    
    # Connection pool settings
    DB_POOL_SIZE: int = 20  # Default pool size
    DB_MAX_OVERFLOW: int = 10  # Default max overflow
    DB_POOL_TIMEOUT: int = 30  # seconds
    DB_POOL_RECYCLE: int = 3600  # 1 hour
    DB_POOL_PRE_PING: bool = True
    DB_POOL_USE_LIFO: bool = True
    DB_COMMAND_TIMEOUT: int = 30  # seconds
    
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
        """Construct Redis URL from individual components."""
        auth_part = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        scheme = "rediss" if self.REDIS_SSL else "redis"
        return f"{scheme}://{auth_part}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # Database URI
    @computed_field
    @property
    def DB_URI(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # Alembic URL
    @computed_field
    @property
    def alembic_url(self) -> str:
        return self.DB_URI.replace("asyncpg", "psycopg2")
    
    # Cache settings
    CACHE_ENABLED: bool = True
    CACHE_DEFAULT_TTL: int = 3600  # 1 hour in seconds
    
    # Rate limiting settings
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/minute"  # Default rate limit (requests per minute)
    RATE_LIMIT_STORAGE_URI: str = "redis://localhost:6379/0"  # Redis URL for rate limiting storage
    
    # eMAG API settings
    EMAG_API_BASE_URL: str = "https://marketplace.emag.ro/api"
    EMAG_API_USER: str = ""  # Should be set via environment variables
    EMAG_API_KEY: str = ""  # Should be set via environment variables
    EMAG_API_TIMEOUT: int = 30  # seconds
    EMAG_MAX_RETRIES: int = 3
    EMAG_RETRY_DELAY: int = 1  # second
    EMAG_RATE_LIMIT: int = 10  # requests per second
    EMAG_CACHE_TTL: int = 86400  # 24 hours in seconds
    
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
    
    # CORS Configuration
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
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
    LOG_COMPRESSION: str = "zip"
    LOG_JSON_INDENT: Optional[int] = None
    
    # Error handling settings
    ERROR_INCLUDE_TRACEBACK: bool = False
    ERROR_SHOW_DETAILS: bool = True
    ERROR_RESPONSE_FORMAT: str = "json"  # or 'text'
    
    # OpenTelemetry settings
    OTLP_ENABLED: bool = False
    OTLP_ENDPOINT: str = "otel-collector:4317"  # Default to local collector
    OTLP_INSECURE: bool = True  # Set to False in production with proper TLS
    
    # Environment-based CORS settings
    CORS_CONFIG: Dict[str, Dict[str, Any]] = {
        "development": {
            "allow_origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
            "allow_credentials": True,
            "max_age": 600  # 10 minutes
        },
        "production": {
            "allow_origins": ["https://your-production-domain.com"],
            "allow_credentials": True,
            "max_age": 86400  # 24 hours
        },
        "testing": {
            "allow_origins": ["*"],
            "allow_credentials": False,
            "max_age": 0
        }
    }

    # Security headers
    SECURITY_HEADERS: dict = {
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Content-Security-Policy": "default-src 'self'"
    }

    # Rate limiting settings
    RATE_LIMIT_PER_WINDOW: int = 100  # Number of requests allowed per window
    RATE_LIMIT_WINDOW: int = 60  # Window size in seconds (1 minute)
    
    # Security settings
    SECRET_KEY: str = "your-secret-key-here"
    REFRESH_SECRET_KEY: str = "your-secret-key-here"  # Defaults to same as SECRET_KEY for tests
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Access tokens default 15 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # Refresh tokens default 7 days
    
    # Allowed hosts for security middleware
    ALLOWED_HOSTS: List[str] = ["*"]  # Allow all hosts in development

    # Request ID settings
    REQUEST_ID_HEADER: str = "X-Request-ID"
    GENERATE_REQUEST_ID_IF_NOT_IN_HEADER: bool = True

    # JWT Authentication (UPPERCASE canonical fields)
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_SECRET_KEY: str = "change-this-to-a-secure-secret"
    JWT_ISSUER: str = "magflow-service"
    JWT_AUDIENCE: str = "magflow-api"
    JWT_LEEWAY: int = 60
    JWT_KEY_EXPIRE_DAYS: int = 30
    JWT_ROTATE_DAYS: int = 7
    JWT_MAX_ACTIVE_KEYS: int = 2
    JWKS_CACHE_MAX_AGE: int = 3600
    JWT_KEYSET_DIR: str = "jwt-keys"  # Directory to store JWT key pairs

    # JWT Authentication (lowercase aliases expected by tests)
    # Note: These are convenience mirrors to support tests mutating attributes.
    # The application code should continue to rely on the UPPERCASE fields.
    jwt_algorithm: str = "RS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    secret_key: str = "change-this-to-a-secure-secret"
    jwt_issuer: str = "magflow-service"
    jwt_audience: str = "magflow-api"
    jwt_supported_algorithms: List[str] = ["HS256", "RS256"]
    jwt_keyset_dir: str = "jwt-keys"

    # Compatibility flags
    ENABLE_OTEL: bool = False  # Back-compat flag used in some modules

    class Config:
        env_file = ".env"
    
    @property
    def db_pool_size(self) -> int:
        return self.DB_POOL_SIZE
        
    @property
    def db_max_overflow(self) -> int:
        return self.DB_MAX_OVERFLOW
        
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into a list of origins."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def backend_cors_origins_list(self) -> List[str]:
        """Parse BACKEND_CORS_ORIGINS string into a list of origins."""
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]
        
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
        return {
            self.METRICS_PATH,
            "/favicon.ico",
            *self.health_check_paths,
        }


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings, cached for performance.

    Returns:
        Settings: The application settings
    """
    return Settings()


# Create settings instance
settings = get_settings()
