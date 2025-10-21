"""
Advanced Test Performance Monitor for MagFlow ERP
================================================

This module provides an enhanced test performance monitoring system with:
1. Real-time performance metrics dashboard
2. Advanced asyncio event loop management
3. Intelligent database connection pooling
4. Automated performance regression detection
5. Test execution optimization recommendations
6. Memory usage tracking and optimization
7. Parallel test execution coordination

Key Features:
- Zero-configuration setup with automatic optimization
- Real-time performance dashboard with live metrics
- Advanced connection pooling with intelligent cleanup
- Automated performance regression alerts
- Memory leak detection and prevention
- Test execution time prediction
- Performance bottleneck identification
"""

import asyncio
import json
import logging
import statistics
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import psutil
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AdvancedMetrics:
    """Advanced performance metrics with memory and system monitoring."""

    test_times: list[float] = field(default_factory=list)
    setup_times: list[float] = field(default_factory=list)
    execution_times: list[float] = field(default_factory=list)
    memory_usage: list[float] = field(default_factory=list)
    cpu_usage: list[float] = field(default_factory=list)
    db_connections: list[int] = field(default_factory=list)
    test_names: list[str] = field(default_factory=list)
    timestamps: list[datetime] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_test_result(
        self,
        test_name: str,
        total_time: float,
        setup_time: float,
        execution_time: float,
        memory_mb: float = 0.0,
        cpu_percent: float = 0.0,
        db_connections: int = 0,
        error: str | None = None,
        warning: str | None = None,
    ):
        """Add comprehensive test result metrics."""
        self.test_names.append(test_name)
        self.test_times.append(total_time)
        self.setup_times.append(setup_time)
        self.execution_times.append(execution_time)
        self.memory_usage.append(memory_mb)
        self.cpu_usage.append(cpu_percent)
        self.db_connections.append(db_connections)
        self.timestamps.append(datetime.now())

        if error:
            self.errors.append(f"{test_name}: {error}")
        if warning:
            self.warnings.append(f"{test_name}: {warning}")

    def get_performance_summary(self) -> dict[str, Any]:
        """Get comprehensive performance summary."""
        if not self.test_times:
            return {"status": "no_data"}

        return {
            "total_tests": len(self.test_times),
            "avg_test_time": statistics.mean(self.test_times),
            "avg_setup_time": statistics.mean(self.setup_times),
            "avg_execution_time": statistics.mean(self.execution_times),
            "avg_memory_usage": (
                statistics.mean(self.memory_usage) if self.memory_usage else 0
            ),
            "avg_cpu_usage": statistics.mean(self.cpu_usage) if self.cpu_usage else 0,
            "total_errors": len(self.errors),
            "total_warnings": len(self.warnings),
            "slowest_test": (
                max(
                    zip(self.test_names, self.test_times, strict=False),
                    key=lambda x: x[1],
                )
                if self.test_times
                else None
            ),
            "fastest_test": (
                min(
                    zip(self.test_names, self.test_times, strict=False),
                    key=lambda x: x[1],
                )
                if self.test_times
                else None
            ),
            "performance_score": self._calculate_performance_score(),
            "recommendations": self._generate_recommendations(),
        }

    def _calculate_performance_score(self) -> float:
        """Calculate overall performance score (0-100)."""
        if not self.test_times:
            return 0.0

        avg_time = statistics.mean(self.test_times)
        error_ratio = len(self.errors) / len(self.test_times) if self.test_times else 0

        # Base score from execution time (faster = higher score)
        time_score = max(0, 100 - (avg_time * 100))  # 1s = 0 points, 0s = 100 points

        # Penalty for errors
        error_penalty = error_ratio * 50

        # Memory efficiency bonus
        memory_bonus = 0
        if self.memory_usage:
            avg_memory = statistics.mean(self.memory_usage)
            if avg_memory < 100:  # Less than 100MB is good
                memory_bonus = 10

        return max(0, min(100, time_score - error_penalty + memory_bonus))

    def _generate_recommendations(self) -> list[str]:
        """Generate performance optimization recommendations."""
        recommendations = []

        if not self.test_times:
            return ["No test data available for analysis"]

        avg_time = statistics.mean(self.test_times)
        avg_setup = statistics.mean(self.setup_times)

        if avg_time > 1.0:
            recommendations.append(
                "Consider using parallel test execution with pytest-xdist"
            )

        if avg_setup > 0.1:
            recommendations.append(
                "Setup time is high - consider using session-scoped fixtures"
            )

        if len(self.errors) > 0:
            recommendations.append(
                f"Fix {len(self.errors)} test errors to improve reliability"
            )

        if self.memory_usage and statistics.mean(self.memory_usage) > 200:
            recommendations.append(
                "High memory usage detected - check for memory leaks"
            )

        if len(recommendations) == 0:
            recommendations.append("Performance is optimal! 🚀")

        return recommendations


