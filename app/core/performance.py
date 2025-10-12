"""Performance monitoring and optimization utilities.

This module provides tools for monitoring application performance,
caching optimization, and database query optimization.
"""

import logging
import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import wraps
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""

    query_count: int = 0
    query_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    api_calls: int = 0
    api_time: float = 0.0
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))


# Global metrics storage
_metrics: dict[str, PerformanceMetrics] = {}


def get_performance_metrics(request_id: str) -> PerformanceMetrics:
    """Get performance metrics for a request."""
    return _metrics.get(request_id, PerformanceMetrics())


def track_performance(request_id: str):
    """Decorator to track performance metrics for a function."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if request_id not in _metrics:
                _metrics[request_id] = PerformanceMetrics()

            metrics = _metrics[request_id]
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                logger.info(
                    f"Performance: {func.__name__} took {execution_time:.3f}s",
                    extra={
                        "request_id": request_id,
                        "function": func.__name__,
                        "execution_time": execution_time,
                        "total_queries": metrics.query_count,
                        "total_query_time": metrics.query_time,
                    },
                )

        return wrapper

    return decorator


@contextmanager
def track_db_queries():
    """Context manager to track database queries."""
    query_count = {"count": 0}
    start_time = time.time()

    def count_queries(conn, cursor, statement, parameters, context, executemany):
        query_count["count"] += 1

    event.listen(Engine, "before_cursor_execute", count_queries)

    try:
        yield query_count
    finally:
        event.remove(Engine, "before_cursor_execute", count_queries)
        query_time = time.time() - start_time
        logger.info(
            f"Database queries executed: {query_count['count']} in {query_time:.3f}s"
        )


class CacheOptimizer:
    """Cache optimization utilities."""

    def __init__(self, cache_service):
        self.cache = cache_service

    async def get_or_compute(
        self,
        key: str,
        compute_func: Callable,
        ttl: int | None = None,
        namespace: str = "default",
    ) -> Any:
        """Get cached value or compute and cache it."""
        # Try to get from cache first
        cached_value = await self.cache.get(key, namespace)
        if cached_value is not None:
            _metrics[namespace].cache_hits += 1
            return cached_value

        # Compute and cache
        _metrics[namespace].cache_misses += 1
        value = await compute_func()

        await self.cache.set(key, value, ttl, namespace)
        return value

    async def invalidate_pattern(self, pattern: str, namespace: str = "default") -> int:
        """Invalidate cache entries matching a pattern."""
        return await self.cache.delete_pattern(pattern, namespace)


class QueryOptimizer:
    """Database query optimization utilities."""

    @staticmethod
    def analyze_query_performance(query, execution_time: float) -> dict[str, Any]:
        """Analyze query performance and provide recommendations."""
        analysis = {
            "execution_time": execution_time,
            "performance_level": (
                "good"
                if execution_time < 0.1
                else "slow"
                if execution_time < 1.0
                else "very_slow"
            ),
            "recommendations": [],
        }

        if execution_time > 1.0:
            analysis["recommendations"].append("Consider adding database indexes")
        if execution_time > 0.5:
            analysis["recommendations"].append("Review query complexity")
        if execution_time > 0.1:
            analysis["recommendations"].append("Consider query optimization")

        return analysis

    @staticmethod
    def suggest_indexes(query: str) -> list[str]:
        """Suggest database indexes for a query."""
        # This is a simplified implementation
        # In practice, you'd use EXPLAIN ANALYZE results
        suggestions = []

        if "WHERE" in query.upper():
            suggestions.append("Add indexes on columns used in WHERE clauses")
        if "ORDER BY" in query.upper():
            suggestions.append("Add indexes on columns used in ORDER BY clauses")
        if "JOIN" in query.upper():
            suggestions.append("Add indexes on foreign key columns used in JOINs")

        return suggestions


# Performance monitoring middleware
async def performance_monitoring_middleware(request, call_next):
    """Middleware to monitor request performance."""
    request_id = request.headers.get("X-Request-ID", "unknown")
    start_time = time.time()

    _metrics[request_id] = PerformanceMetrics()
    metrics = _metrics[request_id]

    # Track API call
    metrics.api_calls += 1

    try:
        response = await call_next(request)
        metrics.api_time = time.time() - start_time

        # Log performance metrics
        if metrics.api_time > 5.0:  # Log slow requests
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path} took {metrics.api_time:.2f}s",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "execution_time": metrics.api_time,
                    "query_count": metrics.query_count,
                    "query_time": metrics.query_time,
                },
            )

        return response

    except Exception as e:
        logger.error(
            f"Request failed: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "error": str(e),
            },
        )
        raise
