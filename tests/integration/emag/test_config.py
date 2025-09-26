"""Tests for eMAG configuration."""

import os

import pytest

from app.integrations.emag.config import EmagAccountType, EmagEnvironment, EmagSettings


def test_emag_settings_loading():
    """Test loading eMAG settings from environment variables."""
    # Set up test environment variables
    os.environ["EMAG_ENV"] = "sandbox"
    os.environ["EMAG_RATE_LIMIT_ORDERS"] = "10"
    os.environ["EMAG_RATE_LIMIT_OTHER"] = "2"

    # Test MAIN account config
    os.environ["EMAG_MAIN_USERNAME"] = "test_main_user"
    os.environ["EMAG_MAIN_PASSWORD"] = "test_main_pass"
    os.environ["EMAG_MAIN_WAREHOUSE_ID"] = "1"
    os.environ["EMAG_MAIN_IP_WHITELIST_NAME"] = "test_main_whitelist"
    os.environ["EMAG_MAIN_CALLBACK_BASE"] = "https://test.com/emag/main"

    # Test FBE account config
    os.environ["EMAG_FBE_USERNAME"] = "test_fbe_user"
    os.environ["EMAG_FBE_PASSWORD"] = "test_fbe_pass"
    os.environ["EMAG_FBE_WAREHOUSE_ID"] = "2"
    os.environ["EMAG_FBE_IP_WHITELIST_NAME"] = "test_fbe_whitelist"
    os.environ["EMAG_FBE_CALLBACK_BASE"] = "https://test.com/emag/fbe"

    # Load settings
    settings = EmagSettings()

    # Test basic settings
    assert settings.env == EmagEnvironment.SANDBOX
    assert settings.rate_limit_orders == 10
    assert settings.rate_limit_other == 2

    # Test MAIN account config
    main_config = settings.get_account_config(EmagAccountType.MAIN)
    assert main_config.username == "test_main_user"
    assert main_config.warehouse_id == 1
    assert main_config.ip_whitelist_name == "test_main_whitelist"
    assert str(main_config.callback_base) == "https://test.com/emag/main"

    # Test FBE account config
    fbe_config = settings.get_account_config(EmagAccountType.FBE)
    assert fbe_config.username == "test_fbe_user"
    assert fbe_config.warehouse_id == 2
    assert fbe_config.ip_whitelist_name == "test_fbe_whitelist"
    assert str(fbe_config.callback_base) == "https://test.com/emag/fbe"


def test_emag_settings_defaults():
    """Test eMAG settings default values."""
    # Clear environment variables
    for key in os.environ:
        if key.startswith("EMAG_"):
            del os.environ[key]

    # Load settings with defaults
    settings = EmagSettings()

    # Test default values
    assert settings.env == EmagEnvironment.SANDBOX
    assert settings.rate_limit_orders == 12
    assert settings.rate_limit_other == 3
    assert settings.request_timeout == 30
    assert settings.connect_timeout == 10
    assert settings.max_retries == 3
    assert settings.retry_delay == 1.0
    assert settings.circuit_breaker_failures == 5
    assert settings.circuit_breaker_timeout == 60
    assert settings.log_level == "INFO"
    assert settings.log_format == "json"
    assert settings.metrics_enabled is True
    assert settings.tracing_enabled is True

    # Test account configs are None when not provided
    assert settings.main is None
    assert settings.fbe is None

    # Test getting non-existent account config raises ValueError
    with pytest.raises(ValueError):
        settings.get_account_config(EmagAccountType.MAIN)
    with pytest.raises(ValueError):
        settings.get_account_config(EmagAccountType.FBE)
