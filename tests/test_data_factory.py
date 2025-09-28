"""Test data factory and fixtures for MagFlow ERP testing.

This module provides comprehensive test data generation utilities,
factory patterns, and enhanced fixtures for consistent testing.
"""

from datetime import date, datetime
from typing import List
from unittest.mock import AsyncMock, MagicMock

import factory
import pytest
from factory.fuzzy import FuzzyChoice, FuzzyDate, FuzzyInteger, FuzzyFloat
import json

# Import actual models for database factories
try:
    from app.models.user import User
    from app.models.role import Role
    from app.models.permission import Permission
    from app.models.product import Product
    from app.models.category import Category
    from app.models.order import Order, OrderLine
    from app.models.purchase import Supplier
    from app.models.sales import Customer
    from app.models.inventory import Warehouse
    from app.models.audit_log import AuditLog
    DATABASE_MODELS_AVAILABLE = True
except ImportError:
    DATABASE_MODELS_AVAILABLE = False


class BaseFactory(factory.Factory):
    """Base factory class for all test data factories."""

    @classmethod
    def create_batch(cls, size: int, **kwargs) -> List:
        """Create a batch of objects with optional overrides."""
        return [cls(**kwargs) for _ in range(size)]


# Dictionary-based factories (for simple testing)
class UserDictFactory(BaseFactory):
    """Factory for generating user test data dictionaries."""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: n)
    email = factory.LazyAttribute(lambda obj: f"user{obj.id}@example.com")
    full_name = factory.Faker("name")
    is_active = FuzzyChoice([True, False])
    is_superuser = FuzzyChoice([True, False])
    created_at = FuzzyDate(start_date=date(2023, 1, 1))
    updated_at = factory.LazyAttribute(lambda obj: obj.created_at)


class AdminUserDictFactory(UserDictFactory):
    """Factory for generating admin user test data dictionaries."""

    is_superuser = True
    email = factory.LazyAttribute(lambda obj: f"admin{obj.id}@example.com")
    full_name = factory.Faker("name")


class ProductDictFactory(BaseFactory):
    """Factory for generating product test data dictionaries."""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: n)
    name = factory.Faker("word")
    sku = factory.LazyAttribute(lambda obj: f"SKU-{obj.id:06d}")
    description = factory.Faker("text", max_nb_chars=200)
    price = FuzzyFloat(10.0, 1000.0, precision=2)
    stock_quantity = FuzzyInteger(0, 1000)
    is_active = FuzzyChoice([True, False])
    category_id = FuzzyInteger(1, 10)
    created_at = FuzzyDate(start_date=date(2023, 1, 1))


class OrderDictFactory(BaseFactory):
    """Factory for generating order test data dictionaries."""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: n)
    customer_id = FuzzyInteger(1, 100)
    order_date = FuzzyDate(start_date=date(2024, 1, 1))
    total_amount = FuzzyFloat(50.0, 5000.0, precision=2)
    status = FuzzyChoice(["pending", "processing", "shipped", "delivered", "cancelled"])
    order_lines = factory.LazyAttribute(
        lambda obj: [
            {
                "product_id": factory.Faker("random_int")(min=1, max=100),
                "quantity": factory.Faker("random_int")(min=1, max=10),
                "unit_price": factory.Faker("random_float")(min=10, max=100),
            }
            for _ in range(factory.Faker("random_int")(min=1, max=5))
        ]
    )


