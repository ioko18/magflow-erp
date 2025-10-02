"""
Performance benchmarks for MagFlow ERP database operations.

This module provides comprehensive performance testing for database operations
including CRUD operations, queries, and bulk operations.
"""

import pytest
import time
import asyncio
from typing import Dict
import statistics

from tests.test_data_factory import (
    UserFactory,
    AuditLogFactory,
    create_bulk_users,
    create_bulk_products,
)


class DatabasePerformanceBenchmark:
    """Performance benchmark suite for database operations."""

    def __init__(self, db_session):
        self.db_session = db_session
        self.results = {}

    async def measure_time(self, operation_name: str, operation_func):
        """Measure the execution time of an operation."""
        start_time = time.perf_counter()
        try:
            result = await operation_func()
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            self.results[operation_name] = execution_time
            return result, execution_time
        except Exception as e:
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            self.results[operation_name] = execution_time
            raise e

    async def benchmark_user_creation(self, count: int = 100):
        """Benchmark user creation performance."""

        def create_users():
            return create_bulk_users(self.db_session, count)

        _, execution_time = await self.measure_time(
            f"user_creation_{count}", create_users
        )
        return execution_time

    async def benchmark_product_creation(self, count: int = 200):
        """Benchmark product creation performance."""

        def create_products():
            return create_bulk_products(self.db_session, count)

        _, execution_time = await self.measure_time(
            f"product_creation_{count}", create_products
        )
        return execution_time

    async def benchmark_bulk_audit_logs(self, count: int = 500):
        """Benchmark bulk audit log creation."""

        def create_audit_logs():
            audit_logs = []
            for _ in range(count):
                audit_log = AuditLogFactory()
                self.db_session.add(audit_log)
                audit_logs.append(audit_log)
            return audit_logs

        _, execution_time = await self.measure_time(
            f"audit_log_creation_{count}", create_audit_logs
        )
        return execution_time

    async def benchmark_query_performance(self):
        """Benchmark various query operations."""

        # Simple user query
        def simple_query():
            return self.db_session.execute("SELECT COUNT(*) FROM users")

        # Complex query with joins
        def complex_query():
            return self.db_session.execute(
                """
                SELECT u.email, r.name as role_name, COUNT(al.id) as audit_count
                FROM users u
                LEFT JOIN user_roles ur ON u.id = ur.user_id
                LEFT JOIN roles r ON ur.role_id = r.id
                LEFT JOIN audit_logs al ON u.id = al.user_id
                GROUP BY u.id, r.name
                LIMIT 100
            """
            )

        # Query with filtering
        def filtered_query():
            return self.db_session.execute(
                """
                SELECT * FROM users
                WHERE is_active = true
                AND created_at >= NOW() - INTERVAL '30 days'
                ORDER BY created_at DESC
                LIMIT 50
            """
            )

        await self.measure_time("simple_query", simple_query)
        await self.measure_time("complex_query", complex_query)
        await self.measure_time("filtered_query", filtered_query)

    async def benchmark_update_operations(self, count: int = 50):
        """Benchmark update operations."""
        # Get some users to update
        result = await self.db_session.execute(
            "SELECT id FROM users LIMIT :count", {"count": count}
        )
        user_ids = [row[0] for row in result]

        def update_users():
            for user_id in user_ids:
                self.db_session.execute(
                    "UPDATE users SET updated_at = NOW() WHERE id = :user_id",
                    {"user_id": user_id},
                )

        _, execution_time = await self.measure_time(
            f"user_update_{count}", update_users
        )
        return execution_time

    async def benchmark_delete_operations(self, count: int = 25):
        """Benchmark delete operations."""
        # Get some audit logs to delete (safest to delete)
        result = await self.db_session.execute(
            "SELECT id FROM audit_logs ORDER BY created_at ASC LIMIT :count",
            {"count": count},
        )
        audit_ids = [row[0] for row in result]

        def delete_audit_logs():
            for audit_id in audit_ids:
                self.db_session.execute(
                    "DELETE FROM audit_logs WHERE id = :audit_id",
                    {"audit_id": audit_id},
                )

        _, execution_time = await self.measure_time(
            f"audit_delete_{count}", delete_audit_logs
        )
        return execution_time

    def get_results(self) -> dict:
        """Get all benchmark results."""
        return self.results.copy()

    def print_summary(self):
        """Print a summary of benchmark results."""
        print("\n" + "=" * 60)
        print("DATABASE PERFORMANCE BENCHMARK RESULTS")
        print("=" * 60)

        if not self.results:
            print("No benchmark results available.")
            return

        # Group results by operation type
        creation_ops = {k: v for k, v in self.results.items() if "creation" in k}
        update_ops = {k: v for k, v in self.results.items() if "update" in k}
        delete_ops = {k: v for k, v in self.results.items() if "delete" in k}

        if creation_ops:
            print("\nCREATION OPERATIONS:")
            for op, time_taken in creation_ops.items():
                print(f"  {op}: {time_taken:.4f}s")

        # Gather query operation results
        query_ops = {k: v for k, v in self.results.items() if "query" in k}
        if query_ops:
            print("\nQUERY OPERATIONS:")
            for op, time_taken in query_ops.items():
                print(f"  {op}: {time_taken:.4f}s")

        if update_ops:
            print("\nUPDATE OPERATIONS:")
            for op, time_taken in update_ops.items():
                print(f"  {op}: {time_taken:.4f}s")

        if delete_ops:
            print("\nDELETE OPERATIONS:")
            for op, time_taken in delete_ops.items():
                print(f"  {op}: {time_taken:.4f}s")
        # Calculate totals
        total_time = sum(self.results.values())
        avg_time = statistics.mean(self.results.values()) if self.results else 0
        max_time = max(self.results.values()) if self.results else 0

        print("\nSUMMARY STATISTICS:")
        print(f"  Total execution time: {total_time:.4f} seconds")
        print(f"  Average operation time: {avg_time:.4f} seconds")
        print(f"  Fastest operation: {min(self.results.values()):.4f} seconds")
        print(f"  Slowest operation: {max_time:.4f} seconds")
        print(f"Database performance results: {len(self.results)} operations tested")
        print("=" * 60)


