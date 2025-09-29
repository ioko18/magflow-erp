"""
Simple Performance Monitor for MagFlow ERP
==========================================

A lightweight, robust performance monitoring solution that:
1. Tracks test execution times and performance metrics
2. Provides simple database connection management
3. Generates comprehensive performance reports
4. Avoids complex asyncio patterns that cause issues
5. Focuses on reliability and ease of use

This is the production-ready solution for MagFlow ERP test performance monitoring.
"""

import time
import json
import statistics
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

import asyncio
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine


@dataclass
class SimpleMetrics:
    """Simple performance metrics tracking."""

    test_names: List[str] = field(default_factory=list)
    test_times: List[float] = field(default_factory=list)
    setup_times: List[float] = field(default_factory=list)
    execution_times: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)

    def add_test(
        self, name: str, total_time: float, setup_time: float = 0.0, error: str = None
    ):
        """Add test metrics."""
        self.test_names.append(name)
        self.test_times.append(total_time)
        self.setup_times.append(setup_time)
        self.execution_times.append(total_time - setup_time)

        if error:
            self.errors.append(f"{name}: {error}")

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        if not self.test_times:
            return {"status": "no_data"}

        return {
            "total_tests": len(self.test_times),
            "avg_test_time": statistics.mean(self.test_times),
            "avg_setup_time": statistics.mean(self.setup_times),
            "avg_execution_time": statistics.mean(self.execution_times),
            "total_errors": len(self.errors),
            "slowest_test": max(
                zip(self.test_names, self.test_times), key=lambda x: x[1]
            ),
            "fastest_test": min(
                zip(self.test_names, self.test_times), key=lambda x: x[1]
            ),
            "total_runtime": time.time() - self.start_time,
            "performance_score": self._calculate_score(),
        }

    def _calculate_score(self) -> float:
        """Calculate performance score (0-100)."""
        if not self.test_times:
            return 0.0

        avg_time = statistics.mean(self.test_times)
        error_ratio = len(self.errors) / len(self.test_times)

        # Base score: faster tests = higher score
        time_score = max(0, 100 - (avg_time * 50))  # 2s = 0 points, 0s = 100 points

        # Penalty for errors
        error_penalty = error_ratio * 30

        return max(0, min(100, time_score - error_penalty))


class SimplePerformanceMonitor:
    """Simple, reliable performance monitor."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.metrics = SimpleMetrics()
        self._engine: Optional[AsyncEngine] = None
        self._schema_ready = False
        self._loop_id: Optional[int] = None
        self._test_data_cache = {}
        self._pool_settings = {
            "pool_size": 10,  # Increased pool size for parallel test execution
            "max_overflow": 20,  # Allow more connections during peak
            "pool_timeout": 30,  # Wait up to 30s for a connection
            "pool_recycle": 3600,  # Recycle connections after 1 hour
            "pool_pre_ping": True,  # Check connection health
            "echo": False,  # Disable SQL echo for performance
        }

    async def get_engine(self) -> AsyncEngine:
        """Get database engine."""
        current_loop = asyncio.get_running_loop()
        current_loop_id = id(current_loop)

        # Recreate engine if no engine or event loop changed between tests
        if self._engine is None or self._loop_id != current_loop_id:
            if self._engine is not None:
                try:
                    await self._engine.dispose()
                except Exception:
                    pass
            # Create engine with optimized settings for testing
            self._engine = create_async_engine(
                self.database_url,
                **self._pool_settings,
                # Use server-side cursors for better memory efficiency
                execution_options={
                    "isolation_level": "READ COMMITTED",
                    "compiled_cache": None,  # Disable SQL compilation cache
                },
            )
            self._loop_id = current_loop_id
        return self._engine

    async def ensure_schema(self):
        """Ensure database schema exists with optimized table creation."""
        if not self._schema_ready:
            try:
                from app.db.base_class import Base
                from sqlalchemy.schema import CreateSchema

                engine = await self.get_engine()

                async with engine.begin() as conn:
                    # Create schema if not exists
                    await conn.execute(CreateSchema("public", if_not_exists=True))

                    # Only drop and create tables if they don't match expected schema
                    inspector = await conn.run_sync(
                        lambda sync_conn: inspect(sync_conn.engine)
                    )
                    existing_tables = set(inspector.get_table_names())
                    expected_tables = set(Base.metadata.tables.keys())

                    if existing_tables != expected_tables:
                        await conn.run_sync(Base.metadata.drop_all)
                        await conn.run_sync(Base.metadata.create_all)
                    else:
                        # Just clear data without dropping tables
                        for table in reversed(Base.metadata.sorted_tables):
                            await conn.execute(table.delete())

                    await conn.commit()

                self._schema_ready = True
                print("✅ Database schema verified and ready")
            except Exception as e:
                print(f"❌ Schema initialization failed: {e}")
                raise

    @asynccontextmanager
    async def get_session(self):
        """Get database session with optimized connection handling."""
        engine = await self.get_engine()
        await self.ensure_schema()

        connection = None
        session = None
        transaction = None

        try:
            # Get connection from pool
            connection = await engine.connect()

            # Start a transaction
            transaction = await connection.begin()

            # Create session with optimized settings
            session = AsyncSession(
                bind=connection,
                expire_on_commit=False,
                autoflush=False,
                future=True,
                enable_baked_queries=True,
            )

            try:
                yield session
                await session.commit()
                await transaction.commit()
            except Exception as exc:
                await transaction.rollback()
                await session.rollback()
                print(f"⚠️  Error in session: {str(exc)}")
                raise exc
            finally:
                await session.close()

        except Exception as exc:
            print(f"⚠️  Error establishing connection: {str(exc)}")
            if transaction and not transaction.is_active:
                try:
                    await transaction.rollback()
                except Exception:
                    pass
            raise exc
        finally:
            if connection and not connection.closed:
                # Return connection to pool instead of closing it
                await connection.close()

    async def get_cached_test_data(self, key: str, factory, *args, **kwargs):
        """Get or create test data with caching."""
        if key not in self._test_data_cache:
            self._test_data_cache[key] = await factory(*args, **kwargs)
        return self._test_data_cache[key]

    def start_test(self, test_name: str) -> Dict[str, Any]:
        """Start monitoring a test."""
        return {"name": test_name, "start_time": time.time()}

    async def end_test(self, test_context: Dict[str, Any], error: str = None):
        """End test monitoring."""
        try:
            total_time = time.time() - test_context["start_time"]
            setup_time = test_context.get("setup_time", 0.0)

            self.metrics.add_test(test_context["name"], total_time, setup_time, error)

            status = "✅" if not error else "❌"
            print(f"{status} {test_context['name']}: {total_time:.3f}s")

            # Do not dispose engine here; fixture/cleanup manages lifecycle to avoid
            # leaving a disposed engine referenced between tests.

        except Exception as e:
            print(f"⚠️  Error in end_test: {str(e)}")
            raise

    def generate_report(self) -> str:
        """Generate performance report."""
        summary = self.metrics.get_summary()

        if summary.get("status") == "no_data":
            return "📊 No performance data available"

        report = f"""
