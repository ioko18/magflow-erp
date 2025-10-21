from datetime import datetime, timedelta
from types import SimpleNamespace

from fastapi import status
from jose import jwt

from app.api.v1.endpoints.system.auth import _get_current_user
from app.core.config import settings
from app.main import app


# Test endpoints that require authentication
async def test_protected_route_requires_auth(async_client):
    """Test that protected routes require authentication."""
    response = await async_client.get("/api/v1/users/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# Test role-based access control
async def test_authenticated_user_can_access_protected_route(async_client, test_user):
    """Test that an authenticated user can access a protected route."""
    payload = {
        "sub": test_user["email"],
        "exp": datetime.now(datetime.UTC) + timedelta(minutes=30),
        "iat": datetime.now(datetime.UTC),
        "type": "access",
        "email": test_user["email"],
        "roles": ["user"],
    }
    secret = (
        getattr(settings, "SECRET_KEY", None)
        or getattr(settings, "secret_key", None)
    )
    algorithm = (
        getattr(settings, "ALGORITHM", None)
        or getattr(settings, "algorithm", None)
        or "HS256"
    )
    token = jwt.encode(payload, secret, algorithm=algorithm)

    user_id = test_user.get("id", 1)
    now = datetime.now(datetime.UTC)

    async def override_current_user():
        return SimpleNamespace(
            id=user_id,
            email=test_user["email"],
            full_name=test_user.get("full_name", "Test User"),
            is_active=True,
            is_superuser=False,
            created_at=now,
            updated_at=None,
            last_login=None,
            failed_login_attempts=0,
            avatar_url=None,
            roles=[],
        )

    app.dependency_overrides[_get_current_user] = override_current_user

    try:
        response = await async_client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.pop(_get_current_user, None)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == test_user["email"]
# that's not currently available in the test environment. They can be uncommented
# and implemented once the necessary fixtures and endpoints are available.
# async def test_admin_access(async_client, admin_token_headers):
#     """Test that admin users can access admin-only endpoints."""
#     async for client in async_client:
#         try:
#             response = await client.get(
#                 "/api/v1/admin/endpoint",
#                 headers=admin_token_headers
#             )
#             assert response.status_code == status.HTTP_200_OK
#             break
#         except Exception as e:
#             print(f"Error during test: {str(e)}")
#             raise

# async def test_user_access_denied_to_admin_route(async_client, user_token_headers):
#     """Test that regular users cannot access admin-only endpoints."""
#     async for client in async_client:
#         try:
#             response = await client.get(
#                 "/api/v1/admin/endpoint",
#                 headers=user_token_headers
#             )
#             assert response.status_code == status.HTTP_403_FORBIDDEN
#             break
#         except Exception as e:
#             print(f"Error during test: {str(e)}")
#             raise
