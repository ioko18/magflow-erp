from fastapi import APIRouter
import asyncpg
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/observability", tags=["observability"])


async def _get_pgb_connection() -> asyncpg.Connection:
    """Create direct asyncpg connection to PgBouncer admin."""
    user = os.getenv("DB_USER", "app")
    pwd = os.getenv("DB_PASS", "app_password_change_me")
    host = "pgbouncer"
    port = int(os.getenv("PGB_PORT", "6432"))
    
    try:
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=pwd,
            database="pgbouncer",
            timeout=5.0,  # Connection timeout in seconds
            command_timeout=5.0,  # Query timeout in seconds
        )
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to PgBouncer: {e}")
        raise


async def _execute_query_safe(conn: asyncpg.Connection, query: str) -> List[Dict[str, Any]]:
    """Execute a PgBouncer query safely and return normalized results."""
    try:
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]
    except Exception as e:
        logger.warning(f"Query '{query}' failed: {e}")
        return []


@router.get("/pool")
async def get_pool_stats():
    """Get comprehensive PgBouncer statistics including stats, averages, totals, pools, and file descriptors."""
    # Initialize response with all required keys
    response = {"stats": [], "averages": [], "totals": [], "pools": [], "fds": []}

    try:
        conn = await _get_pgb_connection()
        try:
            # Execute all 5 required queries
            response["stats"] = await _execute_query_safe(conn, "SHOW STATS")
            response["averages"] = await _execute_query_safe(conn, "SHOW STATS_AVERAGES")

            # Try both STATS_TOTALS and TOTALS (some versions use different names)
            totals = await _execute_query_safe(conn, "SHOW STATS_TOTALS")
            if not totals:
                totals = await _execute_query_safe(conn, "SHOW TOTALS")
            response["totals"] = totals

            response["pools"] = await _execute_query_safe(conn, "SHOW POOLS")
            response["fds"] = await _execute_query_safe(conn, "SHOW FDS")
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Error connecting to PgBouncer admin: {e}")
        # Return 200 with empty lists as requested, rather than raising HTTPException
        logger.warning("Returning empty response due to connection error")
        return response
