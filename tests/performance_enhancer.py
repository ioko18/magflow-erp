"""
Performance Enhancement System for MagFlow ERP Tests

This module provides comprehensive performance monitoring and optimization
for the test suite, addressing slow test durations and resource management.
"""


import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Callable, Dict, List

import psutil
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


@dataclass
class PerformanceMetrics:
    """Performance metrics for test execution."""

    test_name: str
    setup_time: float
    execution_time: float
    teardown_time: float
    memory_usage_mb: float
    cpu_percent: float
    database_queries: int
    cache_hits: int
    cache_misses: int

    @property
    def total_time(self) -> float:
        """Total test execution time."""
        return self.setup_time + self.execution_time + self.teardown_time

    @property
    def performance_score(self) -> int:
        """Performance score from 0-100 (higher is better)."""
        # Base score starts at 100
        score = 100

        # Penalize slow tests
        if self.total_time > 2.0:
            score -= 30
        elif self.total_time > 1.0:
            score -= 15
        elif self.total_time > 0.5:
            score -= 5

        # Penalize high memory usage
        if self.memory_usage_mb > 100:
            score -= 20
        elif self.memory_usage_mb > 50:
            score -= 10

        # Penalize high CPU usage
        if self.cpu_percent > 80:
            score -= 15
        elif self.cpu_percent > 50:
            score -= 5

        # Penalize excessive database queries
        if self.database_queries > 20:
            score -= 10
        elif self.database_queries > 10:
            score -= 5

        # Bonus for good cache hit ratio
        if self.cache_hits + self.cache_misses > 0:
            hit_ratio = self.cache_hits / (self.cache_hits + self.cache_misses)
            if hit_ratio > 0.8:
                score += 5

        return max(0, min(100, score))


class DatabaseQueryTracker:
    """Tracks database queries for performance monitoring."""

    def __init__(self):
        self.query_count = 0
        self.queries = []
        self.slow_queries = []

    def track_query(self, query: str, duration: float):
        """Track a database query."""
        self.query_count += 1
        self.queries.append({"query": query, "duration": duration})

        if duration > 0.1:  # Queries slower than 100ms
            self.slow_queries.append({"query": query, "duration": duration})

    def reset(self):
        """Reset query tracking."""
        self.query_count = 0
        self.queries.clear()
        self.slow_queries.clear()


class CacheTracker:
    """Tracks cache performance."""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.operations = []

    def record_hit(self, key: str):
        """Record a cache hit."""
        self.hits += 1
        self.operations.append({"key": key, "type": "hit", "timestamp": time.time()})

    def record_miss(self, key: str):
        """Record a cache miss."""
        self.misses += 1
        self.operations.append({"key": key, "type": "miss", "timestamp": time.time()})

    def reset(self):
        """Reset cache tracking."""
        self.hits = 0
        self.misses = 0
        self.operations.clear()


