"""
Tests for authentication API endpoints.

This module contains tests for the authentication-related API endpoints.
"""
import pytest
from fastapi import status
from httpx import AsyncClient

from app.core.config import settings

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: dict):
    """Test successful user login."""
    login_data = {
        "username": test_user["email"],
        "password": "testpassword"
    }
    response = await client.post(
        f"{settings.API_V1_STR}/auth/login",
        data=login_data
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """Test login with invalid credentials."""
    login_data = {
        "username": "nonexistent@example.com",
        "password": "wrongpassword"
    }
    response = await client.post(
        f"{settings.API_V1_STR}/auth/login",
        data=login_data
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Incorrect username or password" in response.json()["detail"]

@pytest.mark.asyncio
async def test_read_users_me(
    client: AsyncClient,
    auth_headers: dict,
    test_user: dict
):
    """Test retrieving current user information."""
    response = await client.get(
        f"{settings.API_V1_STR}/users/me",
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == test_user["email"]
    assert "hashed_password" not in data
    assert "id" in data

@pytest.mark.asyncio
async def test_read_users_me_unauthorized(client: AsyncClient):
    """Test accessing protected endpoint without authentication."""
    response = await client.get(f"{settings.API_V1_STR}/users/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_refresh_token(
    client: AsyncClient,
    test_user: dict,
    auth_headers: dict
):
    """Test refreshing access token."""
    # First get a refresh token by logging in
    login_data = {
        "username": test_user["email"],
        "password": "testpassword"
    }
    login_response = await client.post(
        f"{settings.API_V1_STR}/auth/login",
        data=login_data
    )
    refresh_token = login_response.json().get("refresh_token")
    
    # Now use the refresh token to get a new access token
    response = await client.post(
        f"{settings.API_V1_STR}/auth/refresh-token",
        headers={"Authorization": f"Bearer {refresh_token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
