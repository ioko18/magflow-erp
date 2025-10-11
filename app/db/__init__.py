"""COMPATIBILITY LAYER: Re-exports from app.db.session.

FIXED: This module previously created its own engine, causing memory leaks.
Now it re-exports from the canonical source (app.db.session) to ensure
a single connection pool.

For new code, import directly from app.db.session instead.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator, Generator

from sqlalchemy import exc, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import scoped_session

from ..core.config import settings
from .session import (
    AsyncSessionLocal as AsyncSessionFactory,
)
from .session import (
    SessionLocal as SessionFactory,
)

# Import from the canonical source - single connection pool
from .session import (
    async_engine,  # noqa: F401
)
from .session import (
    engine as sync_engine,  # noqa: F401
)

# Configure logging
logger = logging.getLogger(__name__)

# Scoped session for thread safety
Session = scoped_session(SessionFactory)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Async database session dependency.
    Yields a database session and ensures it's properly closed after use.
    """
    async with AsyncSessionFactory() as session:
        try:
            # Get a raw connection to set the search path
            connection = await session.connection()
            await connection.exec_driver_sql(
                f"SET search_path TO {settings.search_path}",
            )

            yield session
            await session.commit()
        except exc.SQLAlchemyError as e:
            logger.error(f"Database error: {e!s}")
            await session.rollback()
            raise


def get_sync_db() -> Generator[Session, None, None]:
    """Synchronous database session dependency.
    For use in sync contexts like migrations.
    """
    db = Session()
    try:
        db.execute(text(f"SET search_path TO {settings.search_path}"))
        db.commit()
        yield db
        db.commit()
    except exc.SQLAlchemyError as e:
        logger.error(f"Database error: {e!s}")
        db.rollback()
        raise
    finally:
        db.close()


async def get_db_session() -> AsyncSession:
    """Return a new async database session.
    Caller should await .close() when finished.
    """
    return AsyncSessionFactory()
