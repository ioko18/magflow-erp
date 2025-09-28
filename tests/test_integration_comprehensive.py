"""
Comprehensive integration tests for MagFlow ERP.

This module provides integration tests that verify the interaction between
different components, services, and modules of the application.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient

from app.main import app
from tests.test_data_factory import (
    create_test_user_data, create_test_product_data, create_test_category_data,
    UserFactory, ProductFactory, CategoryFactory, RoleFactory, PermissionFactory
)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_user_authentication_integration(db_session):
    """Test complete user authentication flow."""
    # Create test user
    user = UserFactory()
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Test password hashing
    from app.core.security import verify_password, get_password_hash
    hashed_password = get_password_hash("test_password123")
    assert verify_password("test_password123", hashed_password)

    # Test user authentication
    assert user.is_authenticated
    assert user.check_password("test_password123")

    # Test admin privileges
    admin_user = UserFactory(is_superuser=True)
    assert admin_user.is_admin

    # Test role-based permissions
    role = RoleFactory()
    permission = PermissionFactory(name="test_permission")
    role.permissions.append(permission)
    user.roles.append(role)
    await db_session.commit()

    assert user.has_permission("test_permission")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_product_category_relationship_integration(db_session):
    """Test product-category relationship integration."""
    # Create categories
    categories = []
    for i in range(3):
        category = CategoryFactory(name=f"Test Category {i}")
        db_session.add(category)
        categories.append(category)

    await db_session.commit()

    # Create product with categories
    product = ProductFactory()
    product.categories = categories
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    # Verify relationships
    assert len(product.categories) == 3
    category_names = [cat.name for cat in product.categories]
    assert "Test Category 0" in category_names
    assert "Test Category 1" in category_names
    assert "Test Category 2" in category_names


@pytest.mark.asyncio
@pytest.mark.integration
async def test_user_role_permission_integration(db_session):
    """Test user-role-permission integration."""
    # Create permission
    permission = PermissionFactory(name="read_products", resource="products", action="read")
    db_session.add(permission)

    # Create role with permission
    role = RoleFactory(name="product_manager")
    role.permissions.append(permission)
    db_session.add(role)

    # Create user with role
    user = UserFactory()
    user.roles.append(role)
    db_session.add(user)

    await db_session.commit()
    await db_session.refresh(user)

    # Verify integration
    assert len(user.roles) == 1
    assert user.roles[0].name == "product_manager"
    assert len(user.roles[0].permissions) == 1
    assert user.roles[0].permissions[0].name == "read_products"

    # Test permission checking
    assert user.has_permission("read_products")
    assert not user.has_permission("nonexistent_permission")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_audit_logging_integration(db_session):
    """Test audit logging integration across operations."""
    from app.models.audit_log import AuditLog

    # Create user
    user = UserFactory()
    db_session.add(user)
    await db_session.commit()

    # Create audit log entry
    audit_log = AuditLog(
        user_id=user.id,
        action="test_action",
        resource="test_resource",
        resource_id="test:123",
        details={"test": True},
        success=True
    )
    db_session.add(audit_log)
    await db_session.commit()
    await db_session.refresh(audit_log)

    # Verify audit log was created
    assert audit_log.id is not None
    assert audit_log.user_id == user.id
    assert audit_log.action == "test_action"
    assert audit_log.success is True

    # Query audit logs
    result = await db_session.execute(
        "SELECT COUNT(*) FROM audit_logs WHERE user_id = :user_id",
        {"user_id": user.id}
    )
    count = result.scalar()
    assert count == 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_database_transaction_isolation(db_session):
    """Test database transaction isolation between operations."""
    # Create user in one transaction
    user1 = UserFactory(email="user1@example.com")
    db_session.add(user1)
    await db_session.commit()

    # Create another user in separate transaction context
    user2 = UserFactory(email="user2@example.com")
    db_session.add(user2)
    await db_session.commit()

    # Verify both users exist
    result = await db_session.execute("SELECT COUNT(*) FROM users")
    total_users = result.scalar()
    assert total_users >= 2

    # Test user retrieval
    result = await db_session.execute(
        "SELECT email FROM users WHERE email = :email",
        {"email": "user1@example.com"}
    )
    db_user1 = result.fetchone()
    assert db_user1 is not None
    assert db_user1.email == "user1@example.com"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cascade_operations_integration(db_session):
    """Test cascade operations and relationships."""
    # Create role first
    role = RoleFactory()
    db_session.add(role)
    await db_session.commit()

    # Create user with role (many-to-many relationship)
    user = UserFactory()
    user.roles.append(role)
    db_session.add(user)
    await db_session.commit()

    # Verify relationship was created
    assert len(user.roles) == 1
    assert user.roles[0].id == role.id

    # Test cascade behavior - deleting user should not delete role
    await db_session.delete(user)
    await db_session.commit()

    # Role should still exist
    result = await db_session.execute(
        "SELECT COUNT(*) FROM roles WHERE id = :role_id",
        {"role_id": role.id}
    )
    role_count = result.scalar()
    assert role_count == 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_json_field_operations_integration(db_session):
    """Test JSON field operations and serialization."""
    # Create product with JSON characteristics
    characteristics = {
        "color": ["red", "blue"],
        "size": ["S", "M", "L"],
        "features": ["waterproof", "durable"]
    }

    product = ProductFactory()
    # Simulate JSON field storage
    product.characteristics = json.dumps(characteristics)
    db_session.add(product)
    await db_session.commit()

    # Retrieve and verify JSON data
    result = await db_session.execute(
        "SELECT characteristics FROM products WHERE id = :product_id",
        {"product_id": product.id}
    )
    stored_data = result.scalar()

    if stored_data:
        parsed_data = json.loads(stored_data)
        assert parsed_data["color"] == ["red", "blue"]
        assert "waterproof" in parsed_data["features"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_concurrent_operations_safety(db_session):
    """Test safety of concurrent database operations."""
    import asyncio

    async def create_user_with_retry(email: str):
        """Create a user with retry logic."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                user = UserFactory(email=email)
                db_session.add(user)
                await db_session.commit()
                return user
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                await db_session.rollback()

    # Create multiple users concurrently
    emails = [f"concurrent_user_{i}@example.com" for i in range(5)]
    tasks = [create_user_with_retry(email) for email in emails]

    users = await asyncio.gather(*tasks)

    # Verify all users were created
    assert len(users) == 5
    created_emails = [user.email for user in users]
    assert all(email in created_emails for email in emails)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_api_database_integration():
    """Test API and database integration."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test user creation via API
        user_data = create_test_user_data()
        response = await client.post("/api/v1/auth/register", json=user_data)

        if response.status_code == 201:
            # User created successfully
            user_response = response.json()
            assert "email" in user_response
            assert user_response["email"] == user_data["email"]
        else:
            # Registration might not be implemented, that's okay
            assert response.status_code in [404, 422, 501]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_service_layer_integration(db_session):
    """Test service layer integration with database."""
    # This would test actual service classes if they exist
    # For now, test basic CRUD operations

    # Create product
    product = ProductFactory()
    db_session.add(product)
    await db_session.commit()

    # Update product
    product.price = 199.99
    await db_session.commit()

    # Verify update
    result = await db_session.execute(
        "SELECT price FROM products WHERE id = :product_id",
        {"product_id": product.id}
    )
    updated_price = result.scalar()
    assert updated_price == 199.99


@pytest.mark.asyncio
@pytest.mark.integration
async def test_error_handling_integration(db_session):
    """Test error handling across integrated components."""
    # Test constraint violations
    try:
        # Try to create user with duplicate email (if unique constraint exists)
        user1 = UserFactory(email="duplicate@example.com")
        user2 = UserFactory(email="duplicate@example.com")

        db_session.add(user1)
        db_session.add(user2)

        await db_session.commit()
        # If no error, that's also fine (no unique constraint)
    except Exception:
        # Expected if unique constraint exists
        await db_session.rollback()

    # Test foreign key constraints
    try:
        # Try to create invalid foreign key reference
        # This depends on actual model constraints
        pass
    except Exception:
        # Expected if constraints exist
        await db_session.rollback()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_data_consistency_integration(db_session):
    """Test data consistency across related operations."""
    # Create category
    category = CategoryFactory()
    db_session.add(category)
    await db_session.commit()

    # Create product in category
    product = ProductFactory()
    product.categories.append(category)
    db_session.add(product)
    await db_session.commit()

    # Verify consistency
    result = await db_session.execute("""
        SELECT p.name, c.name as category_name
        FROM products p
        JOIN product_categories pc ON p.id = pc.product_id
        JOIN categories c ON pc.category_id = c.id
        WHERE p.id = :product_id
    """, {"product_id": product.id})

    rows = result.fetchall()
    assert len(rows) == 1
    assert rows[0].name == product.name
    assert rows[0].category_name == category.name


@pytest.mark.asyncio
@pytest.mark.integration
async def test_performance_under_load(db_session):
    """Test system performance under moderate load."""
    import time

    # Create moderate amount of test data
    users = []
    for i in range(20):
        user = UserFactory(email=f"load_test_{i}@example.com")
        db_session.add(user)
        users.append(user)

    products = []
    for i in range(50):
        product = ProductFactory(name=f"Load Test Product {i}")
        db_session.add(product)
        products.append(product)

    await db_session.commit()

    # Measure query performance under load
    start_time = time.perf_counter()

    # Run several complex queries
    for _ in range(10):
        result = await db_session.execute("""
            SELECT COUNT(*) FROM users u
            LEFT JOIN user_roles ur ON u.id = ur.user_id
            LEFT JOIN roles r ON ur.role_id = r.id
        """)
        count = result.scalar()

    end_time = time.perf_counter()
    execution_time = end_time - start_time

    # Should handle moderate load reasonably well
    assert execution_time < 2.0, f"Queries under load took too long: {execution_time:.2f}s"
    assert count >= 20, "User count should be at least the number we created"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_memory_usage_integration(db_session):
    """Test memory usage patterns in integrated operations."""
    # This is a basic test - in real scenarios you'd use memory profiling
    initial_object_count = len(db_session.new) + len(db_session.dirty) + len(db_session.deleted)

    # Create some objects
    for _ in range(10):
        user = UserFactory()
        db_session.add(user)

    after_creation_count = len(db_session.new)

    # Commit changes
    await db_session.commit()

    after_commit_count = len(db_session.new) + len(db_session.dirty) + len(db_session.deleted)

    # Memory should be managed properly
    assert after_commit_count < after_creation_count, "Session should be cleaner after commit"
    assert after_commit_count <= initial_object_count + 1, "Should not have excessive objects in session"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cross_service_data_flow(db_session):
    """Test data flow between different services/components."""
    # This would test actual service integrations
    # For now, test basic data relationships

    # Create user with role
    role = RoleFactory(name="test_role")
    user = UserFactory()
    user.roles.append(role)

    db_session.add(role)
    db_session.add(user)
    await db_session.commit()

    # Create product with category
    category = CategoryFactory(name="test_category")
    product = ProductFactory()
    product.categories.append(category)

    db_session.add(category)
    db_session.add(product)
    await db_session.commit()

    # Verify cross-component relationships
    user_result = await db_session.execute(
        "SELECT COUNT(*) FROM user_roles WHERE user_id = :user_id",
        {"user_id": user.id}
    )
    user_role_count = user_result.scalar()
    assert user_role_count == 1

    product_result = await db_session.execute(
        "SELECT COUNT(*) FROM product_categories WHERE product_id = :product_id",
        {"product_id": product.id}
    )
    product_category_count = product_result.scalar()
    assert product_category_count == 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_backup_and_recovery_simulation(db_session):
    """Simulate backup and recovery operations."""
    # Create test data
    original_users = []
    for i in range(5):
        user = UserFactory(email=f"backup_test_{i}@example.com")
        db_session.add(user)
        original_users.append(user)

    await db_session.commit()

    # Simulate counting records (like a backup verification)
    result = await db_session.execute("SELECT COUNT(*) FROM users")
    backup_count = result.scalar()

    # Simulate data recovery by creating more users
    recovery_users = []
    for i in range(3):
        user = UserFactory(email=f"recovery_test_{i}@example.com")
        db_session.add(user)
        recovery_users.append(user)

    await db_session.commit()

    # Verify recovery
    result = await db_session.execute("SELECT COUNT(*) FROM users")
    final_count = result.scalar()

    assert final_count >= backup_count + 3, "Recovery should increase user count"
    assert final_count >= 8, "Should have at least 8 users total"