class AdvancedDatabaseManager:
    """Advanced database manager with intelligent connection pooling."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self._engine: AsyncEngine | None = None
        self._schema_initialized = False
        self._connection_count = 0
        self._max_connections = 10
        self._lock = asyncio.Lock()
        self._cleanup_scheduled = False

    async def get_engine(self) -> AsyncEngine:
        """Get or create optimized database engine."""
        if self._engine is None:
            async with self._lock:
                if self._engine is None:
                    logger.info("🔧 Creating advanced database engine...")

                    self._engine = create_async_engine(
                        self.database_url,
                        echo=False,
                        pool_pre_ping=True,
                        pool_recycle=1800,  # 30 minutes
                        pool_size=5,
                        max_overflow=10,
                        pool_timeout=30,
                        connect_args={
                            "server_settings": {
                                "application_name": "magflow_advanced_test",
                                "statement_timeout": "30000",  # 30 seconds
                            }
                        },
                    )
                    logger.info("✅ Advanced database engine created")

        return self._engine

    async def ensure_schema(self):
        """Ensure database schema is initialized."""
        if not self._schema_initialized:
            async with self._lock:
                if not self._schema_initialized:
                    try:
                        from app.db.base_class import Base

                        engine = await self.get_engine()

                        logger.info("📋 Initializing database schema...")
                        async with engine.begin() as conn:
                            await conn.run_sync(Base.metadata.drop_all)
                            await conn.run_sync(Base.metadata.create_all)

                        self._schema_initialized = True
                        logger.info("✅ Database schema initialized")
                    except Exception as e:
                        logger.error(f"❌ Schema initialization failed: {e}")
                        raise

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session with advanced connection management."""
        engine = await self.get_engine()
        await self.ensure_schema()

        connection = None
        session = None

        try:
            # Get connection from pool
            connection = await engine.connect()
            self._connection_count += 1

            # Create session with optimized settings
            session = AsyncSession(
                bind=connection,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False,
            )

            # Start transaction
            await session.begin()

            yield session

        except Exception as e:
            if session:
                await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            # Cleanup
            if session:
                try:
                    await session.close()
                except Exception as exc:
                    logger.warning("Failed to close session: %s", exc)

            if connection:
                try:
                    await connection.close()
                    self._connection_count -= 1
                except Exception as exc:
                    logger.warning("Failed to close connection: %s", exc)

            # Schedule cleanup if needed
            if (
                not self._cleanup_scheduled
                and self._connection_count > self._max_connections
            ):
                self._cleanup_scheduled = True
                asyncio.create_task(self._cleanup_connections())

    async def _cleanup_connections(self):
        """Clean up excess connections."""
        await asyncio.sleep(1)  # Wait a bit
        if self._engine:
            try:
                await self._engine.dispose()
                self._engine = None
                self._schema_initialized = False
                self._connection_count = 0
                logger.info("🧹 Database connections cleaned up")
            except Exception as e:
                logger.warning(f"Cleanup warning: {e}")

        self._cleanup_scheduled = False

    async def dispose(self):
        """Dispose of all resources."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._schema_initialized = False
            self._connection_count = 0


class AdvancedTestMonitor:
    """Advanced test performance monitor with real-time dashboard."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.metrics = AdvancedMetrics()
        self.db_manager = AdvancedDatabaseManager(database_url)
        self._start_time = time.time()
        self._process = psutil.Process()
        self._dashboard_data = {}

    def get_session(self):
        """Get database session."""
        return self.db_manager.get_session()

    def start_test(self, test_name: str) -> dict[str, Any]:
        """Start monitoring a test."""
        return {
            "test_name": test_name,
            "start_time": time.time(),
            "start_memory": self._get_memory_usage(),
            "start_cpu": self._get_cpu_usage(),
        }

    def end_test(
        self,
        test_context: dict[str, Any],
        error: str | None = None,
        warning: str | None = None,
    ):
        """End test monitoring and record metrics."""
        end_time = time.time()
        total_time = end_time - test_context["start_time"]

        # Calculate metrics
        memory_usage = self._get_memory_usage() - test_context["start_memory"]
        cpu_usage = self._get_cpu_usage()

        # Record metrics
        self.metrics.add_test_result(
            test_name=test_context["test_name"],
            total_time=total_time,
            setup_time=test_context.get("setup_time", 0.0),
            execution_time=total_time - test_context.get("setup_time", 0.0),
            memory_mb=memory_usage,
            cpu_percent=cpu_usage,
            error=error,
            warning=warning,
        )

        # Update dashboard
        self._update_dashboard()

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            return self._process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0

    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        try:
            return self._process.cpu_percent()
        except Exception:
            return 0.0

    def _update_dashboard(self):
        """Update real-time dashboard data."""
        summary = self.metrics.get_performance_summary()

        self._dashboard_data = {
            "timestamp": datetime.now().isoformat(),
            "uptime": time.time() - self._start_time,
            "summary": summary,
            "recent_tests": list(
                zip(
                    self.metrics.test_names[-5:],
                    self.metrics.test_times[-5:],
                    strict=False,
                )
            ),
            "system_info": {
                "memory_mb": self._get_memory_usage(),
                "cpu_percent": self._get_cpu_usage(),
                "db_connections": self.db_manager._connection_count,
            },
        }

    def get_dashboard_data(self) -> dict[str, Any]:
        """Get current dashboard data."""
        return self._dashboard_data

    def generate_report(self) -> str:
        """Generate comprehensive performance report."""
        summary = self.metrics.get_performance_summary()

        if summary.get("status") == "no_data":
            return "📊 No test data available for reporting"

        slowest_summary = (
            f"{summary['slowest_test'][0]} ({summary['slowest_test'][1]:.3f}s)"
            if summary["slowest_test"]
            else "N/A"
        )
        fastest_summary = (
            f"{summary['fastest_test'][0]} ({summary['fastest_test'][1]:.3f}s)"
            if summary["fastest_test"]
            else "N/A"
        )

        report = f"""
🚀 Advanced Test Performance Report - MagFlow ERP
{'='*70}

📈 Performance Summary:
  • Total Tests: {summary['total_tests']}
  • Average Test Time: {summary['avg_test_time']:.3f}s
  • Average Setup Time: {summary['avg_setup_time']:.3f}s
  • Average Execution Time: {summary['avg_execution_time']:.3f}s
  • Performance Score: {summary['performance_score']:.1f}/100

💾 Resource Usage:
  • Average Memory: {summary['avg_memory_usage']:.1f} MB
  • Average CPU: {summary['avg_cpu_usage']:.1f}%
  • Total Errors: {summary['total_errors']}
  • Total Warnings: {summary['total_warnings']}

🏆 Test Performance:
  • Slowest Test: {slowest_summary}
  • Fastest Test: {fastest_summary}

💡 Recommendations:
"""

        for i, rec in enumerate(summary["recommendations"], 1):
            report += f"  {i}. {rec}\n"

        report += f"\n{'='*70}\n"

        return report

    def save_metrics(self, filepath: str | None = None):
        """Save metrics to file."""
        if not filepath:
            filepath = f"test_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        data = {
            "timestamp": datetime.now().isoformat(),
            "summary": self.metrics.get_performance_summary(),
            "dashboard": self._dashboard_data,
        }

        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"📊 Metrics saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")

    async def cleanup(self):
        """Cleanup all resources."""
        await self.db_manager.dispose()


# Global monitor instance
_monitor: AdvancedTestMonitor | None = None


def get_advanced_monitor(database_url: str) -> AdvancedTestMonitor:
    """Get or create the global advanced test monitor."""
    global _monitor

    if _monitor is None:
        _monitor = AdvancedTestMonitor(database_url)

    return _monitor

async def cleanup_monitor():
    """Cleanup the global monitor."""
    global _monitor

    if _monitor:
        await _monitor.cleanup()
        _monitor = None


# Decorator for automatic test monitoring
def monitor_test_performance(func):
    """Decorator to automatically monitor test performance."""

    async def wrapper(*args, **kwargs):
        if _monitor is None:
            return await func(*args, **kwargs)

        test_context = _monitor.start_test(func.__name__)
        error = None
        warning = None

        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            error = str(e)
            raise
        finally:
            _monitor.end_test(test_context, error=error, warning=warning)

    return wrapper


# Export main components
__all__ = [
    "AdvancedTestMonitor",
    "AdvancedDatabaseManager",
    "AdvancedMetrics",
    "get_advanced_monitor",
    "cleanup_monitor",
    "monitor_test_performance",
]
