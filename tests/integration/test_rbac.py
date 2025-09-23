import pytest
from fastapi import status

pytestmark = pytest.mark.asyncio


# Test endpoints that require authentication
async def test_protected_route_requires_auth(async_client):
    """Test that protected routes require authentication."""
    async for client in async_client:
        try:
            # Access protected route without token
            response = await client.post("/api/v1/auth/test-token")
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            break
        except Exception as e:
            print(f"Error during test: {e!s}")
            raise


# Test role-based access control
async def test_authenticated_user_can_access_protected_route(async_client, test_user):
    """Test that an authenticated user can access a protected route."""
    user_data = None
    async for user in test_user:
        user_data = user
        break

    if not user_data:
        pytest.fail("Failed to get test user data")

    async for client in async_client:
        try:
            # First login to get a token
            login_response = await client.post(
                "/api/v1/auth/login/access-token",
                data={"username": user_data["email"], "password": "testpass123"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            assert login_response.status_code == status.HTTP_200_OK
            token_data = login_response.json()

            # Access protected route with valid token
            response = await client.post(
                "/api/v1/auth/test-token",
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "email" in data
            assert data["email"] == user_data["email"]
            break
        except Exception as e:
            print(f"Error during test: {e!s}")
            raise


# Note: The following tests are commented out as they require additional setup
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
