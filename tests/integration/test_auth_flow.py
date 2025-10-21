import pytest
from fastapi import status

# This tells pytest to treat all test functions as async
pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_successful_login(client, create_test_user):
    """Test successful login with valid credentials."""
    # Get the test user from the database
    test_user = create_test_user

    # Make the login request
    login_data = {
        "username": test_user["email"],
        "password": test_user["password"],
    }

    response = await client.post(
        "/api/v1/auth/login",
        json=login_data,
        headers={"Content-Type": "application/json"},
    )

    # Assert the response
    assert response.status_code == status.HTTP_200_OK, f"Login failed: {response.text}"
    data = response.json()
    assert "access_token" in data, "Access token not in response"
    assert "token_type" in data, "Token type not in response"
    assert data["token_type"].lower() == "bearer", "Token type is not 'bearer'"
    assert len(data["access_token"]) > 0, "Access token is empty"


@pytest.mark.asyncio
async def test_invalid_credentials(client, create_test_user):
    """Test login with invalid credentials."""
    # Get the test user from the database
    test_user = create_test_user

    login_data = {
        "username": test_user["email"],
        "password": "wrongpassword",
    }

    response = await client.post(
        "/api/v1/auth/login",
        json=login_data,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Incorrect email or password" in response.text


@pytest.mark.asyncio
async def test_refresh_token(client, create_test_user):
    """Test token refresh flow."""
    # Get the test user from the database
    test_user = create_test_user

    # First, log in to get a refresh token
    login_data = {
        "username": test_user["email"],
        "password": test_user["password"],
    }

    login_response = await client.post(
        "/api/v1/auth/login",
        json=login_data,
        headers={"Content-Type": "application/json"},
    )

    assert login_response.status_code == status.HTTP_200_OK
    refresh_token = login_response.json()["refresh_token"]

    # Now try to refresh the token using the bearer token contract
    response = await client.post(
        "/api/v1/auth/refresh-token",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )

    # Assert the response
    assert (
        response.status_code == status.HTTP_200_OK
    ), f"Refresh failed: {response.text}"
    data = response.json()
    assert "access_token" in data, "Access token not in refresh response"
    assert "token_type" in data, "Token type not in refresh response"
    assert data["token_type"].lower() == "bearer", "Token type is not 'bearer'"
    assert len(data["access_token"]) > 0, "Access token from refresh is empty"


@pytest.mark.asyncio
async def test_refresh_token_rejects_invalid_payload(client, create_test_user):
    """Refresh endpoint should reject requests without a bearer token."""

    response = await client.post("/api/v1/auth/refresh-token", json={"refresh_token": "bad-token"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Could not validate refresh token" in response.text


@pytest.mark.asyncio
async def test_key_rotation(client, create_test_user, monkeypatch):
    """Test that key rotation works correctly."""
    # Get the test user from the database
    test_user = create_test_user

    # First, log in to get a token
    login_data = {
        "username": test_user["email"],
        "password": test_user["password"],
    }

    # Get the current keys
    from app.security.keys import get_current_key, get_public_keys

    old_key = get_current_key()

    # Mock the key rotation to happen immediately
    from datetime import timedelta

    # Set the key to expire in the past to force rotation
    monkeypatch.setattr(
        "app.security.keys.KEY_ROTATION_INTERVAL",
        timedelta(seconds=-1),
    )

    # Make a request to trigger key rotation
    response = await client.post(
        "/api/v1/auth/login",
        json=login_data,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == status.HTTP_200_OK

    # Get the new key
    new_key = get_current_key()

    # Verify a new key was generated
    assert old_key.kid != new_key.kid, "Key was not rotated"

    # Verify the old key is still in the public keys (for verification of existing tokens)
    public_keys = await get_public_keys()
    assert any(k.kid == old_key.kid for k in public_keys), "Old key not in public keys"


@pytest.mark.asyncio
async def test_expired_token(client, create_test_user):
    """Test that an expired access token is properly rejected."""
    # Get the test user from the database
    test_user = create_test_user

    # Create an expired token
    from datetime import timedelta

    from app.security.jwt import create_access_token

    # Create a token that expired 1 second ago
    expired_token = create_access_token(
        subject=test_user["email"],
        expires_delta=timedelta(seconds=-1),  # Expired 1 second ago
    )

    # Try to use the expired token
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    # Should return 401 Unauthorized
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Token has expired" in response.text
    assert "expired" in response.json().get("detail", "").lower()
