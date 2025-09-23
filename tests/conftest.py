"""
Simplified test configuration for MagFlow ERP.

This module provides mock-based fixtures to avoid SQLAlchemy model conflicts
during testing. Focus is on unit tests and integration tests with mocked dependencies.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import Any, Dict

import pytest
from unittest.mock import AsyncMock
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


@pytest.fixture
def performance_config():
    """Provide performance testing configuration."""
    return {
        "max_response_time": 1.0,  # seconds
        "concurrent_requests": 10,
        "timeout": 30.0,  # seconds
        "retry_attempts": 3,
        "retry_delay": 0.1,  # seconds
        "warmup_iterations": 5,
        "test_iterations": 10
    }


@pytest.fixture
def mock_catalog_service():
    """Create a mock catalog service for testing."""
    mock_service = AsyncMock()

    # Configure mock methods to return appropriate responses
    mock_service.list_products.return_value = {
        "data": [],
        "meta": {
            "total_items": 0,
            "total_pages": 0,
            "page": 1,
            "per_page": 20,
            "has_next": False,
            "has_prev": False,
            "next_cursor": None,
            "prev_cursor": None,
        }
    }

    mock_service.get_product_by_id.return_value = {
        "id": "test-uuid",
        "name": "Test Product",
        "description": "A test product",
        "sku": "TEST-001",
        "price": 99.99,
        "status": "active",
        "is_active": True,
        "stock_quantity": 10,
        "category_id": 1,
        "created_at": "2023-10-15T12:00:00Z",
        "updated_at": "2023-10-15T12:00:00Z",
    }

    mock_service.create_product.return_value = {
        "id": "test-uuid",
        "name": "New Product",
        "description": "A new product",
        "sku": "NEW-001",
        "price": 199.99,
        "status": "draft",
        "is_active": True,
        "stock_quantity": 0,
        "category_id": 1,
        "created_at": "2023-10-15T12:00:00Z",
        "updated_at": "2023-10-15T12:00:00Z",
    }

    mock_service.update_product.return_value = {
        "id": "test-uuid",
        "name": "Updated Product",
        "description": "A test product",
        "sku": "UPD-001",
        "price": 249.99,
        "status": "active",
        "is_active": True,
        "stock_quantity": 5,
        "category_id": 1,
        "created_at": "2023-10-15T12:00:00Z",
        "updated_at": "2023-10-15T13:00:00Z",
    }

    mock_service.delete_product.return_value = None

    mock_service.list_brands.return_value = {
        "data": [
            {
                "id": 1,
                "name": "Test Brand",
                "slug": "test-brand",
                "is_active": True,
                "created_at": "2023-10-15T12:00:00Z",
                "updated_at": "2023-10-15T12:00:00Z",
            }
        ],
        "meta": {
            "total_items": 1,
            "total_pages": 1,
            "page": 1,
            "per_page": 20,
            "has_next": False,
            "has_prev": False,
            "next_cursor": None,
            "prev_cursor": None,
        }
    }

    mock_service.get_brand_by_id.return_value = {
        "id": 1,
        "name": "Test Brand",
        "slug": "test-brand",
        "is_active": True,
        "created_at": "2023-10-15T12:00:00Z",
        "updated_at": "2023-10-15T12:00:00Z",
    }

    mock_service.list_characteristics.return_value = {
        "data": [
            {
                "id": 1,
                "name": "Color",
                "code": "color",
                "type": "select",
                "is_required": True,
                "is_filterable": True,
                "is_variant": True,
                "category_id": 1,
                "values": [
                    {
                        "id": 1,
                        "value": "Red",
                        "is_default": True,
                        "position": 0,
                    }
                ],
                "created_at": "2023-10-15T12:00:00Z",
                "updated_at": "2023-10-15T12:00:00Z",
            }
        ],
        "meta": {
            "total_items": 1,
            "total_pages": 1,
            "page": 1,
            "per_page": 20,
            "has_next": False,
            "has_prev": False,
            "next_cursor": None,
            "prev_cursor": None,
        }
    }

    mock_service.get_characteristic_values.return_value = [
        {
            "id": 1,
            "value": "Red",
            "is_default": True,
            "position": 0,
        },
        {
            "id": 2,
            "value": "Blue",
            "is_default": False,
            "position": 1,
        }
    ]

    return mock_service


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