# SQLAlchemy model factories (for database testing)
if DATABASE_MODELS_AVAILABLE:

    class UserFactory(BaseFactory):
        """Factory for creating User database instances."""

        class Meta:
            model = User

        id = factory.Sequence(lambda n: n)
        email = factory.Sequence(lambda n: f"user{n}@example.com")
        hashed_password = factory.Faker("password")
        full_name = factory.Faker("name")
        is_active = True
        is_superuser = False
        email_verified = True
        failed_login_attempts = 0
        created_at = factory.Faker("past_datetime", start_date="-30d")
        updated_at = factory.Faker("past_datetime", start_date="-1d")


    class AdminUserFactory(UserFactory):
        """Factory for creating admin User database instances."""

        is_superuser = True
        email = factory.Sequence(lambda n: f"admin{n}@example.com")
        full_name = factory.Faker("name")


    class RoleFactory(BaseFactory):
        """Factory for creating Role database instances."""

        class Meta:
            model = Role

        id = factory.Sequence(lambda n: n)
        name = factory.Sequence(lambda n: f"role_{n}")
        description = factory.Faker("sentence", nb_words=6)
        is_system_role = False
        created_at = factory.Faker("past_datetime", start_date="-30d")
        updated_at = factory.Faker("past_datetime", start_date="-1d")


    class PermissionFactory(BaseFactory):
        """Factory for creating Permission database instances."""

        class Meta:
            model = Permission

        id = factory.Sequence(lambda n: n)
        name = factory.Sequence(lambda n: f"permission_{n}")
        description = factory.Faker("sentence", nb_words=8)
        resource = FuzzyChoice(["users", "products", "orders", "categories", "reports"])
        action = FuzzyChoice(["read", "write", "delete", "execute", "admin"])
        created_at = factory.Faker("past_datetime", start_date="-30d")
        updated_at = factory.Faker("past_datetime", start_date="-1d")


    class CategoryFactory(BaseFactory):
        """Factory for creating Category database instances."""

        class Meta:
            model = Category

        id = factory.Sequence(lambda n: n)
        name = factory.Sequence(lambda n: f"Category {n}")
        description = factory.Faker("sentence", nb_words=10)
        created_at = factory.Faker("past_datetime", start_date="-30d")
        updated_at = factory.Faker("past_datetime", start_date="-1d")


    class ProductFactory(BaseFactory):
        """Factory for creating Product database instances."""

        class Meta:
            model = Product

        id = factory.Sequence(lambda n: n)
        name = factory.Sequence(lambda n: f"Test Product {n}")
        description = factory.Faker("sentence", nb_words=15)
        price = FuzzyFloat(10.0, 1000.0, precision=2)
        sku = factory.Sequence(lambda n: f"SKU-{n:06d}")
        stock_quantity = FuzzyInteger(0, 1000)
        is_active = True
        created_at = factory.Faker("past_datetime", start_date="-30d")
        updated_at = factory.Faker("past_datetime", start_date="-1d")


    class CustomerFactory(BaseFactory):
        """Factory for creating Customer database instances."""

        class Meta:
            model = Customer

        id = factory.Sequence(lambda n: n)
        name = factory.Faker("name")
        email = factory.Sequence(lambda n: f"customer{n}@example.com")
        phone = factory.Faker("phone_number")
        address = factory.Faker("address")
        created_at = factory.Faker("past_datetime", start_date="-30d")
        updated_at = factory.Faker("past_datetime", start_date="-1d")


    class WarehouseFactory(BaseFactory):
        """Factory for creating Warehouse database instances."""

        class Meta:
            model = Warehouse

        id = factory.Sequence(lambda n: n)
        name = factory.Sequence(lambda n: f"Warehouse {n}")
        code = factory.Sequence(lambda n: f"WH{n:03d}")
        address = factory.Faker("street_address")
        city = factory.Faker("city")
        country = factory.Faker("country")
        is_active = True


    class AuditLogFactory(BaseFactory):
        """Factory for creating AuditLog database instances."""

        class Meta:
            model = AuditLog

        id = factory.Sequence(lambda n: n)
        user_id = FuzzyInteger(1, 100)
        action = FuzzyChoice([
            "login_success", "login_attempt", "create", "update", "delete",
            "view", "export", "import", "login_failed", "logout"
        ])
        resource = FuzzyChoice([
            "users", "products", "orders", "reports", "inventory",
            "settings", "auth", "dashboard", "api"
        ])
        resource_id = factory.LazyAttribute(
            lambda obj: f"{obj.resource}:{factory.Faker('uuid4')}"
        )
        details = factory.LazyFunction(lambda: {
            "ip_address": factory.Faker("ipv4").generate({}),
            "user_agent": factory.Faker("user_agent").generate({}),
            "metadata": {"test": True, "factory_generated": True},
        })
        success = FuzzyChoice([True, False])
        timestamp = factory.Faker("past_datetime", start_date="-30d")


    class OrderFactory(BaseFactory):
        """Factory for creating Order database instances."""

        class Meta:
            model = Order

        id = factory.Sequence(lambda n: n)
        customer_id = FuzzyInteger(1, 100)
        order_date = factory.Faker("past_datetime", start_date="-30d")
        total_amount = FuzzyFloat(50.0, 5000.0, precision=2)
        status = FuzzyChoice(["pending", "processing", "shipped", "delivered", "cancelled"])
        created_at = factory.Faker("past_datetime", start_date="-30d")
        updated_at = factory.Faker("past_datetime", start_date="-1d")


    class OrderLineFactory(BaseFactory):
        """Factory for creating OrderLine database instances."""

        class Meta:
            model = OrderLine

        id = factory.Sequence(lambda n: n)
        order_id = FuzzyInteger(1, 100)
        product_id = FuzzyInteger(1, 200)
        quantity = FuzzyInteger(1, 10)
        unit_price = FuzzyFloat(10.0, 100.0, precision=2)
        total_price = factory.LazyAttribute(lambda obj: obj.quantity * obj.unit_price)


    class SupplierFactory(BaseFactory):
        """Factory for creating Supplier database instances."""

        class Meta:
            model = Supplier

        id = factory.Sequence(lambda n: n)
        name = factory.Sequence(lambda n: f"Supplier {n}")
        contact_email = factory.Sequence(lambda n: f"contact{n}@example.com")
        phone = factory.Faker("phone_number")
        address = factory.Faker("address")
        is_active = True
        created_at = factory.Faker("past_datetime", start_date="-30d")
        updated_at = factory.Faker("past_datetime", start_date="-1d")


