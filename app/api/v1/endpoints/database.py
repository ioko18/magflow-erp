"""Database management endpoints."""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.db_health import (
    check_database_migrations,
    get_connection_pool_stats,
    get_database_health,
)

router = APIRouter()


@router.get("/health")
async def database_health(
    db: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """Get detailed database health information.

    Returns comprehensive database health status including connection details,
    schema access, and PostgreSQL version information.
    """
    try:
        return await get_database_health(db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database health check failed: {e!s}",
        )


@router.get("/migrations")
async def database_migrations(
    db: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """Get database migration status.

    Returns information about the current migration revision and status.
    """
    try:
        return await check_database_migrations(db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration status check failed: {e!s}",
        )


@router.get("/connection-pool")
async def connection_pool_stats(
    db: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """Get database connection pool statistics.

    Returns information about active connections and pool usage.
    """
    try:
        return await get_connection_pool_stats(db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get connection pool stats: {e!s}",
        )
