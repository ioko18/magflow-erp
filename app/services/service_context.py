"""Service context for managing shared resources and dependencies.

This module provides a central place to manage shared resources like database
sessions, caches, and other service dependencies that need to be shared across
different parts of the application.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class ServiceContext:
    """Container for shared service dependencies and resources.

    This class acts as a dependency injection container that can be used to share
    resources like database sessions, caches, and other services across the application.
    """

    def __init__(
        self,
        db_session: AsyncSession | None = None,
        cache: Any | None = None,
        settings: Any | None = None,
    ):
        """Initialize the service context with optional dependencies.

        Args:
            db_session: Optional SQLAlchemy async session for database access.
            cache: Optional cache client (e.g., Redis).
            settings: Optional application settings.
        """
        self._db_session = db_session
        self._cache = cache
        self._settings = settings

    @property
    def db_session(self) -> AsyncSession | None:
        """Get the database session."""
        return self._db_session

    @db_session.setter
    def db_session(self, session: AsyncSession) -> None:
        """Set the database session."""
        self._db_session = session

    @property
    def cache(self) -> Any | None:
        """Get the cache client."""
        return self._cache

    @cache.setter
    def cache(self, cache: Any) -> None:
        """Set the cache client."""
        self._cache = cache

    @property
    def settings(self) -> Any | None:
        """Get the application settings."""
        return self._settings

    @settings.setter
    def settings(self, settings: Any) -> None:
        """Set the application settings."""
        self._settings = settings

    async def close(self) -> None:
        """Close any resources held by this context."""
        if self._db_session is not None:
            await self._db_session.close()
            self._db_session = None

        if self._cache is not None and hasattr(self._cache, "close"):
            await self._cache.close()
            self._cache = None

    def __del__(self):
        """Ensure resources are cleaned up when the context is garbage collected."""
        import asyncio

        if self._db_session is not None or self._cache is not None:
            try:
                loop = asyncio.get_running_loop()
                # Schedule cleanup task in the running loop
                if loop.is_running():
                    loop.create_task(self.close())
            except RuntimeError:
                # No running loop - resources will be cleaned up by garbage collector
                # This is acceptable in __del__ as we can't reliably create event loops here
                pass