🚀 MagFlow ERP Performance Report
{'='*50}

📈 Performance Summary:
  • Total Tests: {summary['total_tests']}
  • Average Test Time: {summary['avg_test_time']:.3f}s
  • Average Setup Time: {summary['avg_setup_time']:.3f}s
  • Performance Score: {summary['performance_score']:.1f}/100
  • Total Runtime: {summary['total_runtime']:.2f}s

🏆 Test Performance:
  • Slowest: {summary['slowest_test'][0]} ({summary['slowest_test'][1]:.3f}s)
  • Fastest: {summary['fastest_test'][0]} ({summary['fastest_test'][1]:.3f}s)

📊 Quality Metrics:
  • Total Errors: {summary['total_errors']}
  • Success Rate: {((summary['total_tests'] - summary['total_errors']) / summary['total_tests'] * 100):.1f}%

💡 Status: {'🟢 EXCELLENT' if summary['performance_score'] >= 80 else '🟡 GOOD' if summary['performance_score'] >= 60 else '🟠 NEEDS IMPROVEMENT' if summary['performance_score'] >= 40 else '🔴 POOR'}

{'='*50}
"""
        return report

    def save_metrics(self, filepath: str = None):
        """Save metrics to file."""
        if not filepath:
            filepath = (
                f"performance_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

        data = {
            "timestamp": datetime.now().isoformat(),
            "summary": self.metrics.get_summary(),
        }

        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)
            print(f"📊 Metrics saved to {filepath}")
        except Exception as e:
            print(f"⚠️ Could not save metrics: {e}")

    async def cleanup(self):
        """Cleanup resources."""
        # Wait for any pending tasks to complete
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if pending:
            await asyncio.wait(pending, timeout=1.0)

        # Cancel any remaining tasks
        for task in pending:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Dispose of the engine
        if self._engine:
            try:
                await self._engine.dispose()
            except Exception as e:
                print(f"Error disposing engine: {e}")
            self._engine = None

        # Reset state
        self._schema_ready = False


_monitor: Optional["SimplePerformanceMonitor"] = None


def get_simple_monitor(database_url: str) -> "SimplePerformanceMonitor":
    """Get or create the global performance monitor."""
    global _monitor
    if _monitor is None:
        _monitor = SimplePerformanceMonitor(database_url)

    return _monitor


async def cleanup_monitor():
    """Cleanup the global monitor."""
    global _monitor

    if _monitor:
        await _monitor.cleanup()
        _monitor = None


__all__ = [
    "SimplePerformanceMonitor",
    "SimpleMetrics",
    "get_simple_monitor",
    "cleanup_monitor",
]