# Enhanced Test Fixtures
@pytest.fixture
def sample_user():
    """Provide a sample user for testing."""
    if DATABASE_MODELS_AVAILABLE:
        return UserFactory()
    return UserDictFactory()


@pytest.fixture
def sample_users():
    """Provide multiple sample users for testing."""
    if DATABASE_MODELS_AVAILABLE:
        return UserFactory.create_batch(5)
    return UserDictFactory.create_batch(5)


@pytest.fixture
def sample_admin_user():
    """Provide a sample admin user for testing."""
    if DATABASE_MODELS_AVAILABLE:
        return AdminUserFactory()
    return AdminUserDictFactory()


@pytest.fixture
def sample_audit_log():
    """Provide a sample audit log entry."""
    if DATABASE_MODELS_AVAILABLE:
        return AuditLogFactory()
    return {
        "id": 1,
        "user_id": 1,
        "action": "login_success",
        "resource": "auth",
        "resource_id": "auth:123",
        "details": {"ip_address": "127.0.0.1", "user_agent": "test"},
        "success": True,
        "timestamp": datetime.now()
    }


@pytest.fixture
def sample_audit_logs():
    """Provide multiple sample audit logs."""
    if DATABASE_MODELS_AVAILABLE:
        return AuditLogFactory.create_batch(10)
    return [
        {
            "id": i,
            "user_id": i % 5 + 1,
            "action": "login_success",
            "resource": "auth",
            "resource_id": f"auth:{i}",
            "details": {"ip_address": "127.0.0.1", "user_agent": "test"},
            "success": True,
            "timestamp": datetime.now()
        }
        for i in range(10)
    ]


@pytest.fixture
def sample_product():
    """Provide a sample product."""
    if DATABASE_MODELS_AVAILABLE:
        return ProductFactory()
    return ProductDictFactory()


@pytest.fixture
def sample_products():
    """Provide multiple sample products."""
    if DATABASE_MODELS_AVAILABLE:
        return ProductFactory.create_batch(5)
    return ProductDictFactory.create_batch(5)


@pytest.fixture
def sample_order():
    """Provide a sample order."""
    if DATABASE_MODELS_AVAILABLE:
        return OrderFactory()
    return OrderDictFactory()


@pytest.fixture
def sample_orders():
    """Provide multiple sample orders."""
    if DATABASE_MODELS_AVAILABLE:
        return OrderFactory.create_batch(3)
    return OrderDictFactory.create_batch(3)


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


