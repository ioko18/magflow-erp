"""Database utilities with real PostgreSQL connection."""

from typing import AsyncGenerator

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..core.database_resilience import DatabaseConfig, DatabaseHealthChecker
from ..core.exceptions import DatabaseError
from sqlalchemy.orm import declarative_base

# Declarative base for ORM models
Base = declarative_base()

# Create the async engine
engine = DatabaseConfig.create_optimized_engine()

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create health checker
health_checker = DatabaseHealthChecker(async_session_factory)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Async database session dependency.
    Yields a session and ensures proper cleanup.
    """
    """Get an async database session."""
    # TODO: Re-enable health check after fixing the issue
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
        finally:
            await session.close()


# Alias for compatibility with existing imports in tests
get_db = get_async_session

# Test database engine for development/testing
test_engine = DatabaseConfig.create_test_engine()
test_session_factory = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
