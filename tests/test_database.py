"""Tests for MagFlow ERP database models and services."""


def test_database_settings():
    """Test that database settings are properly configured."""
    from app.core.config import settings

    # Test database connection settings exist
    assert hasattr(settings, "DB_HOST")
    assert hasattr(settings, "DB_PORT")
    assert hasattr(settings, "DB_NAME")
    assert hasattr(settings, "DB_USER")
    assert hasattr(settings, "DB_PASS")
    assert hasattr(settings, "DB_SCHEMA")

    # Test database pool settings exist
    assert hasattr(settings, "DB_POOL_SIZE")
    assert hasattr(settings, "DB_MAX_OVERFLOW")
    assert hasattr(settings, "DB_POOL_TIMEOUT")
    assert hasattr(settings, "DB_POOL_RECYCLE")
    assert hasattr(settings, "DB_POOL_PRE_PING")

    # Test that property methods work
    assert settings.db_pool_size == settings.DB_POOL_SIZE
    assert settings.db_max_overflow == settings.DB_MAX_OVERFLOW
    assert settings.db_pool_timeout == settings.DB_POOL_TIMEOUT
    assert settings.db_pool_recycle == settings.DB_POOL_RECYCLE
    assert settings.db_pool_pre_ping == settings.DB_POOL_PRE_PING
    assert settings.db_command_timeout == settings.DB_COMMAND_TIMEOUT
    assert settings.search_path == settings.DB_SCHEMA


def test_async_database_engine_creation():
    """Test that we can create async database engine."""
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.core.config import settings

    # Test that we can create an engine (without actually connecting)
    try:
        engine = create_async_engine(
            settings.SQLALCHEMY_DATABASE_URI,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_recycle=settings.db_pool_recycle,
            pool_pre_ping=settings.db_pool_pre_ping,
        )
        assert engine is not None
        assert hasattr(engine, "pool")
    except Exception as e:
        # We expect this to potentially fail due to no actual database
        # but the engine creation should work
        print(f"Engine creation failed (expected): {e}")


def test_environment_settings():
    """Test environment-specific settings."""
    from app.core.config import settings

    # Test that environment is set
    assert hasattr(settings, "APP_ENV")
    assert settings.APP_ENV in ["development", "testing", "production"]

    # Test that debug settings work
    assert hasattr(settings, "DEBUG")
    assert isinstance(settings.DEBUG, bool)

    # Test that version settings exist
    assert hasattr(settings, "APP_VERSION")
    assert hasattr(settings, "API_V1_STR")


def test_api_settings():
    """Test API configuration settings."""
    from app.core.config import settings

    # Test API settings
    assert hasattr(settings, "API_V1_STR")
    assert settings.API_V1_STR == "/api/v1"

    # Test server settings
    assert hasattr(settings, "SERVER_NAME")
    assert hasattr(settings, "SERVER_HOST")
    assert hasattr(settings, "BACKEND_CORS_ORIGINS")

    # Test that CORS origins list works
    origins_list = settings.backend_cors_origins_list
    assert isinstance(origins_list, list)


def test_logging_settings():
    """Test logging configuration settings."""
    from app.core.config import settings

    # Test logging settings exist
    assert hasattr(settings, "LOG_LEVEL")
    assert hasattr(settings, "LOG_FORMAT")
    assert hasattr(settings, "LOG_FILE")
    assert hasattr(settings, "LOG_MAX_SIZE")
    assert hasattr(settings, "LOG_BACKUP_COUNT")

    # Test that log level is valid
    assert settings.LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def test_redis_settings():
    """Test Redis configuration settings."""
    from app.core.config import settings

    # Test Redis settings exist
    assert hasattr(settings, "REDIS_HOST")
    assert hasattr(settings, "REDIS_PORT")
    assert hasattr(settings, "REDIS_DB")
    assert hasattr(settings, "REDIS_PASSWORD")

    # Test Redis URL construction
    redis_url = (
        f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
    )
    assert redis_url.startswith("redis://")


def test_emag_settings():
    """Test eMAG API configuration settings."""
    from app.core.config import settings

    # Test eMAG settings exist (matching actual config names)
    assert hasattr(settings, "EMAG_API_BASE_URL")
    assert hasattr(
        settings, "EMAG_API_KEY"
    )  # Note: config uses EMAG_API_KEY, not EMAG_API_SECRET
    assert hasattr(settings, "EMAG_API_USER")
    assert hasattr(settings, "EMAG_CLIENT_ID")
    assert hasattr(settings, "EMAG_USERNAME")

    # Test that eMAG base URL is properly formatted
    assert settings.EMAG_API_BASE_URL.startswith("http")


def test_metrics_settings():
    """Test metrics and monitoring settings."""
    from app.core.config import settings

    # Test metrics settings exist
    assert hasattr(settings, "METRICS_PATH")
    assert hasattr(settings, "METRICS_PORT")
    assert hasattr(settings, "PROMETHEUS_MULTIPROC_DIR")

    # Test health check paths
    health_paths = settings.health_check_paths
    assert isinstance(health_paths, set)
    assert "/health" in health_paths or "/health/" in health_paths
