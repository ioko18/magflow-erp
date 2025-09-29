"""Test configuration module."""

from .test_config import (
    TEST_DB_HOST,
    TEST_DB_PORT,
    TEST_DB_USER,
    TEST_DB_PASSWORD,
    TEST_DB_NAME,
    TEST_DB_SCHEMA,
    TEST_DB_URL,
    TEST_APP_ENV,
    TEST_APP_DEBUG,
    TEST_APP_PORT,
    TEST_APP_SECRET,
)


# Create a test_config object with all the configuration values
class TestConfig:
    """Test configuration object."""

    TEST_DB_HOST = TEST_DB_HOST
    TEST_DB_PORT = TEST_DB_PORT
    TEST_DB_USER = TEST_DB_USER
    TEST_DB_PASSWORD = TEST_DB_PASSWORD
    TEST_DB_NAME = TEST_DB_NAME
    TEST_DB_SCHEMA = TEST_DB_SCHEMA
    TEST_DB_URL = TEST_DB_URL
    TEST_APP_ENV = TEST_APP_ENV
    TEST_APP_DEBUG = TEST_APP_DEBUG
    TEST_APP_PORT = TEST_APP_PORT
    TEST_APP_SECRET = TEST_APP_SECRET


test_config = TestConfig()
