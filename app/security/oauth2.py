"""OAuth2 integration for third-party authentication providers."""

import secrets
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from ..core.config import settings
from ..schemas.user import UserCreate, UserInDB
from ..security.jwt import (
    create_access_token,
    create_refresh_token,
    get_current_active_user,
)

router = APIRouter(prefix="/oauth", tags=["oauth"])


# OAuth2 providers configuration
OAUTH_PROVIDERS = {
    "google": {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "authorize_url": "https://accounts.google.com/o/oauth2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "user_info_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scope": "openid email profile",
        "response_type": "code",
    },
    "github": {
        "client_id": settings.GITHUB_CLIENT_ID,
        "client_secret": settings.GITHUB_CLIENT_SECRET,
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "user_info_url": "https://api.github.com/user",
        "scope": "user:email",
        "response_type": "code",
    },
}


class OAuth2Service:
    """Service for handling OAuth2 authentication with various providers."""

    def __init__(self):
        self.state_store: dict[str, dict[str, Any]] = {}
        self.state_timeout = 600  # 10 minutes

    def generate_state(self) -> str:
        """Generate a secure random state parameter."""
        return secrets.token_urlsafe(32)

    def store_state(self, state: str, provider: str, redirect_uri: str) -> None:
        """Store OAuth2 state with expiration."""
        self.state_store[state] = {
            "provider": provider,
            "redirect_uri": redirect_uri,
            "created_at": datetime.now(),
        }

    def get_and_validate_state(self, state: str) -> dict[str, Any] | None:
        """Get and validate OAuth2 state."""
        if state not in self.state_store:
            return None

        state_data = self.state_store[state]

        # Check if state has expired
        if datetime.now() - state_data["created_at"] > timedelta(
            seconds=self.state_timeout,
        ):
            del self.state_store[state]
            return None

        # Remove state from store (one-time use)
        del self.state_store[state]
        return state_data

    def get_authorization_url(
        self,
        provider: str,
        redirect_uri: str,
        state: str,
    ) -> str:
        """Generate OAuth2 authorization URL."""
        provider_config = OAUTH_PROVIDERS.get(provider)
        if not provider_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported OAuth2 provider: {provider}",
            )

        params = {
            "client_id": provider_config["client_id"],
            "redirect_uri": redirect_uri,
            "scope": provider_config["scope"],
            "response_type": provider_config["response_type"],
            "state": state,
        }

        return f"{provider_config['authorize_url']}?{urlencode(params)}"

    async def exchange_code_for_token(
        self,
        provider: str,
        code: str,
        redirect_uri: str,
    ) -> dict[str, Any]:
        """Exchange authorization code for access token."""
        provider_config = OAUTH_PROVIDERS.get(provider)
        if not provider_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported OAuth2 provider: {provider}",
            )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                provider_config["token_url"],
                data={
                    "client_id": provider_config["client_id"],
                    "client_secret": provider_config["client_secret"],
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
                headers={"Accept": "application/json"},
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to exchange code for token",
                )

            return response.json()

    async def get_user_info(self, provider: str, access_token: str) -> dict[str, Any]:
        """Get user information from OAuth2 provider."""
        provider_config = OAUTH_PROVIDERS.get(provider)
        if not provider_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported OAuth2 provider: {provider}",
            )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                provider_config["user_info_url"],
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get user information",
                )

            return response.json()

    def map_provider_user_to_user(
        self,
        provider: str,
        user_info: dict[str, Any],
    ) -> UserCreate:
        """Map OAuth2 provider user info to our User model."""
        if provider == "google":
            return UserCreate(
                email=user_info["email"],
                full_name=user_info.get("name", user_info["email"]),
                password="",  # OAuth2 users don't have passwords
                is_active=True,
                is_superuser=False,
                oauth_provider=provider,
                oauth_id=user_info["id"],
            )
        if provider == "github":
            return UserCreate(
                email=user_info["email"] or f"{user_info['id']}@github",
                full_name=user_info.get("name", user_info["login"]),
                password="",
                is_active=True,
                is_superuser=False,
                oauth_provider=provider,
                oauth_id=str(user_info["id"]),
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider mapping: {provider}",
        )


# Global OAuth2 service instance
oauth_service = OAuth2Service()


@router.get("/{provider}/login")
async def oauth_login(provider: str, request: Request):
    """Initiate OAuth2 login flow."""
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth2 provider: {provider}",
        )

    # Generate state for CSRF protection
    state = oauth_service.generate_state()

    # Store state with provider info
    redirect_uri = str(request.url_for("oauth_callback", provider=provider))
    oauth_service.store_state(state, provider, redirect_uri)

    # Generate authorization URL
    auth_url = oauth_service.get_authorization_url(provider, redirect_uri, state)

    return RedirectResponse(url=auth_url)


@router.get("/{provider}/callback")
async def oauth_callback(provider: str, request: Request, code: str, state: str):
    """Handle OAuth2 callback."""
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth2 provider: {provider}",
        )

    # Validate state parameter
    state_data = oauth_service.get_and_validate_state(state)
    if not state_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state parameter",
        )

    try:
        # Exchange code for token
        token_data = await oauth_service.exchange_code_for_token(
            provider,
            code,
            state_data["redirect_uri"],
        )

        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No access token received",
            )

        # Get user information
        user_info = await oauth_service.get_user_info(provider, access_token)

        # Map to our user model
        user_create = oauth_service.map_provider_user_to_user(provider, user_info)

        # Create or get existing user (in a real app, you'd check the database)
        # For now, create a JWT token as if the user exists
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            subject=user_create.email,
            expires_delta=access_token_expires,
            additional_claims={
                "email": user_create.email,
                "full_name": user_create.full_name,
                "oauth_provider": provider,
                "oauth_id": user_info["id"],
                "type": "access",
            },
        )

        # Create refresh token
        refresh_token = create_refresh_token(
            subject=user_create.email,
            expires_delta=timedelta(days=settings.refresh_token_expire_days),
        )

        # Redirect back to frontend with tokens
        frontend_url = settings.FRONTEND_URL or "http://localhost:3000"
        redirect_url = (
            f"{frontend_url}/auth/callback?"
            f"access_token={access_token}&"
            f"refresh_token={refresh_token}&"
            f"token_type=bearer&"
            f"expires_in={int(access_token_expires.total_seconds())}"
        )

        return RedirectResponse(url=redirect_url)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth2 authentication failed: {e!s}",
        )


@router.get("/{provider}/userinfo")
async def get_oauth_user_info(
    provider: str,
    current_user: UserInDB = Depends(get_current_active_user),
):
    """Get OAuth2 user information for the current user."""
    if not current_user.oauth_provider or current_user.oauth_provider != provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not authenticated with this OAuth2 provider",
        )

    # In a real app, you'd fetch fresh user info from the provider
    # For now, return what we have
    return {
        "provider": current_user.oauth_provider,
        "oauth_id": current_user.oauth_id,
        "email": current_user.email,
        "full_name": current_user.full_name,
    }
