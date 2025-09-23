"""Unit tests for authentication system."""

from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.api.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_active_user,
    get_password_hash,
    verify_password,
)


class TestPasswordFunctions:
    """Test password hashing and verification functions."""

    def test_verify_password_success(self):
        """Test successful password verification."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_failure(self):
        """Test failed password verification."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    def test_get_password_hash(self):
        """Test password hashing."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)

        # Verify the hash is different from the original password
        assert hashed != password
        assert len(hashed) > 0
        assert verify_password(password, hashed) is True


class TestJWTTokenFunctions:
    """Test JWT token creation and validation functions."""

    def test_create_access_token(self):
        """Test access token creation."""
        subject = "test@example.com"
        token = create_access_token(subject)

        # Verify token is not empty
        assert len(token) > 0

        # Verify token can be decoded
        payload = decode_token(token)
        assert payload["sub"] == subject
        assert payload["type"] == "access"

    def test_create_access_token_with_expiry(self):
        """Test access token creation with custom expiry."""
        subject = "test@example.com"
        expires_delta = timedelta(minutes=30)
        token = create_access_token(subject, expires_delta)

        payload = decode_token(token)
        assert payload["sub"] == subject
        assert payload["type"] == "access"

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        subject = "test@example.com"
        token = create_refresh_token(subject)

        # Verify token is not empty
        assert len(token) > 0

        # Verify token can be decoded
        payload = decode_token(token)
        assert payload["sub"] == subject
        assert payload["type"] == "refresh"

    def test_decode_token_invalid(self):
        """Test invalid token decoding."""
        invalid_token = "invalid.jwt.token"

        with pytest.raises(HTTPException) as exc_info:
            decode_token(invalid_token)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)


@pytest.mark.asyncio
class TestAuthenticationSystem:
    """Test the authentication system integration."""

    async def test_get_current_active_user_success(
        self,
        db_session,
        test_user,
    ):
        """Test successful user authentication."""
        # Create a valid token for the test user
        token = create_access_token(test_user.email)

        # Test getting current user
        user = await get_current_active_user(token, db_session)

        assert user.email == test_user.email
        assert user.id == test_user.id
        assert user.is_active == test_user.is_active

    async def test_get_current_active_user_no_token(self):
        """Test authentication with no token."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user("", None)

        assert exc_info.value.status_code == 401
        assert "Not authenticated" in str(exc_info.value.detail)

    async def test_get_current_active_user_invalid_token(self):
        """Test authentication with invalid token."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user("invalid.token", None)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)

    async def test_get_current_active_user_user_not_found(
        self,
        db_session,
    ):
        """Test authentication with valid token but user not in database."""
        token = create_access_token("nonexistent@example.com")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(token, db_session)

        assert exc_info.value.status_code == 401
        assert "User not found" in str(exc_info.value.detail)

    async def test_get_current_active_user_inactive_user(
        self,
        db_session,
        test_user,
    ):
        """Test authentication with inactive user."""
        # Make user inactive
        test_user.is_active = False
        await db_session.commit()

        token = create_access_token(test_user.email)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(token, db_session)

        assert exc_info.value.status_code == 400
        assert "Inactive user" in str(exc_info.value.detail)
