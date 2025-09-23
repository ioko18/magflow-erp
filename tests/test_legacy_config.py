"""Tests for MagFlow ERP configuration settings."""


def test_rate_limiting_settings():
    """Test rate limiting configuration settings."""
    from app.core.config import settings

    # Test rate limiting defaults using property methods
    assert settings.rate_limit_per_window == 100
    assert settings.rate_limit_window == 60

    # Test that properties exist
    assert hasattr(settings, "rate_limit_per_window")
    assert hasattr(settings, "rate_limit_window")

    # Test lowercase property access (for tests)
    assert settings.rate_limit_per_window == 100
    assert settings.rate_limit_window == 60


def test_jwt_settings():
    """Test JWT configuration settings."""
    from app.core.config import settings

    # Test JWT defaults
    assert settings.JWT_ALGORITHM == "RS256"
    assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 15
    assert settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS == 7
    assert (
        settings.JWT_SECRET_KEY
        == "your-super-secure-secret-key-change-this-in-production-2025"
    )
    assert settings.JWT_ISSUER == "magflow-service"
    assert settings.JWT_AUDIENCE == "magflow-api"
    assert settings.JWT_LEEWAY == 60
    assert settings.JWT_KEY_EXPIRE_DAYS == 30
    assert settings.JWT_MAX_ACTIVE_KEYS == 2
    assert settings.JWKS_CACHE_MAX_AGE == 3600
    assert settings.JWT_KEYSET_DIR == "jwt-keys"

    # Test lowercase aliases for tests
    assert settings.jwt_algorithm == "RS256"
    assert settings.access_token_expire_minutes == 15
    assert settings.refresh_token_expire_days == 7
    assert (
        settings.secret_key
        == "your-super-secure-secret-key-change-this-in-production-2025"
    )
    assert settings.jwt_issuer == "magflow-service"
    assert settings.jwt_audience == "magflow-api"
    assert settings.jwt_supported_algorithms == ["HS256", "RS256"]
    assert settings.jwt_keyset_dir == "jwt-keys"


def test_security_settings():
    """Test security configuration settings."""
    from app.core.config import settings

    # Test security defaults - check actual values
    assert (
        settings.SECRET_KEY
        == "your-super-secure-secret-key-change-this-in-production-2025"
    )
    assert (
        settings.REFRESH_SECRET_KEY == "your-secret-key-here"
    )  # REFRESH_SECRET_KEY has different default
    assert settings.ALGORITHM == "RS256"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 7
    assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7
    assert settings.ALLOWED_HOSTS == ["*"]

    # Test request ID settings
    assert settings.REQUEST_ID_HEADER == "X-Request-ID"
    assert settings.GENERATE_REQUEST_ID_IF_NOT_IN_HEADER is True


def test_cors_settings():
    """Test CORS configuration settings."""
    from app.core.config import settings

    # Test CORS configuration structure
    assert isinstance(settings.CORS_CONFIG, dict)
    assert "development" in settings.CORS_CONFIG
    assert "production" in settings.CORS_CONFIG
    assert "testing" in settings.CORS_CONFIG

    # Test development CORS config
    dev_config = settings.CORS_CONFIG["development"]
    assert dev_config["allow_origins"] == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    assert dev_config["allow_credentials"] is True
    assert dev_config["max_age"] == 600

    # Test get_cors_config method
    dev_cors = settings.get_cors_config("development")
    assert dev_cors == dev_config


def test_security_headers():
    """Test security headers configuration."""
    from app.core.config import settings

    expected_headers = {
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Content-Security-Policy": "default-src 'self'",
    }

    assert expected_headers == settings.SECURITY_HEADERS


def test_missing_property_methods():
    """Test that we're not missing any property methods that tests expect."""
    from app.core.config import settings

    # Check for any missing lowercase properties that tests might expect
    test_attributes = [
        "rate_limit_per_window",
        "rate_limit_window",
        "search_path",
    ]

    for attr in test_attributes:
        assert hasattr(settings, attr), f"Missing property method: {attr}"

    # Verify the property methods return the correct values
    # Note: RATE_LIMIT_PER_WINDOW and RATE_LIMIT_WINDOW are constants, not attributes
    # The property methods should return the correct constant values
    assert settings.rate_limit_per_window == 100  # Expected default value
    assert settings.rate_limit_window == 60  # Expected default value
    assert settings.search_path == settings.DB_SCHEMA
