"""Comprehensive tests for MagFlow ERP API and services."""


def test_api_endpoints_configuration():
    """Test API endpoint configuration."""
    from app.core.config import settings

    # Test API prefix and version settings
    assert settings.API_PREFIX == "/api/v1"
    assert settings.API_V1_STR == "/api/v1"

    # Test that API settings exist
    assert hasattr(settings, "DOCS_ENABLED")
    assert hasattr(settings, "OPENAPI_URL")
    assert hasattr(settings, "DOCS_URL")

    # Test API security settings
    assert hasattr(settings, "CORS_ALLOW_CREDENTIALS")
    assert hasattr(settings, "CORS_ALLOW_METHODS")
    assert hasattr(settings, "CORS_ALLOW_HEADERS")

    # Test OAuth2 settings
    assert hasattr(settings, "OAUTH2_ENABLED")
    assert hasattr(settings, "FRONTEND_URL")
    assert hasattr(settings, "CORS_MAX_AGE")


def test_error_handling_settings():
    """Test error handling configuration."""
    from app.core.config import settings

    # Test error response settings
    assert hasattr(settings, "ERROR_INCLUDE_TRACEBACK")
    assert hasattr(settings, "ERROR_SHOW_DETAILS")
    assert hasattr(settings, "ERROR_RESPONSE_FORMAT")

    # Test that error settings are properly configured
    assert isinstance(settings.ERROR_INCLUDE_TRACEBACK, bool)
    assert isinstance(settings.ERROR_SHOW_DETAILS, bool)
    assert settings.ERROR_RESPONSE_FORMAT in ["json", "text"]


def test_vault_settings():
    """Test Vault configuration settings."""
    from app.core.config import settings

    # Test Vault settings exist
    assert hasattr(settings, "VAULT_ENABLED")
    assert hasattr(settings, "VAULT_ADDR")
    assert hasattr(settings, "VAULT_ROLE")
    assert hasattr(settings, "VAULT_NAMESPACE")
    assert hasattr(settings, "VAULT_SECRET_PATH")
    assert hasattr(settings, "VAULT_KV_MOUNT")

    # Test Vault URL is properly formatted
    if settings.VAULT_ENABLED:
        assert settings.VAULT_ADDR.startswith("http")


def test_feature_flags():
    """Test feature flag configuration."""
    from app.core.config import settings

    # Test feature flags exist
    assert hasattr(settings, "EMAG_INTEGRATION_ENABLED")
    assert hasattr(settings, "OAUTH2_ENABLED")
    assert hasattr(settings, "ENABLE_OTEL")

    # Test that feature flags are boolean
    assert isinstance(settings.EMAG_INTEGRATION_ENABLED, bool)
    assert isinstance(settings.OAUTH2_ENABLED, bool)
    assert isinstance(settings.ENABLE_OTEL, bool)


def test_cache_settings():
    """Test caching configuration."""
    from app.core.config import settings

    # Test cache settings exist
    assert hasattr(settings, "CACHE_ENABLED")
    assert hasattr(settings, "CACHE_DEFAULT_TTL")

    # Test cache values are reasonable
    assert isinstance(settings.CACHE_ENABLED, bool)
    assert isinstance(settings.CACHE_DEFAULT_TTL, int)
    assert settings.CACHE_DEFAULT_TTL > 0


def test_rate_limiting_detailed():
    """Test detailed rate limiting configuration."""
    from app.core.config import settings

    # Test rate limiting settings
    assert hasattr(settings, "RATE_LIMIT_ENABLED")
    assert hasattr(settings, "RATE_LIMIT_DEFAULT")
    assert hasattr(settings, "RATE_LIMIT_STORAGE_URI")

    # Test that rate limiting is properly configured
    assert isinstance(settings.RATE_LIMIT_ENABLED, bool)
    assert settings.RATE_LIMIT_DEFAULT.endswith(
        "/minute"
    ) or settings.RATE_LIMIT_DEFAULT.endswith("/second")

    # Test Redis URL for rate limiting
    assert settings.RATE_LIMIT_STORAGE_URI.startswith("redis://")


def test_open_telemetry_settings():
    """Test OpenTelemetry configuration."""
    from app.core.config import settings

    # Test OpenTelemetry settings exist
    assert hasattr(settings, "OTLP_ENABLED")
    assert hasattr(settings, "OTLP_ENDPOINT")
    assert hasattr(settings, "OTLP_INSECURE")

    # Test OpenTelemetry values
    assert isinstance(settings.OTLP_ENABLED, bool)
    assert isinstance(settings.OTLP_INSECURE, bool)
    if settings.OTLP_ENABLED:
        assert settings.OTLP_ENDPOINT is not None


def test_cors_configuration_detailed():
    """Test detailed CORS configuration."""
    from app.core.config import settings

    # Test CORS config structure
    assert isinstance(settings.CORS_CONFIG, dict)
    assert "development" in settings.CORS_CONFIG
    assert "production" in settings.CORS_CONFIG
    assert "testing" in settings.CORS_CONFIG

    # Test development CORS settings
    dev_config = settings.CORS_CONFIG["development"]
    assert "allow_origins" in dev_config
    assert "allow_credentials" in dev_config
    assert "max_age" in dev_config

    # Test get_cors_config method
    cors_config = settings.get_cors_config("development")
    assert cors_config == dev_config

    # Test property methods
    origins_list = settings.cors_origins_list
    backend_origins = settings.backend_cors_origins_list
    assert isinstance(origins_list, list)
    assert isinstance(backend_origins, list)


def test_health_check_configuration():
    """Test health check configuration."""
    from app.core.config import settings

    # Test health check paths property
    health_paths = settings.health_check_paths
    assert isinstance(health_paths, set)
    assert len(health_paths) > 0

    # Test skip paths property
    skip_paths = settings.skip_paths
    assert isinstance(skip_paths, set)
    assert settings.METRICS_PATH in skip_paths
    assert "/favicon.ico" in skip_paths
    assert len(health_paths.intersection(skip_paths)) == len(health_paths)


def test_jwt_configuration_detailed():
    """Test detailed JWT configuration."""
    from app.core.config import settings

    # Test all JWT settings exist
    jwt_attrs = [
        "JWT_ALGORITHM",
        "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
        "JWT_REFRESH_TOKEN_EXPIRE_DAYS",
        "JWT_SECRET_KEY",
        "JWT_ISSUER",
        "JWT_AUDIENCE",
        "JWT_LEEWAY",
        "JWT_KEY_EXPIRE_DAYS",
        "JWT_ROTATE_DAYS",
        "JWT_MAX_ACTIVE_KEYS",
        "JWKS_CACHE_MAX_AGE",
        "JWT_KEYSET_DIR",
    ]

    for attr in jwt_attrs:
        assert hasattr(settings, attr), f"Missing JWT setting: {attr}"

    # Test JWT algorithm is valid
    assert settings.JWT_ALGORITHM in ["HS256", "RS256", "ES256"]

    # Test lowercase aliases exist
    assert hasattr(settings, "jwt_algorithm")
    assert hasattr(settings, "access_token_expire_minutes")
    assert hasattr(settings, "refresh_token_expire_days")
    assert hasattr(settings, "secret_key")

    # Test that aliases match uppercase versions
    assert settings.jwt_algorithm == settings.JWT_ALGORITHM
    assert (
        settings.access_token_expire_minutes == settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    assert settings.refresh_token_expire_days == settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