# Database session-based fixtures
if DATABASE_MODELS_AVAILABLE:

    @pytest.fixture
    async def db_user(db_session):
        """Create a test user in the database."""
        user = UserFactory()
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user


    @pytest.fixture
    async def db_admin_user(db_session):
        """Create a test admin user in the database."""
        user = AdminUserFactory()
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user


    @pytest.fixture
    async def db_product(db_session):
        """Create a test product in the database."""
        product = ProductFactory()
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)
        return product


    @pytest.fixture
    async def db_category(db_session):
        """Create a test category in the database."""
        category = CategoryFactory()
        db_session.add(category)
        await db_session.commit()
        await db_session.refresh(category)
        return category


    @pytest.fixture
    async def db_role(db_session):
        """Create a test role in the database."""
        role = RoleFactory()
        db_session.add(role)
        await db_session.commit()
        await db_session.refresh(role)
        return role


    @pytest.fixture
    async def db_permission(db_session):
        """Create a test permission in the database."""
        permission = PermissionFactory()
        db_session.add(permission)
        await db_session.commit()
        await db_session.refresh(permission)
        return permission


    @pytest.fixture
    async def db_audit_log(db_session):
        """Create a test audit log in the database."""
        audit_log = AuditLogFactory()
        db_session.add(audit_log)
        await db_session.commit()
        await db_session.refresh(audit_log)
        return audit_log


# Convenience functions for creating test data with relationships
def create_user_with_role(db_session, role_name: str = "user", **user_kwargs):
    """Create a user with a specific role."""
    if not DATABASE_MODELS_AVAILABLE:
        return {"email": f"{role_name}@example.com", "role": role_name, **user_kwargs}

    # Create or get role
    role = db_session.query(Role).filter_by(name=role_name).first()
    if not role:
        role = RoleFactory(name=role_name, description=f"{role_name} role")
        db_session.add(role)
        db_session.commit()

    # Create user
    user = UserFactory(roles=[role], **user_kwargs)
    db_session.add(user)
    db_session.commit()

    return user


def create_product_with_categories(db_session, category_count: int = 2):
    """Create a product with random categories."""
    if not DATABASE_MODELS_AVAILABLE:
        return {
            "name": "Test Product",
            "categories": [f"Category {i}" for i in range(category_count)]
        }

    # Create categories if they don't exist
    categories = []
    for i in range(category_count):
        category = CategoryFactory(name=f"Test Category {i}")
        db_session.add(category)
        categories.append(category)

    db_session.commit()

    # Create product
    product = ProductFactory()
    product.categories = categories
    db_session.add(product)
    db_session.commit()

    return product


def create_admin_user(db_session):
    """Create an admin user with admin role."""
    return create_user_with_role(db_session, "admin", is_superuser=True)


def create_test_user_data():
    """Create sample user data for API testing."""
    return {
        "email": "test@example.com",
        "password": "test_password123",
        "full_name": "Test User",
        "is_active": True
    }


def create_test_product_data():
    """Create sample product data for API testing."""
    return {
        "name": "Test Product",
        "description": "This is a test product for API testing",
        "price": 99.99,
        "sku": "TEST-001",
        "stock_quantity": 100,
        "is_active": True
    }


def create_test_category_data():
    """Create sample category data for API testing."""
    return {
        "name": "Test Category",
        "description": "This is a test category for API testing"
    }


# Bulk data creation functions
def create_bulk_users(db_session, count: int = 10):
    """Create multiple users for performance testing."""
    if not DATABASE_MODELS_AVAILABLE:
        return [UserDictFactory() for _ in range(count)]

    users = []
    for _ in range(count):
        user = UserFactory()
        db_session.add(user)
        users.append(user)

    db_session.commit()
    return users


def create_bulk_products(db_session, count: int = 20):
    """Create multiple products for performance testing."""
    if not DATABASE_MODELS_AVAILABLE:
        return [ProductDictFactory() for _ in range(count)]

    products = []
    for _ in range(count):
        product = ProductFactory()
        db_session.add(product)
        products.append(product)

    db_session.commit()
    return products
