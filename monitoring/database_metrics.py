"""
Database metrics collection and monitoring for MagFlow ERP.

This module provides functionality to collect and expose database performance metrics
for monitoring and alerting purposes.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, TypedDict

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession

# Configuration is loaded through environment variables
from app.db.session import get_async_engine

# Constants
METRICS_CACHE_TTL = 30  # seconds
LONG_RUNNING_THRESHOLD = 300  # 5 minutes in seconds
HEALTH_CHECK_TIMEOUT = 10  # seconds

logger = logging.getLogger(__name__)

# Global variable to store pool metrics
pool_metrics = {
    "checkouts": 0,
    "checkins": 0,
    "connections_created": 0,
    "connections_closed": 0,
    "pool_size": 0,
    "overflow": 0,
    "last_updated": None,
    "errors": 0,
    "wait_time": 0.0,
    "avg_wait_time": 0.0,
}

# Cache for expensive queries
_metrics_cache = {}
_cache_timestamps = {}


def _get_cached_metrics(key: str, ttl: int = METRICS_CACHE_TTL) -> tuple[Any, bool]:
    """Get cached metrics if they exist and are not expired."""
    now = time.time()
    if key in _metrics_cache and (now - _cache_timestamps.get(key, 0)) < ttl:
        return _metrics_cache[key], True
    return None, False


def _set_cached_metrics(key: str, value: Any) -> None:
    """Store metrics in cache with current timestamp."""
    _metrics_cache[key] = value
    _cache_timestamps[key] = time.time()


class DatabaseMetrics(TypedDict, total=False):
    """Type definition for database metrics dictionary."""

    active_connections: int
    max_connections: int
    connection_utilization: float
    total_transactions: int
    active_transactions: int
    idle_in_transaction: int
    long_running_queries: list[dict[str, Any]]
    table_sizes: list[dict[str, Any]]
    index_usage: list[dict[str, Any]]
    cache_hit_ratio: float
    collection_time_ms: float
    error: str | None


async def collect_database_metrics(
    session: AsyncSession, use_cache: bool = True
) -> DatabaseMetrics:
    """Collect comprehensive database metrics with caching support.

    Args:
        session: Database session to use for collecting metrics
        use_cache: Whether to use cached metrics if available

    Returns:
        Dictionary containing database metrics
    """
    cache_key = f"db_metrics_{session.bind.url.database}"
    metrics: DatabaseMetrics = {}

    if use_cache:
        cached, is_valid = _get_cached_metrics(cache_key)
        if is_valid and cached:
            return cached

    start_time = time.monotonic()
    is_sqlite = session.bind.dialect.name == "sqlite"

    try:
        async with asyncio.timeout(HEALTH_CHECK_TIMEOUT):
            if is_sqlite:
                # SQLite-specific metrics
                try:
                    result = await session.execute(text("PRAGMA database_list;"))
                    db_list = result.fetchall()
                    metrics["databases"] = [dict(row) for row in db_list]
                except Exception as e:
                    logger.warning("Failed to get SQLite database list: %s", str(e))
            else:
                # PostgreSQL-specific metrics
                try:
                    # Get connection and transaction metrics
                    conn_metrics = await session.execute(
                        text("""
                        SELECT
                            COUNT(*) as total_connections,
                            COUNT(*) FILTER
                                (WHERE state = 'active') as active_connections,
                            COUNT(*) FILTER
                                (WHERE state = 'idle') as idle_connections,
                            COUNT(*) FILTER (
                                WHERE state = 'idle in transaction'
                            ) as idle_in_transaction,
                            COUNT(*) FILTER (
                                WHERE state = 'idle in transaction (aborted)'
                            ) as aborted_transactions,
                            COUNT(*) FILTER (
                                WHERE state = 'fastpath function call'
                            ) as function_calls,
                            COUNT(*) FILTER
                                (WHERE state = 'disabled') as disabled_connections,
                            COUNT(*) FILTER (
                                WHERE state = 'active'
                                AND query_start < NOW() - INTERVAL '5 minutes'
                            ) as long_running_queries
                        FROM pg_stat_activity
                        WHERE pid != pg_backend_pid()
                        """)
                    )

                    metrics.update(dict(conn_metrics.fetchone()._mapping))

                    # Get table sizes and bloat
                    table_sizes = await session.execute(
                        text("""
                        SELECT
                            schemaname as schema,
                            relname as table_name,
                            n_live_tup as row_estimate,
                            pg_size_pretty(
                                pg_total_relation_size(
                                    quote_ident(schemaname) || '.' || quote_ident(relname)
                                )
                            ) as total_size,
                            pg_size_pretty(
                                pg_relation_size(
                                    quote_ident(schemaname) || '.' || quote_ident(relname)
                                )
                            ) as table_size,
                            pg_size_pretty(
                                pg_total_relation_size(
                                    quote_ident(schemaname) || '.' || quote_ident(relname)
                                )
                                - pg_relation_size(
                                    quote_ident(schemaname) || '.' || quote_ident(relname)
                                )
                            ) as index_size,
                            pg_stat_get_last_autovacuum_time(c.oid) as last_vacuum,
                            pg_stat_get_last_autoanalyze_time(c.oid) as last_analyze
                        FROM pg_stat_user_tables t
                        JOIN pg_class c ON c.relname = t.relname
                        WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                        ORDER BY pg_total_relation_size(
                            quote_ident(schemaname) || '.' || quote_ident(relname)
                        ) DESC
                        LIMIT 20;
                        """)
                    )
                    metrics["table_sizes"] = [dict(row._mapping) for row in table_sizes]

                    # Get index usage statistics
                    index_usage = await session.execute(
                        text("""
                        SELECT
                            schemaname as schema,
                            relname as table_name,
                            indexrelname as index_name,
                            idx_scan as index_scans,
                            idx_tup_read as tuples_read,
                            idx_tup_fetch as tuples_fetched,
                            pg_size_pretty(
                                pg_relation_size(quote_ident(indexrelid)::regclass)
                            ) as index_size
                        FROM pg_stat_user_indexes
                        WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                        ORDER BY idx_scan DESC NULLS LAST
                        LIMIT 20;
                        """)
                    )
                    metrics["index_usage"] = [dict(row._mapping) for row in index_usage]

                    # Get cache hit ratio
                    cache_stats = await session.execute(
                        text("""
                        SELECT
                            sum(heap_blks_read) as heap_read,
                            sum(heap_blks_hit) as heap_hit,
                            sum(heap_blks_hit) / nullif(
                                sum(heap_blks_hit) + sum(heap_blks_read),
                                0
                            ) as hit_ratio
                        FROM pg_statio_user_tables;
                        """)
                    )
                    cache_row = cache_stats.fetchone()
                    if cache_row:
                        metrics["cache_hit_ratio"] = (
                            float(cache_row.hit_ratio or 0) * 100
                        )

                except Exception as e:
                    logger.error(
                        "Error collecting PostgreSQL metrics: %s", str(e), exc_info=True
                    )
                    metrics["error"] = f"Error collecting metrics: {str(e)}"

            # Calculate collection time
            metrics["collection_time_ms"] = (time.monctime() - start_time) * 1000

            # Update cache
            _set_cached_metrics(cache_key, metrics)

            return metrics

    except TimeoutError:
        logger.warning(
            "Database metrics collection timed out after %s seconds",
            HEALTH_CHECK_TIMEOUT,
        )
        metrics["error"] = (
            f"Metrics collection timed out after {HEALTH_CHECK_TIMEOUT} seconds"
        )
        return metrics
    except Exception as e:
        logger.error(
            "Unexpected error collecting database metrics: %s", str(e), exc_info=True
        )
        metrics["error"] = f"Unexpected error: {str(e)}"
        return metrics


async def get_database_health_status(
    session: AsyncSession | None = None,
) -> dict[str, Any]:
    """Get a comprehensive health status of the database.

    Args:
        session: Optional database session to use. If not provided, a new one will be created.

    Returns:
        Dictionary containing database health status
    """
    close_session = False
    try:
        if session is None:
            from app.db.session import get_async_session

            session = await get_async_session()
            close_session = True

        is_sqlite = session.bind.dialect.name == "sqlite"

        if is_sqlite:
            return await _get_sqlite_health_status(session)
        else:
            return await _get_postgresql_health_status(session)

    except Exception as e:
        logger.error("Error getting database health status: %s", str(e), exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
    finally:
        if close_session and session is not None:
            await session.close()


async def _get_postgresql_health_status(session: AsyncSession) -> dict[str, Any]:
    """Get health status for PostgreSQL database."""
    try:
        metrics = await collect_database_metrics(session)

        # Check for critical issues
        is_healthy = True
        issues = []

        # Check connection utilization
        max_connections = metrics.get("max_connections")
        active_connections = metrics.get("active_connections", 0)
        if max_connections and active_connections > max_connections * 0.9:
            issues.append(
                "High connection utilization: "
                f"{active_connections}/{max_connections} connections in use"
            )
            is_healthy = False

        # Check for long-running transactions
        long_running = metrics.get("long_running_queries", 0)
        if long_running > 0:
            issues.append(f"{long_running} long-running queries detected")
            is_healthy = False

        # Check for idle in transaction
        idle_in_transaction = metrics.get("idle_in_transaction", 0)
        if idle_in_transaction > 0:
            issues.append(f"{idle_in_transaction} idle in transaction connections")
            is_healthy = False

        # Check cache hit ratio
        cache_hit_ratio = metrics.get("cache_hit_ratio", 100)
        if cache_hit_ratio < 90:  # Less than 90% cache hit ratio
            issues.append(f"Low cache hit ratio: {cache_hit_ratio:.1f}%")
            is_healthy = False

        # Get blocking locks if any
        blocking_locks = await _get_blocking_locks(session)
        if blocking_locks:
            issues.append(f"{len(blocking_locks)} blocking locks detected")
            is_healthy = False

        return {
            "status": "healthy" if is_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "active_connections": active_connections,
                "max_connections": max_connections,
                "connection_utilization": (active_connections / max_connections * 100)
                if max_connections
                else 0,
                "idle_in_transaction": idle_in_transaction,
                "long_running_queries": long_running,
                "cache_hit_ratio": cache_hit_ratio,
                "blocking_locks": blocking_locks[:10],  # Limit to top 10
            },
            "issues": issues if issues else None,
        }

    except Exception as e:
        logger.error(
            "Error getting PostgreSQL health status: %s", str(e), exc_info=True
        )
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


async def _get_sqlite_health_status(session: AsyncSession) -> dict[str, Any]:
    """Get health status for SQLite database."""
    try:
        # Simple health check for SQLite
        await session.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "SQLite database is accessible",
        }
    except Exception as e:
        logger.error("Error getting SQLite health status: %s", str(e), exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


async def _get_blocking_locks(session: AsyncSession) -> list[dict[str, Any]]:
    """Get blocking locks from PostgreSQL."""
    try:
        query = """
        SELECT
            blocked_locks.pid AS blocked_pid,
            blocked_activity.usename AS blocked_user,
            blocking_locks.pid AS blocking_pid,
            blocking_activity.usename AS blocking_user,
            blocked_activity.query AS blocked_statement,
            blocking_activity.query AS blocking_statement,
            blocked_activity.application_name AS blocked_application,
            blocking_activity.application_name AS blocking_application,
            now() - blocked_activity.query_start AS blocked_duration,
            now() - blocking_activity.query_start AS blocking_duration,
            blocked_activity.state AS blocked_state,
            blocking_activity.state AS blocking_state
        FROM pg_catalog.pg_locks blocked_locks
        JOIN pg_catalog.pg_stat_activity blocked_activity
            ON blocked_activity.pid = blocked_locks.pid
        JOIN pg_catalog.pg_locks blocking_locks
            ON blocking_locks.locktype = blocked_locks.locktype
            AND blocking_locks.DATABASE IS NOT DISTINCT FROM blocked_locks.DATABASE
            AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
            AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
            AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
            AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
            AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
            AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
            AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
            AND blocking_locks.objsubid = blocked_locks.objsubid
            AND blocking_locks.pid != blocked_locks.pid
        JOIN pg_catalog.pg_stat_activity blocking_activity
            ON blocking_activity.pid = blocking_locks.pid
        WHERE NOT blocked_locks.GRANTED;
        """

        result = await session.execute(text(query))
        return [dict(row._mapping) for row in result]
    except Exception as e:
        logger.error("Error getting blocking locks: %s", str(e), exc_info=True)
        return []


def setup_pool_monitoring():
    """Set up event listeners for connection pool monitoring with enhanced metrics."""
    engine = get_async_engine()

    @event.listens_for(engine.sync_engine, "checkout")
    def on_checkout(dbapi_connection, connection_record, connection_proxy):
        start_time = time.time()
        connection_record._checkout_time = start_time
        pool_metrics["checkouts"] += 1
        pool_metrics["last_updated"] = datetime.utcnow().isoformat()
        logger.debug("Database connection checked out")

    @event.listens_for(engine.sync_engine, "checkin")
    def on_checkin(dbapi_connection, connection_record):
        pool_metrics["checkins"] += 1
        pool_metrics["last_updated"] = datetime.utcnow().isoformat()

        # Calculate wait time if checkout time was recorded
        if hasattr(connection_record, "_checkout_time"):
            wait_time = time.time() - connection_record._checkout_time
            pool_metrics["wait_time"] += wait_time
            pool_metrics["avg_wait_time"] = (
                pool_metrics["wait_time"] / pool_metrics["checkins"]
            )

        logger.debug("Database connection checked in")

    @event.listens_for(engine.sync_engine, "connect")
    def on_connect(dbapi_connection, connection_record):
        pool_metrics["connections_created"] += 1
        pool_metrics["last_updated"] = datetime.utcnow().isoformat()
        logger.debug("New database connection created")

    @event.listens_for(engine.sync_engine, "close")
    def on_close(dbapi_connection, connection_record):
        pool_metrics["connections_closed"] += 1
        pool_metrics["last_updated"] = datetime.utcnow().isoformat()
        logger.debug("Database connection closed")

    @event.listens_for(engine.sync_engine, "handle_error")
    def on_error(exception_context):
        pool_metrics["errors"] += 1
        pool_metrics["last_updated"] = datetime.utcnow().isoformat()
        logger.error(
            "Database error: %s",
            str(exception_context.original_exception),
            exc_info=exception_context.original_exception,
        )


# Initialize pool monitoring when module is imported
setup_pool_monitoring()


async def main():
    """Run the main application with proper async context."""
    try:
        # Initialize database connection
        import json

        from app.db.session import get_async_session

        async with get_async_session() as session:
            # Example: Get database health status
            health = await get_database_health_status(session)
            print("\nDatabase Health Status:")
            print(json.dumps(health, indent=2, default=str))

            # Example: Collect detailed metrics
            metrics = await collect_database_metrics(session)
            print("\nDatabase Metrics:")
            print(
                "- Active Connections: {}".format(
                    metrics.get("active_connections", "N/A")
                )
            )
            print(
                "- Connection Utilization: {:.1f}%".format(
                    metrics.get("connection_utilization", 0)
                )
            )
            print("- Table Count: {}".format(len(metrics.get("table_sizes", []))))

    except Exception as e:
        logger.error("Error in main: %s", str(e), exc_info=True)
        raise


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
