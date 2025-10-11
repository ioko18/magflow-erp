"""Database connection health checks and resilience patterns.

This module provides utilities for ensuring database connectivity
and implementing automatic retry logic for failed operations.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..core.config import settings
from ..core.exceptions import ConnectionServiceError, DatabaseError

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration and connection management."""

    @staticmethod
    def create_optimized_engine():
        """Create optimized database engine with proper configuration."""
        return create_async_engine(
            settings.DB_URI,
            # Connection pool settings
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pool_pre_ping=settings.DB_POOL_PRE_PING,
            # Performance settings
            echo=settings.DB_ECHO,
            future=True,
        )

    @staticmethod
    def create_test_engine():
        """Create test database engine."""
        return create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
            future=True,
        )


class DatabaseHealthChecker:
    """Database connection health checker with automatic retry logic."""

    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self._is_healthy = True
        self._last_check = None
        self._detailed_health_info = {}

    async def check_health(self) -> bool:
        """Check database connectivity and update health status."""
        try:
            async with self.db_session_factory() as session:
                # 1. Schema Access Verification
                await session.execute(text("SET search_path TO app, public"))
                schema_check = await session.execute(
                    text(
                        "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'app'",
                    ),
                )
                if schema_check.scalar_one_or_none() is None:
                    raise DatabaseError("Schema 'app' not accessible.")

                # 2. PostgreSQL Version Detection
                version_check = await session.execute(text("SHOW server_version"))
                pg_version = version_check.scalar_one()

                # 3. Basic Connectivity
                await session.execute(text("SELECT 1"))
                await session.commit()

            self._is_healthy = True
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                import time

                self._last_check = time.time()
            else:
                self._last_check = loop.time()
            self._detailed_health_info = {
                "status": "healthy",
                "postgres_version": pg_version,
                "schema_accessible": True,
                "last_check": self._last_check,
            }
            return True

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            self._is_healthy = False
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                import time

                self._last_check = time.time()
            else:
                self._last_check = loop.time()
            self._detailed_health_info = {
                "status": "unhealthy",
                "error": str(e),
                "last_check": self._last_check,
            }
            return False

    async def get_detailed_health(self) -> dict:
        """Return detailed health information."""
        await self.check_health()
        return self._detailed_health_info

    async def ensure_healthy(self) -> None:
        """Ensure database is healthy, raise exception if not."""
        if not await self.check_health():
            raise ConnectionServiceError(
                "Database connection is not available",
                details={"last_check": self._last_check},
            )

    @property
    def is_healthy(self) -> bool:
        """Check if database is currently healthy."""
        return self._is_healthy


async def resilient_db_operation(
    operation: Callable,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    backoff_factor: float = 2.0,
) -> Any:
    """Execute database operation with automatic retry logic.

    Args:
        operation: Async function to execute
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries (seconds)
        backoff_factor: Exponential backoff multiplier

    Returns:
        Result of the operation

    Raises:
        DatabaseError: If operation fails after all retries

    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await operation()
        except Exception as e:
            last_exception = e

            if attempt == max_retries:
                logger.error(f"Operation failed after {max_retries} retries: {e}")
                raise DatabaseError(
                    f"Database operation failed: {e!s}",
                    details={"attempts": attempt + 1, "max_retries": max_retries},
                ) from e

            # Calculate delay with exponential backoff
            delay = retry_delay * (backoff_factor**attempt)
            logger.warning(
                f"Database operation failed (attempt {attempt + 1}), retrying in {delay}s: {e}",
            )
            await asyncio.sleep(delay)

    # This should never be reached, but just in case
    raise DatabaseError(
        "Unexpected error in resilient_db_operation",
    ) from last_exception


@asynccontextmanager
async def resilient_db_session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions with automatic retry and recovery.

    Usage:
        async with resilient_db_session(session_factory) as session:
            result = await session.execute(query)
    """
    retry_state = AsyncRetrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ConnectionServiceError, DatabaseError)),
        reraise=True,
    )

    async for attempt in retry_state:
        with attempt:
            try:
                async with session_factory() as session:
                    yield session
                    await session.commit()
                    break
            except Exception as e:
                await session.rollback()
                raise DatabaseError(f"Database session failed: {e}") from e