@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_database_creation_performance(db_session):
    """Benchmark database creation operations performance."""
    benchmark = DatabasePerformanceBenchmark(db_session)

    # Test different scales
    await benchmark.benchmark_user_creation(50)
    await benchmark.benchmark_user_creation(100)
    await benchmark.benchmark_product_creation(100)
    await benchmark.benchmark_product_creation(200)
    await benchmark.benchmark_bulk_audit_logs(250)

    benchmark.print_summary()

    # Performance assertions
    results = benchmark.get_results()

    # User creation should be reasonably fast
    assert results["user_creation_50"] < 2.0, "50 user creation took too long"
    assert results["user_creation_100"] < 3.0, "100 user creation took too long"

    # Product creation should be reasonably fast
    assert results["product_creation_100"] < 3.0, "100 product creation took too long"
    assert results["product_creation_200"] < 5.0, "200 product creation took too long"


@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_database_query_performance(db_session):
    """Benchmark database query operations performance."""
    benchmark = DatabasePerformanceBenchmark(db_session)

    await benchmark.benchmark_query_performance()

    benchmark.print_summary()

    # Performance assertions
    results = benchmark.get_results()

    # Queries should be reasonably fast
    assert results["simple_query"] < 0.1, "Simple query took too long"
    assert results["complex_query"] < 0.5, "Complex query took too long"
    assert results["filtered_query"] < 0.2, "Filtered query took too long"


@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_database_update_performance(db_session):
    """Benchmark database update operations performance."""
    # First create some data to update
    await create_bulk_users(db_session, 50)

    benchmark = DatabasePerformanceBenchmark(db_session)

    await benchmark.benchmark_update_operations(25)
    await benchmark.benchmark_update_operations(50)

    benchmark.print_summary()

    # Performance assertions
    results = benchmark.get_results()

    # Updates should be reasonably fast
    assert results["user_update_25"] < 1.0, "25 user updates took too long"
    assert results["user_update_50"] < 2.0, "50 user updates took too long"


@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_database_delete_performance(db_session):
    """Benchmark database delete operations performance."""
    # First create some audit logs to delete
    audit_logs = []
    for _ in range(100):
        audit_log = AuditLogFactory()
        db_session.add(audit_log)
        audit_logs.append(audit_log)
    await db_session.commit()

    benchmark = DatabasePerformanceBenchmark(db_session)

    await benchmark.benchmark_delete_operations(25)
    await benchmark.benchmark_delete_operations(50)

    benchmark.print_summary()

    # Performance assertions
    results = benchmark.get_results()

    # Deletes should be reasonably fast
    assert results["audit_delete_25"] < 1.0, "25 audit log deletes took too long"
    assert results["audit_delete_50"] < 2.0, "50 audit log deletes took too long"


@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_database_mixed_operations_performance(db_session):
    """Benchmark mixed database operations performance."""
    benchmark = DatabasePerformanceBenchmark(db_session)

    # Run all types of operations
    await benchmark.benchmark_user_creation(25)
    await benchmark.benchmark_query_performance()
    await benchmark.benchmark_update_operations(10)
    await benchmark.benchmark_delete_operations(5)

    benchmark.print_summary()

    # Overall performance should be reasonable
    results = benchmark.get_results()
    total_time = sum(results.values())

    assert total_time < 10.0, f"Mixed operations took too long: {total_time:.2f}s"


# Concurrent performance tests
@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_concurrent_user_creation(db_session):
    """Test concurrent user creation performance."""

    async def create_user_batch(batch_size: int):
        for _ in range(batch_size):
            user = UserFactory()
            db_session.add(user)
        await db_session.commit()

    # Create multiple batches concurrently
    batch_size = 10
    tasks = [create_user_batch(batch_size) for _ in range(5)]

    start_time = time.perf_counter()
    await asyncio.gather(*tasks)
    end_time = time.perf_counter()

    execution_time = end_time - start_time
    print(
        f"✅ Concurrent user creation ({5} batches of {batch_size}): {execution_time:.4f}s"
    )

    # Should be reasonably fast
    assert (
        execution_time < 5.0
    ), f"Concurrent user creation took too long: {execution_time:.2f}s"


@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_database_connection_pool_performance(db_session):
    """Test database connection pool performance under load."""

    async def perform_query(query_id: int):
        result = await db_session.execute(
            "SELECT COUNT(*) FROM users WHERE id > :id", {"id": query_id}
        )
        return result.scalar()

    # Run multiple queries concurrently
    query_count = 20
    tasks = [perform_query(i) for i in range(query_count)]

    start_time = time.perf_counter()
    results = await asyncio.gather(*tasks)
    end_time = time.perf_counter()

    execution_time = end_time - start_time
    print(f"✅ Concurrent queries ({query_count}): {execution_time:.4f}s")
    print(f"✅ Average query time: {execution_time/query_count:.4f}s")

    # Should handle concurrent queries efficiently
    assert (
        execution_time < 3.0
    ), f"Concurrent queries took too long: {execution_time:.2f}s"
    assert all(count >= 0 for count in results), "Query results should be valid"
