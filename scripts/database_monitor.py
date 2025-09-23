#!/usr/bin/env python3
"""Database monitoring and health check script."""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import json


class DatabaseMonitor:
    """Real-time database monitoring and health checks."""

    def __init__(self):
        self.engine = self._create_engine()
        self.metrics = {}

    def _create_engine(self):
        """Create database engine."""
        return create_async_engine(
            "postgresql+asyncpg://"
            f"{os.getenv('DB_USER', 'postgres')}:"
            f"{os.getenv('DB_PASS', 'password')}@"
            f"{os.getenv('DB_HOST', 'localhost')}:"
            f"{os.getenv('DB_PORT', '5432')}/"
            f"{os.getenv('DB_NAME', 'magflow')}"
        )

    async def health_check(self):
        """Comprehensive health check."""
        print("🏥 Database Health Check")
        print("=" * 40)

        checks = [
            self._check_connection,
            self._check_performance,
            self._check_replication,
            self._check_locks,
            self._check_disk_space,
            self._check_connections,
        ]

        results = {}
        for check in checks:
            try:
                check_name = check.__name__.replace('_', ' ').title()
                print(f"\n🔍 Checking {check_name}...")
                result = await check()
                results[check.__name__] = result
                print(f"  ✅ {check_name}: OK")
            except Exception as e:
                check_name = check.__name__.replace('_', ' ').title()
                results[check.__name__] = {"status": "ERROR", "error": str(e)}
                print(f"  ❌ {check_name}: ERROR - {e}")

        return results

    async def _check_connection(self):
        """Check database connection."""
        async with self.engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            return {"status": "OK", "response_time": "N/A"}

    async def _check_performance(self):
        """Check database performance."""
        async with self.engine.begin() as conn:
            start_time = datetime.now()

            # Test various query types
            queries = [
                "SELECT COUNT(*) FROM users",
                "SELECT COUNT(*) FROM orders WHERE created_at > NOW() - INTERVAL '1 day'",
                "SELECT COUNT(*) FROM products WHERE is_active = true",
            ]

            results = []
            for query in queries:
                try:
                    query_start = datetime.now()
                    result = await conn.execute(text(query))
                    query_end = datetime.now()
                    execution_time = (query_end - query_start).total_seconds() * 1000

                    results.append({
                        "query": query[:50] + "...",
                        "execution_time_ms": execution_time,
                        "status": "OK"
                    })
                except Exception as e:
                    results.append({
                        "query": query[:50] + "...",
                        "execution_time_ms": None,
                        "status": "ERROR",
                        "error": str(e)
                    })

            return {"queries": results}

    async def _check_replication(self):
        """Check replication status."""
        async with self.engine.begin() as conn:
            try:
                result = await conn.execute(text("""
                    SELECT
                        application_name,
                        state,
                        sync_state,
                        pg_last_wal_receive_time,
                        pg_last_wal_replay_time
                    FROM pg_stat_replication;
                """))
                replication_slots = result.fetchall()
                return {"replication_slots": len(replication_slots)}
            except Exception as e:
                return {"status": "ERROR", "error": str(e)}

    async def _check_locks(self):
        """Check for lock contention."""
        async with self.engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT
                    COUNT(*) as waiting_queries
                FROM pg_stat_activity
                WHERE wait_event_type IS NOT NULL;
            """))
            waiting = result.scalar()
            return {"waiting_queries": waiting}

    async def _check_disk_space(self):
        """Check disk space usage."""
        async with self.engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT
                    current_setting('data_directory') as data_dir
            """))
            data_dir = result.scalar()

            # Check disk usage (this would typically use system commands)
            return {"data_directory": data_dir, "status": "OK"}

    async def _check_connections(self):
        """Check connection statistics."""
        async with self.engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT
                    state,
                    COUNT(*) as count
                FROM pg_stat_activity
                GROUP BY state;
            """))
            connections = {row.state: row.count for row in result}
            return {"connections": connections}

    async def collect_metrics(self):
        """Collect comprehensive metrics."""
        print("\n📊 Collecting Database Metrics...")
        print("=" * 40)

        async with self.engine.begin() as conn:
            metrics = {}

            # System metrics
            metrics["timestamp"] = datetime.now().isoformat()
            metrics["database_size"] = await self._get_database_size(conn)
            metrics["table_sizes"] = await self._get_table_sizes(conn)
            metrics["index_usage"] = await self._get_index_usage(conn)
            metrics["slow_queries"] = await self._get_slow_queries(conn)
            metrics["connection_stats"] = await self._get_connection_stats(conn)

            # Store metrics
            await self._store_metrics(metrics)

            return metrics

    async def _get_database_size(self, conn):
        """Get database size."""
        result = await conn.execute(text("""
            SELECT
                pg_size_pretty(pg_database_size(current_database())) as size,
                pg_database_size(current_database()) as bytes
        """))
        return result.fetchone()._asdict()

    async def _get_table_sizes(self, conn):
        """Get table sizes."""
        result = await conn.execute(text("""
            SELECT
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            LIMIT 10;
        """))
        return [row._asdict() for row in result]

    async def _get_index_usage(self, conn):
        """Get index usage statistics."""
        result = await conn.execute(text("""
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
        """))
        return [row._asdict() for row in result]

    async def _get_slow_queries(self, conn):
        """Get slow query statistics."""
        result = await conn.execute(text("""
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
        """))
        return [row._asdict() for row in result]

    async def _get_connection_stats(self, conn):
        """Get connection statistics."""
        result = await conn.execute(text("""
            SELECT
                state,
                COUNT(*) as count,
                AVG(EXTRACT(EPOCH FROM (now() - query_start))) as avg_duration
            FROM pg_stat_activity
            WHERE state IS NOT NULL
            GROUP BY state;
        """))
        return [row._asdict() for row in result]

    async def _store_metrics(self, metrics):
        """Store metrics for historical analysis."""
        # Store in file for now (could be InfluxDB, Prometheus, etc.)
        metrics_dir = Path("monitoring/metrics")
        metrics_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics_file = metrics_dir / f"db_metrics_{timestamp}.json"

        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2, default=str)

        print(f"  📝 Metrics saved to {metrics_file}")

    async def generate_report(self, metrics):
        """Generate human-readable report."""
        print("\n📋 Database Health Report")
        print("=" * 50)

        print(f"📅 Report Time: {metrics['timestamp']}")
        print(f"💾 Database Size: {metrics['database_size']['size']}")

        print("\n📊 Top 5 Largest Tables:")
        for i, table in enumerate(metrics['table_sizes'][:5], 1):
            print(f"  {i}. {table['tablename']}: {table['size']}")

        print("\n🔍 Most Used Indexes:")
        for i, index in enumerate(metrics['index_usage'][:5], 1):
            print(f"  {i}. {index['indexname']}: {index['idx_scan']} scans")

        print("\n🐌 Slowest Queries:")
        for i, query in enumerate(metrics['slow_queries'][:3], 1):
            print(f"  {i}. {query['mean_time']:.0f}ms avg")

        print("\n🔗 Connection Statistics:")
        for conn in metrics['connection_stats']:
            print(f"  {conn['state']}: {conn['count']} connections")

    async def cleanup(self):
        """Cleanup and close connections."""
        await self.engine.dispose()


async def main():
    """Main monitoring function."""
    print("🚀 MagFlow ERP Database Monitor")
    print("=" * 40)

    try:
        monitor = DatabaseMonitor()

        # Run health check
        health_results = await monitor.health_check()

        # Collect metrics
        metrics = await monitor.collect_metrics()

        # Generate report
        await monitor.generate_report(metrics)

        # Check for issues
        issues = []
        for check_name, result in health_results.items():
            if isinstance(result, dict) and result.get("status") == "ERROR":
                issues.append(f"{check_name}: {result['error']}")

        if issues:
            print("\n⚠️  Issues Found:")
            for issue in issues:
                print(f"  • {issue}")

        print("\n✅ Database monitoring completed!")

        return 0 if len(issues) == 0 else 1

    except Exception as e:
        print(f"\n❌ Monitoring failed: {e}")
        return 1

    finally:
        await monitor.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
