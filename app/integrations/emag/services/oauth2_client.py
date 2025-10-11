"""OAuth2 Client for eMAG API Authentication.

Provides OAuth2 authentication flow for eMAG API with:
- Authorization code flow
- Token refresh
- Token storage and management
- Automatic token renewal
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import aiohttp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.emag_oauth_token import EmagOAuthToken

logger = logging.getLogger(__name__)


class OAuth2Client:
    """OAuth2 client for eMAG API authentication."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        authorization_url: str,
        token_url: str,
        scope: str | None = None,
    ):
        """Initialize OAuth2 client.

        Args:
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            redirect_uri: Redirect URI for authorization callback
            authorization_url: URL for authorization endpoint
            token_url: URL for token endpoint
            scope: Optional OAuth2 scope
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.authorization_url = authorization_url
        self.token_url = token_url
        self.scope = scope or ""

        self._session: aiohttp.ClientSession | None = None
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expiry: datetime | None = None

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def get_authorization_url(self, state: str | None = None) -> str:
        """Generate authorization URL for user consent.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            str: Authorization URL
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": self.scope,
        }

        if state:
            params["state"] = state

        return f"{self.authorization_url}?{urlencode(params)}"

    async def exchange_code_for_token(
        self,
        code: str,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Exchange authorization code for access token.

        Args:
            code: Authorization code from callback
            db: Database session for storing token

        Returns:
            Dict containing access_token, refresh_token, expires_in, etc.

        Raises:
            Exception: If token exchange fails
        """
        session = await self.get_session()

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        try:
            async with session.post(self.token_url, data=data) as response:
                response.raise_for_status()
                token_data = await response.json()

                # Store token data
                self._access_token = token_data.get("access_token")
                self._refresh_token = token_data.get("refresh_token")

                expires_in = token_data.get("expires_in", 3600)
                self._token_expiry = datetime.now(UTC) + timedelta(
                    seconds=expires_in
                )

                # Save to database if session provided
                if db:
                    await self._save_token_to_db(db, token_data)

                logger.info("Successfully exchanged authorization code for token")
                return token_data

        except aiohttp.ClientError as e:
            logger.error(f"Failed to exchange code for token: {e}")
            raise

    async def refresh_access_token(
        self,
        refresh_token: str | None = None,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token (uses stored token if not provided)
            db: Database session for updating token

        Returns:
            Dict containing new access_token, refresh_token, expires_in, etc.

        Raises:
            Exception: If token refresh fails
        """
        token = refresh_token or self._refresh_token

        if not token:
            raise ValueError("No refresh token available")

        session = await self.get_session()

        data = {
            "grant_type": "refresh_token",
            "refresh_token": token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        try:
            async with session.post(self.token_url, data=data) as response:
                response.raise_for_status()
                token_data = await response.json()

                # Update token data
                self._access_token = token_data.get("access_token")
                self._refresh_token = token_data.get("refresh_token", token)

                expires_in = token_data.get("expires_in", 3600)
                self._token_expiry = datetime.now(UTC) + timedelta(
                    seconds=expires_in
                )

                # Update database if session provided
                if db:
                    await self._save_token_to_db(db, token_data)

                logger.info("Successfully refreshed access token")
                return token_data

        except aiohttp.ClientError as e:
            logger.error(f"Failed to refresh token: {e}")
            raise

    async def get_valid_access_token(
        self,
        db: AsyncSession | None = None,
    ) -> str:
        """Get a valid access token, refreshing if necessary.

        Args:
            db: Database session for loading/updating token

        Returns:
            str: Valid access token

        Raises:
            Exception: If unable to get valid token
        """
        # Load token from database if not in memory
        if not self._access_token and db:
            await self._load_token_from_db(db)

        # Check if token is expired or about to expire (within 5 minutes)
        if self._token_expiry:
            expires_soon = datetime.now(UTC) + timedelta(minutes=5)
            if self._token_expiry <= expires_soon:
                logger.info("Access token expired or expiring soon, refreshing...")
                await self.refresh_access_token(db=db)

        if not self._access_token:
            raise ValueError("No valid access token available")

        return self._access_token

    async def _save_token_to_db(
        self,
        db: AsyncSession,
        token_data: dict[str, Any],
    ) -> None:
        """Save OAuth token to database.

        Args:
            db: Database session
            token_data: Token data from OAuth provider
        """
        try:
            # Check if token exists
            result = await db.execute(
                select(EmagOAuthToken).where(EmagOAuthToken.client_id == self.client_id)
            )
            token = result.scalar_one_or_none()

            expires_in = token_data.get("expires_in", 3600)
            expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)

            if token:
                # Update existing token
                token.access_token = token_data.get("access_token")
                token.refresh_token = token_data.get(
                    "refresh_token", token.refresh_token
                )
                token.expires_at = expires_at
                token.token_type = token_data.get("token_type", "Bearer")
                token.scope = token_data.get("scope", self.scope)
            else:
                # Create new token
                token = EmagOAuthToken(
                    client_id=self.client_id,
                    access_token=token_data.get("access_token"),
                    refresh_token=token_data.get("refresh_token"),
                    expires_at=expires_at,
                    token_type=token_data.get("token_type", "Bearer"),
                    scope=token_data.get("scope", self.scope),
                )
                db.add(token)

            await db.commit()
            logger.debug("Token saved to database")

        except Exception as e:
            logger.error(f"Failed to save token to database: {e}")
            await db.rollback()

    async def _load_token_from_db(self, db: AsyncSession) -> None:
        """Load OAuth token from database.

        Args:
            db: Database session
        """
        try:
            result = await db.execute(
                select(EmagOAuthToken).where(EmagOAuthToken.client_id == self.client_id)
            )
            token = result.scalar_one_or_none()

            if token:
                self._access_token = token.access_token
                self._refresh_token = token.refresh_token
                self._token_expiry = token.expires_at
                logger.debug("Token loaded from database")
            else:
                logger.warning("No token found in database")

        except Exception as e:
            logger.error(f"Failed to load token from database: {e}")


class EmagOAuth2Client(OAuth2Client):
    """OAuth2 client specifically for eMAG API."""

    def __init__(self):
        """Initialize eMAG OAuth2 client with configuration from settings."""
        super().__init__(
            client_id=getattr(settings, "EMAG_OAUTH_CLIENT_ID", ""),
            client_secret=getattr(settings, "EMAG_OAUTH_CLIENT_SECRET", ""),
            redirect_uri=getattr(settings, "EMAG_OAUTH_REDIRECT_URI", ""),
            authorization_url=getattr(
                settings,
                "EMAG_OAUTH_AUTHORIZATION_URL",
                "https://marketplace-api.emag.ro/oauth/authorize",
            ),
            token_url=getattr(
                settings,
                "EMAG_OAUTH_TOKEN_URL",
                "https://marketplace-api.emag.ro/oauth/token",
            ),
            scope=getattr(settings, "EMAG_OAUTH_SCOPE", "read write"),
        )


# Global eMAG OAuth2 client instance
emag_oauth_client = EmagOAuth2Client()