class PerformanceEnhancer:
    """Main performance enhancement and monitoring system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db_tracker = DatabaseQueryTracker()
        self.cache_tracker = CacheTracker()
        self.metrics_history: List[PerformanceMetrics] = []
        self._session_cache = {}
        self._engine_cache = {}

    @asynccontextmanager
    async def monitor_test(self, test_name: str):
        """Context manager to monitor test performance."""
        # Setup phase
        setup_start = time.time()
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Reset trackers
        self.db_tracker.reset()
        self.cache_tracker.reset()

        setup_time = time.time() - setup_start

        # Execution phase
        execution_start = time.time()

        try:
            yield self
        finally:
            execution_time = time.time() - execution_start

            # Teardown phase
            teardown_start = time.time()

            # Collect final metrics
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            cpu_percent = process.cpu_percent()

            teardown_time = time.time() - teardown_start

            # Create metrics
            metrics = PerformanceMetrics(
                test_name=test_name,
                setup_time=setup_time,
                execution_time=execution_time,
                teardown_time=teardown_time,
                memory_usage_mb=final_memory - initial_memory,
                cpu_percent=cpu_percent,
                database_queries=self.db_tracker.query_count,
                cache_hits=self.cache_tracker.hits,
                cache_misses=self.cache_tracker.misses,
            )

            # Store metrics
            self.metrics_history.append(metrics)

            # Log performance warnings
            self._log_performance_warnings(metrics)

    def _log_performance_warnings(self, metrics: PerformanceMetrics):
        """Log performance warnings for slow tests."""
        if metrics.total_time > 1.0:
            self.logger.warning(
                f"Slow test detected: {metrics.test_name} took {metrics.total_time:.2f}s "
                f"(setup: {metrics.setup_time:.2f}s, execution: {metrics.execution_time:.2f}s, "
                f"teardown: {metrics.teardown_time:.2f}s)"
            )

        if metrics.memory_usage_mb > 50:
            self.logger.warning(
                f"High memory usage in test {metrics.test_name}: {metrics.memory_usage_mb:.1f}MB"
            )

        if metrics.database_queries > 10:
            self.logger.warning(
                f"Excessive database queries in test {metrics.test_name}: {metrics.database_queries} queries"
            )

        if self.db_tracker.slow_queries:
            self.logger.warning(
                f"Slow database queries detected in test {metrics.test_name}: "
                f"{len(self.db_tracker.slow_queries)} queries > 100ms"
            )

    async def get_cached_session(
        self, engine: AsyncEngine, session_key: str = "default"
    ) -> AsyncSession:
        """Get a cached database session to reduce setup overhead."""
        if session_key not in self._session_cache:
            from sqlalchemy.orm import sessionmaker
            from sqlalchemy.ext.asyncio import AsyncSession

            async_session = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )
            self._session_cache[session_key] = async_session

        return self._session_cache[session_key]()

    def get_cached_engine(
        self, database_url: str, engine_key: str = "default"
    ) -> AsyncEngine:
        """Get a cached database engine to reduce connection overhead."""
        if engine_key not in self._engine_cache:
            from sqlalchemy.ext.asyncio import create_async_engine
            from sqlalchemy.pool import StaticPool

            engine = create_async_engine(
                database_url,
                poolclass=StaticPool,
                connect_args=(
                    {"check_same_thread": False} if "sqlite" in database_url else {}
                ),
                echo=False,
                pool_pre_ping=True,
                pool_recycle=300,
                pool_size=5,
                max_overflow=10,
            )
            self._engine_cache[engine_key] = engine

        return self._engine_cache[engine_key]

    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate a comprehensive performance report."""
        if not self.metrics_history:
            return {"message": "No performance data available"}

        # Calculate statistics
        total_tests = len(self.metrics_history)
        avg_time = sum(m.total_time for m in self.metrics_history) / total_tests
        avg_memory = sum(m.memory_usage_mb for m in self.metrics_history) / total_tests
        avg_queries = (
            sum(m.database_queries for m in self.metrics_history) / total_tests
        )
        avg_score = sum(m.performance_score for m in self.metrics_history) / total_tests

        # Find slowest tests
        slowest_tests = sorted(
            self.metrics_history, key=lambda m: m.total_time, reverse=True
        )[:5]

        # Find memory-intensive tests
        memory_intensive = sorted(
            self.metrics_history, key=lambda m: m.memory_usage_mb, reverse=True
        )[:5]

        # Find query-heavy tests
        query_heavy = sorted(
            self.metrics_history, key=lambda m: m.database_queries, reverse=True
        )[:5]

        return {
            "summary": {
                "total_tests": total_tests,
                "average_execution_time": f"{avg_time:.2f}s",
                "average_memory_usage": f"{avg_memory:.1f}MB",
                "average_database_queries": f"{avg_queries:.1f}",
                "average_performance_score": f"{avg_score:.1f}/100",
            },
            "slowest_tests": [
                {
                    "name": m.test_name,
                    "total_time": f"{m.total_time:.2f}s",
                    "performance_score": m.performance_score,
                }
                for m in slowest_tests
            ],
            "memory_intensive_tests": [
                {
                    "name": m.test_name,
                    "memory_usage": f"{m.memory_usage_mb:.1f}MB",
                    "performance_score": m.performance_score,
                }
                for m in memory_intensive
            ],
            "query_heavy_tests": [
                {
                    "name": m.test_name,
                    "database_queries": m.database_queries,
                    "performance_score": m.performance_score,
                }
                for m in query_heavy
            ],
            "recommendations": self._generate_recommendations(),
        }

    def _generate_recommendations(self) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []

        if not self.metrics_history:
            return recommendations

        # Analyze patterns
        slow_tests = [m for m in self.metrics_history if m.total_time > 1.0]
        memory_heavy = [m for m in self.metrics_history if m.memory_usage_mb > 50]
        query_heavy = [m for m in self.metrics_history if m.database_queries > 10]

        if slow_tests:
            recommendations.append(
                f"Consider optimizing {len(slow_tests)} slow tests (>1s execution time)"
            )

        if memory_heavy:
            recommendations.append(
                f"Consider reducing memory usage in {len(memory_heavy)} tests (>50MB usage)"
            )

        if query_heavy:
            recommendations.append(
                f"Consider reducing database queries in {len(query_heavy)} tests (>10 queries)"
            )

        # Cache performance
        total_cache_ops = sum(
            m.cache_hits + m.cache_misses for m in self.metrics_history
        )
        if total_cache_ops > 0:
            total_hits = sum(m.cache_hits for m in self.metrics_history)
            hit_ratio = total_hits / total_cache_ops
            if hit_ratio < 0.7:
                recommendations.append(
                    f"Consider improving cache hit ratio (currently {hit_ratio:.1%})"
                )

        if not recommendations:
            recommendations.append(
                "Test performance looks good! Keep up the excellent work."
            )

        return recommendations

    async def cleanup(self):
        """Clean up cached resources."""
        # Close cached sessions
        for session in self._session_cache.values():
            try:
                if hasattr(session, "close"):
                    await session.close()
            except Exception as e:
                self.logger.debug(f"Error closing cached session: {e}")

        # Dispose cached engines
        for engine in self._engine_cache.values():
            try:
                if hasattr(engine, "dispose"):
                    await engine.dispose()
            except Exception as e:
                self.logger.debug(f"Error disposing cached engine: {e}")

        # Clear caches
        self._session_cache.clear()
        self._engine_cache.clear()


# Global performance enhancer instance
performance_enhancer = PerformanceEnhancer()


# Utility functions for test optimization
async def optimize_test_database_setup(
    database_url: str = "sqlite+aiosqlite:///:memory:",
):
    """Optimized database setup for tests."""
    engine = performance_enhancer.get_cached_engine(database_url)

    # Create tables if needed
    from app.db.base_class import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return engine


async def create_optimized_test_session(engine):
    """Create an optimized test session."""
    session = await performance_enhancer.get_cached_session(engine)
    return session


def log_test_performance(func):
    """Decorator to log test performance."""

    async def wrapper(*args, **kwargs):
        test_name = func.__name__
        async with performance_enhancer.monitor_test(test_name):
            return await func(*args, **kwargs)

    return wrapper
