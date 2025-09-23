"""Simple test to verify basic functionality."""


def test_simple_math():
    """Test basic math operations."""
    assert 1 + 1 == 2
    assert 2 * 3 == 6
    assert 10 / 2 == 5


def test_settings_import():
    """Test that we can import settings."""
    from app.core.config import settings

    assert settings is not None
    assert hasattr(settings, "APP_NAME")
    assert settings.APP_NAME == "magflow"


def test_settings_properties():
    """Test that settings properties work."""
    from app.core.config import settings

    # Test that the database pool properties exist
    assert hasattr(settings, "db_pool_size")
    assert hasattr(settings, "db_max_overflow")
    assert hasattr(settings, "db_pool_timeout")
    assert hasattr(settings, "db_pool_recycle")
    assert hasattr(settings, "db_pool_pre_ping")
    assert hasattr(settings, "db_command_timeout")

    # Test that the properties return correct values
    assert settings.db_pool_size == settings.DB_POOL_SIZE
    assert settings.db_max_overflow == settings.DB_MAX_OVERFLOW
    assert settings.db_pool_timeout == settings.DB_POOL_TIMEOUT
