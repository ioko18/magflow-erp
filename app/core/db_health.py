"""Database health check utilities."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)


async def get_database_health(session: AsyncSession) -> Dict[str, Any]:
    """Get comprehensive database health status using the centralized health checker."""
    from app.core.database import health_checker

    return await health_checker.get_detailed_health()


async def get_connection_pool_stats(db: AsyncSession) -> Dict[str, Any]:
    """Get database connection pool statistics."""
    try:
        # Query PostgreSQL for connection statistics
        result = await db.execute(
            text(
                """
            SELECT
                count(*) as active_connections,
                count(*) FILTER (WHERE state = 'active') as active_queries,
                count(*) FILTER (WHERE state = 'idle') as idle_connections,
                max(extract(epoch from (now() - backend_start))) as oldest_connection_seconds
            FROM pg_stat_activity
            WHERE application_name = 'magflow-api'
        """,
            ),
        )
        stats = dict(result.mappings().first() or {})

        return {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pool_config": {
                "pool_size": settings.DB_POOL_SIZE,
                "max_overflow": settings.DB_MAX_OVERFLOW,
                "pool_timeout": settings.DB_POOL_TIMEOUT,
                "pool_recycle": settings.DB_POOL_RECYCLE,
            },
            "active_stats": stats,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get connection pool stats: {e!s}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


async def check_database_migrations(session: AsyncSession) -> Dict[str, Any]:
    """Check database migration status.

    Args:
        session: Database session

    Returns:
        Dict with migration status information

    """
    try:
        # Check if alembic_version table exists
        result = await session.execute(
            text(
                """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'app' AND table_name = 'alembic_version'
            )
        """,
            ),
        )
        table_exists = result.scalar()

        if not table_exists:
            return {
                "status": "unknown",
                "message": "Alembic version table not found",
                "current_revision": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # Get current revision
        result = await session.execute(
            text("SELECT version_num FROM app.alembic_version"),
        )
        current_revision = result.scalar()

        return {
            "status": "success" if current_revision else "unknown",
            "message": "Migration information retrieved successfully",
            "current_revision": current_revision,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to check migration status: {e}")
        return {
            "status": "error",
            "message": f"Failed to check migration status: {e!s}",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
