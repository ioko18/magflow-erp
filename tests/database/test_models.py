"""
Tests for database models in MagFlow ERP.

This module contains tests for database models and their relationships.
"""
import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.role import Role
from app.models.user import User


async def _add_role(session, name: str, description: str) -> Role:
    role = Role(name=name, description=description)
    session.add(role)
    await session.flush()
    await session.refresh(role)
    return role


async def _add_user(session, email: str, full_name: str, hashed_password: str = "hashed_password") -> User:
    user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        is_active=True,
        is_superuser=False,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def _attach_role(session, user: User, role: Role) -> None:
    user.roles.append(role)
    await session.flush()
    await session.refresh(user)
    await session.refresh(role)


@pytest.mark.asyncio
async def test_user_model(db_session):
    """Test `User` model creation and relationships."""

    role = await _add_role(db_session, name="test_role", description="Test Role")
    user = await _add_user(db_session, email="test@example.com", full_name="Test User")
    await _attach_role(db_session, user=user, role=role)

    result = await db_session.execute(
        select(User)
        .options(selectinload(User.roles))
        .where(User.email == "test@example.com")
    )
    db_user = result.scalar_one_or_none()

    assert db_user is not None
    assert db_user.email == "test@example.com"
    assert db_user.full_name == "Test User"
    assert db_user.is_active is True
    assert db_user.is_superuser is False
    assert len(db_user.roles) == 1
    assert db_user.roles[0].name == "test_role"


@pytest.mark.asyncio
async def test_role_model(db_session):
    """Test `Role` model creation and relationships."""

    await _add_role(db_session, name="admin", description="Administrator Role")

    result = await db_session.execute(
        select(Role)
        .options(selectinload(Role.users))
        .where(Role.name == "admin")
    )
    db_role = result.scalar_one_or_none()

    assert db_role is not None
    assert db_role.name == "admin"
    assert db_role.description == "Administrator Role"
    assert len(db_role.users) == 0


@pytest.mark.asyncio
async def test_user_role_relationship(db_session):
    """Test the relationship between `User` and `Role` models."""

    role = await _add_role(db_session, name="manager", description="Manager Role")
    user = await _add_user(
        db_session,
        email="manager@example.com",
        full_name="Manager User",
    )
    await _attach_role(db_session, user=user, role=role)

    role_result = await db_session.execute(
        select(Role)
        .options(selectinload(Role.users))
        .where(Role.name == "manager")
    )
    db_role = role_result.scalar_one_or_none()

    user_result = await db_session.execute(
        select(User)
        .options(selectinload(User.roles))
        .where(User.email == "manager@example.com")
    )
    db_user = user_result.scalar_one_or_none()

    assert db_role is not None
    assert len(db_role.users) == 1
    assert db_role.users[0].email == "manager@example.com"

    assert db_user is not None
    assert len(db_user.roles) == 1
    assert db_user.roles[0].name == "manager"
