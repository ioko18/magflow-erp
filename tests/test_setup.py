"""Test setup and utilities for MagFlow ERP."""

import os
from typing import AsyncGenerator

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base_class import Base
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User

# Test database configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

# Create test session
TestingSessionLocal = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def setup_test_database():
    """Create test database tables."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def teardown_test_database():
    """Drop test database tables and clean up."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # Remove test database file
    if os.path.exists("test.db"):
        os.remove("test.db")


async def create_test_data(session: AsyncSession):
    """Create test data for testing."""
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # Create test permissions
    permissions = [
        Permission(
            name="users_read",
            resource="users",
            action="read",
            description="Read user information",
        ),
        Permission(
            name="users_write",
            resource="users",
            action="write",
            description="Create and edit users",
        ),
        Permission(
            name="products_read",
            resource="products",
            action="read",
            description="Read product information",
        ),
        Permission(
            name="products_write",
            resource="products",
            action="write",
            description="Create and edit products",
        ),
    ]

    for perm in permissions:
        session.add(perm)

    await session.flush()

    # Create test roles
    user_role = Role(name="user", description="Regular user role", is_system_role=False)
    user_role.permissions.extend(permissions[:2])  # users_read, users_write

    admin_role = Role(
        name="admin", description="Administrator role", is_system_role=True
    )
    admin_role.permissions.extend(permissions)  # All permissions

    session.add(user_role)
    session.add(admin_role)

    await session.flush()

    # Create test users
    test_user = User(
        email="test@example.com",
        hashed_password=pwd_context.hash("TestPassword123!"),
        full_name="Test User",
        is_active=True,
        is_superuser=False,
    )
    test_user.roles.append(user_role)

    admin_user = User(
        email="admin@example.com",
        hashed_password=pwd_context.hash("AdminPassword123!"),
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
    )
    admin_user.roles.append(admin_role)

    session.add(test_user)
    session.add(admin_user)

    await session.commit()

    return {
        "test_user": test_user,
        "admin_user": admin_user,
        "user_role": user_role,
        "admin_role": admin_role,
        "permissions": permissions,
    }


async def get_test_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a test database session."""
    async with TestingSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class TestDataFactory:
    """Factory for creating test data."""

    @staticmethod
    async def create_user(
        session: AsyncSession,
        email: str = "test@example.com",
        password: str = "TestPassword123!",
        full_name: str = "Test User",
        is_active: bool = True,
        is_superuser: bool = False,
    ) -> User:
        """Create a test user."""
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        user = User(
            email=email,
            hashed_password=pwd_context.hash(password),
            full_name=full_name,
            is_active=is_active,
            is_superuser=is_superuser,
        )
        session.add(user)
        await session.flush()
        return user

    @staticmethod
    async def create_role(
        session: AsyncSession,
        name: str = "test_role",
        description: str = "Test role",
        is_system_role: bool = False,
    ) -> Role:
        """Create a test role."""
        role = Role(
            name=name,
            description=description,
            is_system_role=is_system_role,
        )
        session.add(role)
        await session.flush()
        return role

    @staticmethod
    async def create_permission(
        session: AsyncSession,
        name: str = "test_permission",
        resource: str = "test",
        action: str = "read",
        description: str = "Test permission",
    ) -> Permission:
        """Create a test permission."""
        permission = Permission(
            name=name,
            resource=resource,
            action=action,
            description=description,
        )
        session.add(permission)
        await session.flush()
        return permission


# Test utilities
class TestUtils:
    """Utility functions for testing."""

    @staticmethod
    def create_jwt_token(
        email: str = "test@example.com",
        token_type: str = "access",
        expires_minutes: int = 15,
    ) -> str:
        """Create a JWT token for testing."""
        from datetime import datetime, timedelta

        from jose import jwt

        expire = datetime.utcnow() + timedelta(minutes=expires_minutes)

        to_encode = {
            "exp": expire,
            "sub": email,
            "iat": datetime.utcnow(),
            "type": token_type,
            "email": email,
            "full_name": "Test User",
            "role": "admin",
            "roles": ["admin"],
        }

        return jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

    @staticmethod
    def assert_http_exception(
        exc: Exception,
        expected_status: int,
        expected_detail: str,
    ):
        """Assert that an exception is an HTTPException with expected values."""
        assert isinstance(exc.value, HTTPException)
        assert exc.value.status_code == expected_status
        assert expected_detail in str(exc.value.detail)
