#!/usr/bin/env python3
"""Database maintenance and monitoring script."""

import asyncio
import sys
from sqlalchemy import text
from app.core.database_config import DatabaseConfig


class DatabaseMaintenance:
    """Database maintenance utilities."""

    def __init__(self):
        self.engine = DatabaseConfig.create_optimized_engine()

    async def analyze_database(self):
        """Comprehensive database analysis."""
        print("🔍 Database Analysis Report")
        print("=" * 50)

        async with self.engine.begin() as conn:
            # Table sizes
            await self._analyze_table_sizes(conn)

            # Index usage
            await self._analyze_index_usage(conn)

            # Slow queries
            await self._analyze_slow_queries(conn)

            # Connection statistics
            await self._analyze_connections(conn)

            # Database configuration
            await self._analyze_configuration(conn)

    async def _analyze_table_sizes(self, conn):
        """Analyze table sizes."""
        print("\n📊 Table Sizes:")
        query = """
        SELECT
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
            pg_total_relation_size(schemaname||'.'||tablename) as bytes
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        LIMIT 20;
        """
        try:
            result = await conn.execute(text(query))
            for row in result:
                print(f"  {row.tablename}: {row.size}")
        except Exception as e:
            print(f"  Error analyzing table sizes: {e}")

    async def _analyze_index_usage(self, conn):
        """Analyze index usage."""
        print("\n📈 Index Usage:")
        query = """
        SELECT
            schemaname,
            tablename,
            indexname,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch
        FROM pg_stat_user_indexes
        ORDER BY idx_scan DESC
        LIMIT 10;
        """
        try:
            result = await conn.execute(text(query))
            for row in result:
                efficiency = (row.idx_tup_fetch / row.idx_tup_read * 100) if row.idx_tup_read > 0 else 0
                print(f"  {row.indexname}: {row.idx_scan} scans, {efficiency:.1f}% efficiency")
        except Exception as e:
            print(f"  Error analyzing index usage: {e}")

    async def _analyze_slow_queries(self, conn):
        """Analyze slow queries."""
        print("\n🐌 Slow Queries:")
        query = """
        SELECT
            query,
            calls,
            total_time,
            mean_time,
            rows
        FROM pg_stat_statements
        WHERE mean_time > 100
        ORDER BY mean_time DESC
        LIMIT 10;
        """
        try:
            result = await conn.execute(text(query))
            for row in result:
                print(f"  {row.mean_time:.0f}ms avg: {row.query[:100]}...")
        except Exception as e:
            print(f"  Error analyzing slow queries: {e}")

    async def _analyze_connections(self, conn):
        """Analyze connection statistics."""
        print("\n🔗 Connection Statistics:")
        query = """
        SELECT
            state,
            COUNT(*) as count
        FROM pg_stat_activity
        GROUP BY state;
        """
        try:
            result = await conn.execute(text(query))
            for row in result:
                print(f"  {row.state}: {row.count} connections")
        except Exception as e:
            print(f"  Error analyzing connections: {e}")

    async def _analyze_configuration(self, conn):
        """Analyze database configuration."""
        print("\n⚙️  Configuration Analysis:")
        config_items = [
            "shared_buffers",
            "effective_cache_size",
            "work_mem",
            "maintenance_work_mem",
            "max_connections"
        ]

        for item in config_items:
            try:
                result = await conn.execute(text(f"SHOW {item};"))
                value = result.scalar()
                print(f"  {item}: {value}")
            except Exception as e:
                print(f"  Error checking {item}: {e}")

    async def optimize_database(self):
        """Perform database optimizations."""
        print("\n🔧 Database Optimization")
        print("=" * 30)

        async with self.engine.begin() as conn:
            # Analyze all tables
            await self._run_analyze(conn)

            # Reindex if needed
            await self._reindex_tables(conn)

            # Vacuum analyze
            await self._vacuum_analyze(conn)

    async def _run_analyze(self, conn):
        """Run ANALYZE on all tables."""
        print("  📊 Running ANALYZE...")
        try:
            await conn.execute(text("ANALYZE;"))
            print("  ✅ ANALYZE completed")
        except Exception as e:
            print(f"  ❌ ANALYZE failed: {e}")

    async def _reindex_tables(self, conn):
        """Reindex tables if needed."""
        print("  🔄 Reindexing tables...")
        query = """
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename NOT LIKE 'pg_%';
        """
        try:
            result = await conn.execute(text(query))
            tables = [row.tablename for row in result]

            for table in tables:
                await conn.execute(text(f"REINDEX TABLE {table};"))
                print(f"    Reindexed: {table}")

            print("  ✅ Reindexing completed")
        except Exception as e:
            print(f"  ❌ Reindexing failed: {e}")

    async def _vacuum_analyze(self, conn):
        """Run VACUUM ANALYZE."""
        print("  🧹 Running VACUUM ANALYZE...")
        try:
            await conn.execute(text("VACUUM ANALYZE;"))
            print("  ✅ VACUUM ANALYZE completed")
        except Exception as e:
            print(f"  ❌ VACUUM ANALYZE failed: {e}")

    async def cleanup(self):
        """Cleanup and close connections."""
        await self.engine.dispose()


async def main():
    """Main function."""
    print("🚀 MagFlow ERP Database Maintenance")
    print("=" * 40)

    try:
        maintenance = DatabaseMaintenance()

        # Run analysis
        await maintenance.analyze_database()

        # Run optimizations
        await maintenance.optimize_database()

        print("\n✅ Database maintenance completed successfully!")

    except Exception as e:
        print(f"\n❌ Error during maintenance: {e}")
        return 1

    finally:
        await maintenance.cleanup()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
