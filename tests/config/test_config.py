"""
Test configuration for MagFlow ERP tests.
"""
import os
import sys
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Database
_DEFAULT_DB_HOST = (
    os.getenv("LOCAL_DB_HOST")
    or os.getenv("DB_HOST")
    or os.getenv("POSTGRES_HOST")
    or "localhost"
)
_DEFAULT_DB_PORT = (
    os.getenv("LOCAL_DB_PORT")
    or os.getenv("DB_PORT")
    or os.getenv("POSTGRES_PORT")
    or "5432"
)
_DEFAULT_DB_USER = (
    os.getenv("LOCAL_DB_USER")
    or os.getenv("DB_USER")
    or os.getenv("POSTGRES_USER")
    or "magflow_dev"
)
_DEFAULT_DB_PASSWORD = (
    os.getenv("LOCAL_DB_PASSWORD")
    or os.getenv("DB_PASS")
    or os.getenv("POSTGRES_PASSWORD")
    or "dev_password"
)
_DEFAULT_DB_NAME = (
    os.getenv("LOCAL_DB_NAME")
    or os.getenv("DB_NAME")
    or os.getenv("POSTGRES_DB")
    or "magflow_dev"
)
_DEFAULT_DB_SCHEMA = os.getenv("DB_SCHEMA") or "app"

TEST_DB_HOST = os.getenv("TEST_DB_HOST", _DEFAULT_DB_HOST)
TEST_DB_PORT = int(os.getenv("TEST_DB_PORT", _DEFAULT_DB_PORT))
TEST_DB_USER = os.getenv("TEST_DB_USER", _DEFAULT_DB_USER)
TEST_DB_PASSWORD = os.getenv("TEST_DB_PASSWORD", _DEFAULT_DB_PASSWORD)
TEST_DB_NAME = os.getenv("TEST_DB_NAME", _DEFAULT_DB_NAME)
TEST_DB_SCHEMA = os.getenv("TEST_DB_SCHEMA", _DEFAULT_DB_SCHEMA)
TEST_DB_URL = os.getenv(
    "TEST_DB_URL",
    f"postgresql+asyncpg://{TEST_DB_USER}:{TEST_DB_PASSWORD}@{TEST_DB_HOST}:{TEST_DB_PORT}/{TEST_DB_NAME}",
)

# Application
TEST_APP_ENV = "testing"
TEST_APP_DEBUG = True
TEST_APP_PORT = 8001
TEST_APP_SECRET = "test-secret-key-1234567890"

# Paths
TEST_ROOT_DIR = PROJECT_ROOT / "tests"
TEST_DATA_DIR = TEST_ROOT_DIR / "test_data"
TEST_FIXTURES_DIR = TEST_ROOT_DIR / "fixtures"
TEST_REPORTS_DIR = TEST_ROOT_DIR / "reports"

# Ensure directories exist
for d in [TEST_DATA_DIR, TEST_FIXTURES_DIR, TEST_REPORTS_DIR]:
    d.mkdir(exist_ok=True, parents=True)

# Test data cleanup
TEST_TABLES_TO_CLEAN = [
    "users", "roles", "user_roles", "permissions",
    "role_permissions", "sessions"
]
TEST_FIXTURES_DIR.mkdir(exist_ok=True)
