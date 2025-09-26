"""Database session management for the application.

This module provides utilities for managing database sessions, including
synchronous and asynchronous session factories, as well as a dependency
for FastAPI to get a database session.
"""

from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _get_async_database_uri() -> str:
    """Return async-capable database URI.

    Settings in this project expose `SQLALCHEMY_DATABASE_URI` (which may
    already be async) and separate pool parameters. Some environments do not
    define an explicit `ASYNC_DATABASE_URI`, so we fall back gracefully to the
    primary URI.
    """

    async_uri = getattr(settings, "ASYNC_DATABASE_URI", None)
    if async_uri:
        return async_uri
    return settings.SQLALCHEMY_DATABASE_URI

# Create synchronous engine for legacy code
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    connect_args={"options": "-c timezone=utc"},
)

# Create async engine
async_engine = create_async_engine(
    _get_async_database_uri(),
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    connect_args={"server_settings": {"timezone": "utc"}},
)

# Create session factories
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=async_engine, expire_on_commit=False
)

def get_db() -> Generator[Session, None, None]:
    """Get a synchronous database session.

    Yields:
        Session: A database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session.

    Yields:
        AsyncSession: An async database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
