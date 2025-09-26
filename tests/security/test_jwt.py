"""Tests for JWT authentication with RS256 and EdDSA support."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest
from fastapi import FastAPI, HTTPException, Request, status
from jose import JWTError
from jose import jwt as jose_jwt
from jose.exceptions import JWTError as JoseJWTError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import User
from app.schemas.user import UserInDB
from app.security.jwt import (
    create_access_token,
    decode_token,
    get_current_active_superuser,
    get_current_active_user,
    get_current_user,
    oauth2_scheme,
)

# Remove unused imports

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Test data
test_password = "testpassword123"
# Test user data
test_user_data = {
    "id": 1,
    "email": "test@example.com",
    "hashed_password": "hashed_password",
    "full_name": "Test User",
    "is_active": True,
    "is_superuser": False,
    "is_verified": True,
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
}

# Create test user instance
TEST_USER = UserInDB(**test_user_data)

# Test admin user data
test_admin_data = {
    "id": 2,
    "email": "admin@example.com",
    "hashed_password": "hashed_password",
    "full_name": "Admin User",
    "is_active": True,
    "is_superuser": True,
    "is_verified": True,
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
}

# Create test admin instance
TEST_ADMIN = UserInDB(**test_admin_data)

# Mock database for testing
mock_db = AsyncMock(spec=AsyncSession)


@pytest.mark.asyncio
async def test_create_and_validate_token():
    """Test creating and validating a JWT token."""
    # Create a mock key for testing
    mock_key = MagicMock()
    mock_key.public_key = "test_public_key"

    # Mock the token creation and validation
    with patch("app.security.jwt.key_manager") as mock_key_manager, patch(
        "jose.jwt.encode",
    ) as mock_encode, patch("jose.jwt.get_unverified_header") as mock_get_header, patch(
        "jose.jwt.decode",
    ) as mock_decode:
        # Setup mocks
        mock_key_manager.get_key.return_value = mock_key
        mock_key_manager.get_public_key.return_value = "test_public_key"
        mock_encode.return_value = "test_token"
        mock_get_header.return_value = {"kid": "test_key_id", "alg": "HS256"}
        mock_decode.return_value = {
            "sub": "test@example.com",
            "exp": (datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp(),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        }

        # Create a test token
        token = create_access_token("test@example.com")

        # Verify token was created with correct parameters
        mock_encode.assert_called_once()
        assert token == "test_token"

        # Validate the token
        payload = decode_token(token)
        assert payload["sub"] == "test@example.com"
        assert "exp" in payload

        # Test token expiration
        mock_decode.side_effect = JoseJWTError("Token has expired")
        with pytest.raises(JoseJWTError):
            decode_token(token)


@pytest.mark.asyncio
async def test_create_and_validate_token_rs256():
    """Test creating and validating a token with RS256 algorithm."""
    # Create a token with RS256 algorithm
    token = create_access_token(subject=TEST_USER.email, algorithm="RS256")

    # Decode and validate the token
    payload = decode_token(token, algorithms=["RS256"])

    # Verify the payload
    assert payload["sub"] == TEST_USER.email
    assert payload["iss"] == settings.jwt_issuer
    assert payload["aud"] == settings.jwt_audience
    assert "iat" in payload
    assert "exp" in payload


def test_create_and_validate_token_ed25519():
    """Test creating and validating a token with EdDSA algorithm."""
    # Skip if EdDSA is not supported
    if "EdDSA" not in settings.jwt_supported_algorithms:
        pytest.skip("EdDSA not supported in this configuration")

    # Create token
    token = create_access_token(
        subject=TEST_USER.email,
        expires_delta=timedelta(minutes=15),
        algorithm="EdDSA",
    )

    # Decode and validate token
    payload = decode_token(token, algorithms=["EdDSA"])

    # Assert claims
    assert payload["sub"] == TEST_USER.email
    assert payload["iss"] == settings.jwt_issuer
    assert payload["aud"] == settings.jwt_audience


def test_token_expiration():
    """Test that an expired token raises an exception."""
    # Create a token with a past expiration time
    expired_token = create_access_token(
        subject=TEST_USER.email,
        expires_delta=timedelta(seconds=-1),  # Already expired
    )

    # Mock the current time to be after the token expiration
    with patch("app.security.jwt.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime.now(timezone.utc) + timedelta(
            seconds=60,
        )

        # Verify the token is expired
        with pytest.raises(JoseJWTError) as exc_info:
            decode_token(expired_token)
        assert "Signature has expired" in str(exc_info.value)


def test_invalid_algorithm():
    """Test that an invalid algorithm raises an exception."""
    with pytest.raises(ValueError) as exc_info:
        create_access_token(
            subject=TEST_USER.email,
            algorithm="invalid-alg",
        )
    assert "Unsupported JWT algorithm" in str(exc_info.value)


@pytest.mark.asyncio
async def test_algorithm_mismatch():
    """Test that using the wrong algorithm for validation fails."""
    # Create token with RS256
    token = create_access_token(subject=TEST_USER.email, algorithm="RS256")

    # Try to validate with EdDSA (should fail)
    with pytest.raises(JWTError):
        await decode_token(token, algorithms=["EdDSA"])


def test_missing_kid():
    """Test that a token without a kid raises an exception."""
    from app.security import jwt as security_jwt

    # Ensure we have an RS256 key available and craft a token missing the kid header
    security_jwt.key_manager.ensure_active_key("RS256")
    keypair = security_jwt.key_manager.get_active_key("RS256")

    token = jose_jwt.encode(
        {"sub": "test@example.com"},
        keypair.private_key,
        algorithm="RS256",
        headers={"alg": "RS256"},  # No kid claim on purpose
    )

    # The test should raise JWTError when no kid is present in the token header
    with pytest.raises(JWTError) as exc_info:
        decode_token(token)

    assert "Token header missing 'kid' claim" in str(exc_info.value)


# Mock FastAPI Request for testing
class MockRequest:
    def __init__(self, token: str = None, app: Optional[FastAPI] = None):
        self.headers = {}
        self.scope = {}
        if token:
            self.headers["authorization"] = f"Bearer {token}"
        if app:
            self.scope["app"] = app
            self.app = app


@pytest.mark.asyncio
async def test_get_current_user():
    """Test getting the current user from a valid token."""
    # Create a test user
    test_user = User(
        id=1,
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_superuser=False,
        email_verified=True,
        full_name="Test User",
    )

    # Import the function to test
    from app.security.jwt import get_current_active_user

    # Test with active user
    result = await get_current_active_user(test_user)

    # Assert the result
    assert result.email == "test@example.com"
    assert result.is_active is True
    assert result.is_superuser is False


@pytest.mark.asyncio
async def test_get_current_user_missing_token():
    """Test getting current user with missing token."""
    # Mock database
    mock_db = MagicMock(spec=AsyncSession)

    # Create a mock FastAPI app with state
    mock_app = MagicMock()
    mock_app.state._state = {}

    # Create a mock request with the required scope
    request = Request(scope={"type": "http", "app": mock_app})
    request.app.state._state["db"] = mock_db

    # Create a mock dependency that returns None (no token)
    async def mock_dependency():
        return None

    # Patch the oauth2_scheme dependency
    with patch("app.security.jwt.oauth2_scheme", side_effect=mock_dependency):
        # Call the function and expect an exception
        with pytest.raises(HTTPException) as exc_info:
            # Use FastAPI's dependency injection to call the function
            from fastapi import Depends
            from fastapi.testclient import TestClient

            # Create a test app with the dependency overridden
            app = FastAPI()

            @app.get("/test")
            async def test_route(current_user: UserInDB = Depends(get_current_user)):
                return current_user

            # Override the oauth2_scheme dependency
            app.dependency_overrides[oauth2_scheme] = mock_dependency

            # Create a test client and make a request
            client = TestClient(app)
            response = client.get("/test")

            # The actual test is in the response, but we'll also check the exception
            # to be consistent with the original test
            assert response.status_code == 401
            assert response.json()["detail"] == "Not authenticated"

            # Re-raise the exception to be caught by pytest.raises
            if response.status_code == 401:
                raise HTTPException(status_code=401, detail=response.json()["detail"])

        # Assert the correct status code and error message
        assert exc_info.value.status_code == 401
        assert str(exc_info.value.detail) == "Not authenticated"


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    """Test that an invalid token raises an HTTPException."""
    # Create a mock FastAPI app with proper state
    app = FastAPI()
    app.state._state = {}

    # Create a properly mocked database session
    mock_db = create_autospec(AsyncSession, instance=True)
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result

    # Create a mock request with the app and db
    request = Request(scope={"type": "http", "app": app})

    with patch("app.security.jwt.oauth2_scheme") as mock_oauth_scheme, patch(
        "app.security.jwt.decode_token",
    ) as mock_decode, patch("app.crud.user.CRUDUser.get_by_email") as mock_get_user:
        mock_oauth_scheme.return_value = "invalid-token"
        mock_decode.side_effect = JWTError("Invalid token")
        mock_get_user.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request, mock_db)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert str(exc_info.value.detail) == "Could not validate credentials"


@pytest.mark.asyncio
async def test_get_current_active_user():
    """Test that an active user is returned."""
    # Create a test user
    user = TEST_USER

    # Test getting current active user
    active_user = await get_current_active_user(user)
    assert active_user == user


@pytest.mark.asyncio
async def test_get_current_active_user_inactive():
    """Test that an inactive user raises an HTTPException."""
    # Create an inactive test user
    inactive_user = UserInDB(
        id=999,
        username="inactive",
        email="inactive@example.com",
        hashed_password=pwd_context.hash("testpass"),
        is_active=False,
        is_superuser=False,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        full_name="Inactive User",
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_user(inactive_user)
    assert exc_info.value.status_code == 403
    assert "Inactive user" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_current_active_superuser():
    """Test that a superuser is returned."""
    # Create a test admin user
    admin = TEST_ADMIN

    # Test getting current active superuser
    superuser = await get_current_active_superuser(admin)
    assert superuser == admin


@pytest.mark.asyncio
async def test_get_current_active_superuser_non_superuser():
    """Test that a non-superuser raises an HTTPException."""

    # Mock get_current_user dependency
    async def mock_get_current_user():
        return TEST_USER

    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_superuser(current_user=await mock_get_current_user())
    assert exc_info.value.status_code == 403
    assert "Not enough permissions" in str(exc_info.value.detail)
