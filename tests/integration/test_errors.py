from collections.abc import AsyncGenerator

import pytest
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from httpx import AsyncClient
from pydantic import BaseModel


# Mock User model
class User(BaseModel):
    id: int
    email: str
    is_active: bool = True
    is_superuser: bool = False


# Setup test app
app = FastAPI()

# Mock OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Mock get_current_user dependency
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    if token == "valid_token":
        return User(id=1, email="test@example.com")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Add a test route that requires authentication
@app.get("/api/v1/protected-route")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": "Protected route"}


# Add a test route that doesn't exist
@app.get("/")
async def root():
    return {"message": "Root"}


# Test client fixture
@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# Test cases
@pytest.mark.asyncio
async def test_unauthorized_access():
    """Test 401 Unauthorized for protected routes without token."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/protected-route")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Check the response content
        data = response.json()
        assert "detail" in data
        # The actual message might be different, so we'll just
        # check for the presence of the detail field


@pytest.mark.asyncio
async def test_invalid_token():
    """Test 401 with invalid token."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/protected-route",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Check the response content
        data = response.json()
        assert "detail" in data
        # The actual message might be different, so we'll just check
        # for the presence of the detail field


@pytest.mark.asyncio
async def test_not_found():
    """Test 404 Not Found for non-existent resources."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/non-existent-route")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Check the response content
        data = response.json()
        assert "detail" in data
        assert "Not Found" in data["detail"]


@pytest.mark.asyncio
async def test_internal_server_error():
    """Test 500 Internal Server Error."""

    # Create a mock that will raise an exception
    async def mock_get_current_user():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )

    # Override the dependency for this test
    app.dependency_overrides[get_current_user] = mock_get_current_user

    try:
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/protected-route",
                headers={"Authorization": "Bearer valid_token"},
            )
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

            # Check the response content
            data = response.json()
            assert "detail" in data
    finally:
        # Clean up the override
        app.dependency_overrides.clear()
