"""Test utilities for MagFlow ERP."""
import os
import random
import string
from typing import Any, Dict, Optional
from datetime import datetime, timezone


def random_string(length: int = 10) -> str:
    """Generate a random string of fixed length."""
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for _ in range(length))


def random_email() -> str:
    """Generate a random email address."""
    return f"{random_string(8).lower()}@example.com"


def create_test_user_data(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create test user data with sensible defaults."""
    data = {
        "email": random_email(),
        "username": f"user_{random_string(8)}",
        "password": "testpassword123!",
        "full_name": f"Test User {random_string(5)}",
        "is_active": True,
        "is_superuser": False,
    }
    if overrides:
        data.update(overrides)
    return data


def create_test_product_data(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create test product data with sensible defaults."""
    data = {
        "name": f"Test Product {random_string(5)}",
        "description": f"Description for test product {random_string(10)}",
        "price": round(random.uniform(1.0, 1000.0), 2),
        "quantity": random.randint(1, 1000),
        "created_at": datetime.now(timezone.utc),
    }
    if overrides:
        data.update(overrides)
    return data


def get_test_db_url() -> str:
    """Get the test database URL from environment or use default."""
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://app:app_password@localhost:5432/magflow_test"
    )


def skip_if_ci():
    """Skip a test if running in CI environment."""
    return os.environ.get("CI") is not None
