"""Database optimization and improvement strategies."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class DatabaseOptimization:
    """Database optimization utilities and best practices."""

    @staticmethod
    async def analyze_query_performance(session: AsyncSession, query: str):
        """Analyze query performance using EXPLAIN ANALYZE.

        WARNING: This method should only be used with trusted query strings.
        Do not pass user input directly to this method.
        """
        # Note: EXPLAIN ANALYZE cannot use parameterized queries
        # This is a utility for internal analysis only
        result = await session.execute(text(f"EXPLAIN ANALYZE {query}"))
        return result.fetchall()

    @staticmethod
    async def get_table_statistics(session: AsyncSession, table_name: str):
        """Get table statistics for optimization."""
        # Use parameterized query to prevent SQL injection
        stats_query = """
        SELECT
            schemaname,
            tablename,
            attname,
            n_distinct,
            correlation
        FROM pg_stats
        WHERE tablename = :table_name;
        """
        result = await session.execute(text(stats_query), {"table_name": table_name})
        return result.fetchall()

    @staticmethod
    async def get_index_usage(session: AsyncSession):
        """Get index usage statistics."""
        index_query = """
        SELECT
            schemaname,
            tablename,
            indexname,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch
        FROM pg_stat_user_indexes
        ORDER BY idx_scan DESC;
        """
        result = await session.execute(text(index_query))
        return result.fetchall()

    @staticmethod
    async def get_slow_queries(session: AsyncSession):
        """Get slow query statistics."""
        slow_query = """
        SELECT
            query,
            calls,
            total_time,
            mean_time,
            rows
        FROM pg_stat_statements
        WHERE mean_time > 100  -- Queries taking more than 100ms
        ORDER BY mean_time DESC
        LIMIT 20;
        """
        result = await session.execute(text(slow_query))
        return result.fetchall()


class TestDatabasePerformance:
    """Performance testing for database operations."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_connection_pool_efficiency(self, test_db_session):
        """Test database connection pool efficiency."""
        # This would test connection pool settings
        # Monitor connection usage, pool hits/misses, etc.

    @pytest.mark.asyncio
    async def test_query_optimization(self, test_db_session):
        """Test that queries are optimized."""
        # Test common query patterns for optimization opportunities

    @pytest.mark.asyncio
    async def test_index_effectiveness(self, test_db_session):
        """Test index effectiveness."""
        # Test that indexes are being used efficiently
