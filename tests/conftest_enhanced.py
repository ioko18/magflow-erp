"""Enhanced test configuration with fixtures and utilities."""

from typing import Any, Dict

import pytest
from httpx import AsyncClient


@pytest.fixture
async def test_app():
    """Create a test FastAPI application."""
    from tests.conftest import app

    return app


@pytest.fixture
async def test_client(test_app):
    """Create a test HTTP client."""
    async with AsyncClient(app=test_app, base_url="http://testserver") as client:
        yield client


@pytest.fixture
async def authenticated_client(test_client):
    """Create an authenticated test client."""
    # Create test user and get token
    # This would integrate with your auth system
    return test_client


@pytest.fixture
def test_db_session():
    """Create a test database session."""
    # Setup test database
    # This would integrate with your database testing setup


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


class TestDataFactory:
    """Factory for creating test data."""

    @staticmethod
    def create_user(overrides: Dict[str, Any] = None):
        """Create test user data."""
        base_data = {
            "email": "user@example.com",
            "full_name": "Test User",
            "password": "password123",
            "is_active": True,
        }
        if overrides:
            base_data.update(overrides)
        return base_data

    @staticmethod
    def create_product(overrides: Dict[str, Any] = None):
        """Create test product data."""
        base_data = {
            "name": "Test Product",
            "sku": "TEST-001",
            "price": 99.99,
            "stock_quantity": 50,
            "is_active": True,
        }
        if overrides:
            base_data.update(overrides)
        return base_data

    @staticmethod
    def create_order(overrides: Dict[str, Any] = None):
        """Create test order data."""
        base_data = {
            "customer_id": 1,
            "order_lines": [
                {
                    "product_id": 1,
                    "quantity": 2,
                    "unit_price": 50.0,
                },
            ],
        }
        if overrides:
            base_data.update(overrides)
        return base_data
