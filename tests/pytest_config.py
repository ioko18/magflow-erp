"""Pytest configuration for MagFlow ERP."""

import os

import pytest


def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "security: marks tests as security tests")
    config.addinivalue_line("markers", "performance: marks tests as performance tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "database: marks tests as database tests")
    config.addinivalue_line("markers", "api: marks tests as API tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add markers based on test file or class names
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
        elif "security" in str(item.fspath):
            item.add_marker(pytest.mark.security)
        elif "api" in str(item.fspath):
            item.add_marker(pytest.mark.api)
        elif "database" in str(item.fspath):
            item.add_marker(pytest.mark.database)

        # Add slow marker for tests that might be slow
        if "slow" in item.nodeid or "performance" in item.nodeid:
            item.add_marker(pytest.mark.slow)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    # Set test-specific environment variables
    os.environ.setdefault("APP_ENV", "testing")
    os.environ.setdefault("DEBUG", "true")
    os.environ.setdefault("TESTING", "true")

    yield

    # Cleanup after tests
    os.environ.pop("APP_ENV", None)
    os.environ.pop("DEBUG", None)
    os.environ.pop("TESTING", None)


@pytest.fixture
def sample_user_data():
    """Provide sample user data for tests."""
    return {
        "email": "test@example.com",
        "full_name": "Test User",
        "password": "testpass123",
        "is_active": True,
        "is_superuser": False,
    }


@pytest.fixture
def sample_product_data():
    """Provide sample product data for tests."""
    return {
        "name": "Test Product",
        "sku": "TEST-001",
        "description": "Test product description",
        "price": 99.99,
        "stock_quantity": 100,
        "is_active": True,
    }


@pytest.fixture
def api_headers():
    """Provide common API headers for tests."""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


@pytest.fixture
def auth_headers(api_headers):
    """Provide authenticated API headers for tests."""
    return {
        **api_headers,
        "Authorization": "Bearer test_token",
    }


# Test configuration
test_config = {
    "testpaths": ["tests"],
    "python_files": ["test_*.py", "*_test.py"],
    "python_classes": ["Test*"],
    "python_functions": ["test_*"],
    "addopts": [
        "-v",
        "--tb=short",
        "--strict-markers",
        "--disable-warnings",
        "--cov=app",
        "--cov-report=term-missing",
        "--cov-report=html",
        "--cov-fail-under=80",
    ],
    "filterwarnings": [
        "error",
        "ignore::DeprecationWarning",
        "ignore::PendingDeprecationWarning",
    ],
    "markers": {
        "slow": "marks tests as slow (deselect with '-m \"not slow\"')",
        "integration": "marks tests as integration tests",
        "security": "marks tests as security tests",
        "performance": "marks tests as performance tests",
        "unit": "marks tests as unit tests",
        "database": "marks tests as database tests",
        "api": "marks tests as API tests",
    },
    "norecursedirs": [
        ".git",
        "__pycache__",
        "node_modules",
        ".pytest_cache",
        "build",
        "dist",
        "*.egg-info",
    ],
}


# Add custom command line options
def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="run slow tests",
    )
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="run integration tests",
    )
    parser.addoption(
        "--security",
        action="store_true",
        default=False,
        help="run security tests",
    )


def pytest_cmdline_main(config):
    """Process command line options."""
    if config.getoption("--runslow"):
        # Add slow marker to run slow tests
        config.option.markexpr = config.option.markexpr + " or slow"
    if config.getoption("--integration"):
        config.option.markexpr = config.option.markexpr + " or integration"
    if config.getoption("--security"):
        config.option.markexpr = config.option.markexpr + " or security"
