"""Test data factory and fixtures for MagFlow ERP testing.

This module provides comprehensive test data generation utilities,
factory patterns, and enhanced fixtures for consistent testing.
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import factory
import pytest
from factory.fuzzy import FuzzyChoice, FuzzyDate, FuzzyInteger


class BaseFactory(factory.Factory):
    """Base factory class for all test data factories."""

    @classmethod
    def create_batch(cls, size: int, **kwargs) -> List:
        """Create a batch of objects with optional overrides."""
        return [cls(**kwargs) for _ in range(size)]


# User Test Data Factories
class UserFactory(BaseFactory):
    """Factory for generating user test data."""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: n)
    email = factory.LazyAttribute(lambda obj: f"user{obj.id}@example.com")
    full_name = factory.Faker("name")
    is_active = FuzzyChoice([True, False])
    is_superuser = FuzzyChoice([True, False])
    created_at = FuzzyDate(start_date=date(2023, 1, 1))
    updated_at = factory.LazyAttribute(lambda obj: obj.created_at)


class AuditLogFactory(BaseFactory):
    """Factory for generating audit log test data."""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: n)
    user_id = FuzzyInteger(1, 100)
    action = FuzzyChoice(
        [
            "login_success",
            "login_attempt",
            "create",
            "update",
            "delete",
            "view",
            "export",
            "import",
            "login_failed",
            "logout",
        ]
    )
    resource = FuzzyChoice(
        [
            "users",
            "products",
            "orders",
            "reports",
            "inventory",
            "settings",
            "auth",
            "dashboard",
            "api",
        ]
    )
    resource_id = factory.LazyAttribute(
        lambda obj: f"{obj.resource}:{factory.Faker('uuid4')}",
    )
    details = factory.LazyAttribute(
        lambda obj: {
            "ip_address": factory.Faker("ipv4"),
            "user_agent": factory.Faker("user_agent"),
            "metadata": {"test": True, "factory_generated": True},
        }
    )
    success = FuzzyChoice([True, False])
    timestamp = FuzzyDate(start_date=date(2024, 1, 1))


class ProductFactory(BaseFactory):
    """Factory for generating product test data."""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: n)
    name = factory.Faker("word")
    sku = factory.LazyAttribute(lambda obj: f"SKU-{obj.id:06d}")
    description = factory.Faker("text", max_nb_chars=200)
    price = FuzzyInteger(10, 1000)
    stock_quantity = FuzzyInteger(0, 1000)
    is_active = FuzzyChoice([True, False])
    category_id = FuzzyInteger(1, 10)
    created_at = FuzzyDate(start_date=date(2023, 1, 1))


class OrderFactory(BaseFactory):
    """Factory for generating order test data."""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: n)
    customer_id = FuzzyInteger(1, 100)
    order_date = FuzzyDate(start_date=date(2024, 1, 1))
    total_amount = FuzzyInteger(50, 5000)
    status = FuzzyChoice(["pending", "processing", "shipped", "delivered", "cancelled"])
    order_lines = factory.LazyAttribute(
        lambda obj: [
            {
                "product_id": factory.Faker("random_int")(min=1, max=100),
                "quantity": factory.Faker("random_int")(min=1, max=10),
                "unit_price": factory.Faker("random_int")(min=10, max=100),
            }
            for _ in range(factory.Faker("random_int")(min=1, max=5))
        ]
    )


class ReportFactory(BaseFactory):
    """Factory for generating report test data."""

    class Meta:
        model = dict

    id = factory.Faker("uuid4")
    title = factory.Faker("sentence", nb_words=3)
    description = factory.Faker("text", max_nb_chars=100)
    report_type = FuzzyChoice(
        [
            "sales_overview",
            "inventory_status",
            "user_activity",
            "financial_summary",
            "system_metrics",
        ]
    )
    date_range = factory.LazyAttribute(
        lambda obj: {
            "start_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "end_date": datetime.now().strftime("%Y-%m-%d"),
        }
    )
    filters = factory.LazyAttribute(
        lambda obj: {
            "category": factory.Faker("word"),
            "status": FuzzyChoice(["active", "inactive", "all"]),
        }
    )
    created_at = FuzzyDate(start_date=date(2024, 1, 1))


# Enhanced Test Fixtures
@pytest.fixture
def sample_user():
    """Provide a sample user for testing."""
    return UserFactory()


@pytest.fixture
def sample_users():
    """Provide multiple sample users for testing."""
    return UserFactory.create_batch(5)


@pytest.fixture
def sample_audit_log():
    """Provide a sample audit log entry."""
    return AuditLogFactory()


@pytest.fixture
def sample_audit_logs():
    """Provide multiple sample audit logs."""
    return AuditLogFactory.create_batch(10)


@pytest.fixture
def sample_product():
    """Provide a sample product."""
    return ProductFactory()


@pytest.fixture
def sample_products():
    """Provide multiple sample products."""
    return ProductFactory.create_batch(5)


@pytest.fixture
def sample_order():
    """Provide a sample order."""
    return OrderFactory()


@pytest.fixture
def sample_orders():
    """Provide multiple sample orders."""
    return OrderFactory.create_batch(3)


@pytest.fixture
def sample_report():
    """Provide a sample report configuration."""
    return ReportFactory()


@pytest.fixture
def mock_database_session():
    """Create a comprehensive mock database session."""
    mock_session = AsyncMock()

    # Configure execute to return mock results
    mock_result = AsyncMock()
    mock_result.scalar.return_value = 10
    mock_result.fetchall.return_value = [
        MagicMock(user_id=1, action="login_success", timestamp=datetime.now()),
        MagicMock(user_id=2, action="login_attempt", timestamp=datetime.now()),
    ]
    mock_result.fetchone.return_value = MagicMock(
        total_users=100,
        active_users=85,
    )

    mock_session.execute.return_value = mock_result
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()

    return mock_session


@pytest.fixture
def mock_cache_service():
    """Create a mock cache service."""
    mock_cache = AsyncMock()

    # Configure cache methods
    mock_cache.get = AsyncMock(return_value=None)  # Default to cache miss
    mock_cache.set = AsyncMock(return_value=True)
    mock_cache.delete = AsyncMock(return_value=1)
    mock_cache.delete_pattern = AsyncMock(return_value=5)
    mock_cache.clear = AsyncMock(return_value=True)

    return mock_cache


@pytest.fixture
def mock_reporting_service():
    """Create a mock reporting service."""
    mock_service = AsyncMock()

    # Configure service methods
    mock_service.get_available_reports = AsyncMock(
        return_value=[
            {"type": "sales_overview", "name": "Sales Overview", "category": "Sales"},
        ]
    )

    mock_service._generate_sales_overview = AsyncMock(
        return_value={
            "summary": {"total_records": 100, "key_metrics": {"total_orders": 100}},
            "charts": {"sales_trend": {"chart_type": "line", "data": []}},
            "raw_data": [],
        }
    )

    mock_service._generate_inventory_status = AsyncMock(
        return_value={
            "summary": {"total_records": 50, "key_metrics": {"total_products": 500}},
            "charts": {"stock_levels": {"chart_type": "bar", "data": []}},
            "raw_data": [],
        }
    )

    mock_service.export_report = AsyncMock(return_value=b'{"test": "data"}')

    return mock_service


# Test Data Generators
class TestDataGenerator:
    """Generate test data for various scenarios."""

    @staticmethod
    def generate_user_activity_data(days: int = 30) -> List[Dict[str, Any]]:
        """Generate user activity data for the specified number of days."""
        activities = []

        for day in range(days):
            current_date = date.today() - timedelta(days=day)

            # Generate login activities
            for hour in range(24):
                # Random activity count for this hour
                activity_count = max(1, (day * hour) % 10)

                for i in range(activity_count):
                    activities.append(
                        AuditLogFactory(
                            action=FuzzyChoice(["login_success", "login_attempt"]),
                            resource="auth",
                            timestamp=current_date,
                            details={
                                "ip_address": factory.Faker("ipv4"),
                                "user_agent": factory.Faker("user_agent"),
                            },
                        )
                    )

        return activities

    @staticmethod
    def generate_sales_data(months: int = 12) -> List[Dict[str, Any]]:
        """Generate sales data for the specified number of months."""
        sales_data = []

        for month in range(months):
            month_date = datetime.now().replace(month=month + 1, day=1)

            # Generate daily sales for this month
            for day in range(30):  # Approximate 30 days per month
                daily_orders = max(5, (month * day) % 50)
                daily_revenue = daily_orders * 100  # Average $100 per order

                sales_data.append(
                    {
                        "date": month_date.replace(day=day + 1).strftime("%Y-%m-%d"),
                        "orders": daily_orders,
                        "revenue": daily_revenue,
                    }
                )

        return sales_data

    @staticmethod
    def generate_inventory_movements(days: int = 30) -> List[Dict[str, Any]]:
        """Generate inventory movement data."""
        movements = []

        for day in range(days):
            current_date = date.today() - timedelta(days=day)

            # Generate stock movements
            movement_count = max(2, (day) % 15)

            for i in range(movement_count):
                movements.append(
                    {
                        "date": current_date.strftime("%Y-%m-%d"),
                        "product": f"Product {i % 10 + 1}",
                        "movement_type": FuzzyChoice(["in", "out", "adjustment"]),
                        "quantity": FuzzyInteger(1, 100),
                        "reason": FuzzyChoice(
                            ["Sale", "Purchase", "Return", "Adjustment"]
                        ),
                    }
                )

        return movements

    @staticmethod
    def generate_performance_metrics(hours: int = 24) -> List[Dict[str, Any]]:
        """Generate system performance metrics."""
        metrics = []

        for hour in range(hours):
            current_time = datetime.now() - timedelta(hours=hour)

            metrics.append(
                {
                    "timestamp": current_time.strftime("%Y-%m-%d %H:%M"),
                    "cpu_usage": FuzzyInteger(20, 90),
                    "memory_usage": FuzzyInteger(40, 85),
                    "disk_usage": FuzzyInteger(10, 70),
                    "response_time": FuzzyInteger(50, 500),  # milliseconds
                    "error_rate": FuzzyInteger(0, 5) / 100,  # 0-5% error rate
                }
            )

        return metrics


# Performance Test Data
@pytest.fixture
def performance_test_data():
    """Provide data for performance testing."""
    return {
        "users": UserFactory.create_batch(100),
        "audit_logs": AuditLogFactory.create_batch(500),
        "products": ProductFactory.create_batch(200),
        "orders": OrderFactory.create_batch(50),
        "reports": ReportFactory.create_batch(20),
    }


# Load Test Data
@pytest.fixture
def load_test_data():
    """Provide large datasets for load testing."""
    return {
        "large_user_set": UserFactory.create_batch(1000),
        "large_audit_set": AuditLogFactory.create_batch(5000),
        "large_product_set": ProductFactory.create_batch(2000),
    }


# Edge Case Test Data
@pytest.fixture
def edge_case_data():
    """Provide edge case data for boundary testing."""
    return {
        "empty_user": UserFactory(id=0, email="", full_name="", is_active=False),
        "invalid_email_user": UserFactory(email="invalid-email-format"),
        "zero_quantity_product": ProductFactory(stock_quantity=0, is_active=False),
        "negative_price_product": ProductFactory(price=-100),  # Invalid data
        "very_long_name_product": ProductFactory(
            name="A" * 1000,  # Very long product name
        ),
        "special_characters_order": OrderFactory(
            customer_id=999999,  # Large ID
            total_amount=999999,  # Large amount
        ),
    }


# Test Configuration
@pytest.fixture
def test_config():
    """Provide test configuration settings."""
    return {
        "database": {
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 10,
            "pool_recycle": 300,
        },
        "cache": {
            "default_ttl": 300,
            "max_ttl": 3600,
        },
        "security": {
            "rate_limit": 100,
            "rate_window": 60,
        },
        "testing": {
            "mock_external_services": True,
            "disable_auth": True,
            "fast_mode": True,
        },
    }


# Database Test Helpers
class DatabaseTestHelper:
    """Helper class for database testing operations."""

    @staticmethod
    async def create_test_user(session, user_data: Dict[str, Any]):
        """Create a test user in the database."""
        # This would be implemented with actual database operations

    @staticmethod
    async def create_test_audit_log(session, log_data: Dict[str, Any]):
        """Create a test audit log entry."""
        # This would be implemented with actual database operations

    @staticmethod
    async def cleanup_test_data(session, table_name: str):
        """Clean up test data from specified table."""
        # This would be implemented with actual database operations


# API Test Client Helper
class APITestClient:
    """Helper class for API testing operations."""

    def __init__(self, client):
        self.client = client

    async def authenticate_user(self, email: str, password: str):
        """Authenticate a user and return tokens."""
        response = await self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        if response.status_code == 200:
            data = response.json()
            return data["access_token"], data["refresh_token"]
        return None, None

    async def make_authenticated_request(
        self, method: str, url: str, token: str, **kwargs
    ):
        """Make an authenticated API request."""
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        return await self.client.request(method, url, headers=headers, **kwargs)

    async def create_test_report(self, report_type: str, filters: Dict = None):
        """Create a test report."""
        data = {"report_type": report_type}
        if filters:
            data["filters"] = filters

        return await self.client.post("/api/v1/reports/generate", json=data)
