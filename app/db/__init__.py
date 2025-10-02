from __future__ import annotations

import logging
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine, exc, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import NullPool

from ..core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Create async engine with advanced connection pooling
async_engine = create_async_engine(
    settings.DB_URI,
    echo=settings.ENVIRONMENT == "development",
    # Connection pooling optimization
    pool_size=settings.db_pool_size,  # Default 20
    max_overflow=settings.db_max_overflow,  # Default 30
    pool_timeout=settings.db_pool_timeout,  # Timeout for getting connection
    pool_recycle=settings.db_pool_recycle,  # Recycle connections
    pool_pre_ping=False,  # FIXED: Disable pre-ping for async engines to avoid greenlet issues
    pool_reset_on_return="commit",  # Reset connections on return
    # Performance optimizations
    future=True,
    # Connection arguments for performance
    connect_args={
        "server_settings": {
            "application_name": "magflow-api",
            "work_mem": "256MB",  # Increase working memory for complex queries
            "maintenance_work_mem": "512MB",  # Increase maintenance memory
            "effective_cache_size": "4GB",  # Optimize for PostgreSQL planner
            "statement_timeout": f"{settings.db_command_timeout}s",  # Timeout for queries
        },
        "prepared_statement_cache_size": 500,  # Cache prepared statements
        "command_timeout": settings.db_command_timeout,  # Timeout for long-running queries
    },
)

# Create async session factory with optimizations
AsyncSessionFactory = sessionmaker(
    async_engine,  # Use the async engine defined above
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
    # Query optimization settings
    query_cls=None,  # Use default query class for now
)

# Create sync engine for migrations and other sync operations
sync_engine = create_engine(
    settings.alembic_url.replace("+asyncpg", ""),  # Use sync driver for migrations
    poolclass=NullPool,
    pool_pre_ping=False,  # FIXED: Disable pre-ping to avoid greenlet issues
    pool_recycle=300,
)

# Sync session factory for migrations
SessionFactory = sessionmaker(
    bind=sync_engine,
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


async def get_db_session() -> AsyncSession:
    """Return a new async database session.
    Caller should await .close() when finished.
    """
    return AsyncSessionFactory()
