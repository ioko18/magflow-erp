"""Database utilities with real PostgreSQL connection.

COMPATIBILITY LAYER: This module now re-exports from app.db.session to ensure
a single source of truth for database connections. This prevents multiple
connection pools and memory leaks.

For new code, prefer importing directly from app.db.session:
    from app.db.session import get_async_db, AsyncSessionLocal
"""

from collections.abc import AsyncGenerator

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base

from ..core.database_resilience import DatabaseHealthChecker
from ..core.exceptions import DatabaseError
from ..db.session import (
    AsyncSessionLocal as async_session_factory,
)

# Import from the canonical source
from ..db.session import (
    async_engine as engine,  # noqa: F401 - Re-exported for compatibility
)
from ..db.session import (
    get_async_db,  # noqa: F401 - Re-exported for compatibility
)

# Declarative base for ORM models
Base = declarative_base()

# Create health checker with the shared session factory
health_checker = DatabaseHealthChecker(async_session_factory)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Async database session dependency.
    Yields a session and ensures proper cleanup.

    Note: The async context manager (async with) automatically handles session
    cleanup, so we don't need to manually call session.close() in finally.
    """
    # Note: Health check is disabled to avoid circular dependency issues
    # Consider implementing a separate health check endpoint if needed
    # await health_checker.ensure_healthy()

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except HTTPException:
            await session.rollback()
            raise
        except SQLAlchemyError as e:
            await session.rollback()
            raise DatabaseError(f"Database session error: {e!s}") from e
        except Exception:
            await session.rollback()
            raise


# Alias for compatibility with existing imports in tests
get_db = get_async_session

# Test database utilities are now available from app.db.session
# For test engine, import directly: from app.db.session import async_engine
# This prevents creating duplicate connection pools
