from __future__ import annotations

import logging
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine, exc, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import NullPool

from .core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Create async engine with PgBouncer
engine = create_async_engine(
    settings.DB_URI,
    echo=settings.ENVIRONMENT == "development",
    pool_pre_ping=True,
    pool_recycle=300,  # Recycle connections after 5 minutes
    connect_args={"server_settings": {"application_name": "magflow-api"}},
)

# Create async session factory
AsyncSessionFactory = sessionmaker(
    engine,  # Use the engine variable defined above
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Create sync engine for migrations and other sync operations
engine = create_engine(
    settings.alembic_url.replace("+asyncpg", ""),  # Use sync driver for migrations
    poolclass=NullPool,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Sync session factory for migrations
SessionFactory = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

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


def get_db_session() -> AsyncSession:
    """Return a new async database session.
    Caller should await .close() when finished.
    """
    return AsyncSessionFactory()
