#!/usr/bin/env python3
"""
Test script for PgBouncer prepared statements performance.

Measures query performance before and after enabling prepared statements.
"""

import time
import statistics
import psycopg2
from psycopg2.extras import execute_batch
import argparse


def parse_args():
    parser = argparse.ArgumentParser(
        description="Test PgBouncer prepared statements performance"
    )
    parser.add_argument(
        "--dsn",
        default="postgresql://app:app_password_change_me@localhost:6432/magflow",
        help="Database connection string",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=100,
        help="Number of iterations to run each test",
    )
    parser.add_argument(
        "--batch-size", type=int, default=10, help="Batch size for batch operations"
    )
    return parser.parse_args()


def setup_test_table(conn):
    """Create a test table if it doesn't exist"""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS test_prepared (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                value INTEGER,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """
        )
        conn.commit()


def test_simple_select(conn, iterations):
    """Test simple SELECT query performance"""
    times = []

    for i in range(iterations):
        start = time.perf_counter()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM test_prepared WHERE id = %s", (i % 100 + 1,))
            cur.fetchone()
        times.append(time.perf_counter() - start)

    return times


def test_batch_insert(conn, iterations, batch_size):
    """Test batch insert performance"""
    times = []
    data = [(f"test_{i}", i) for i in range(batch_size)]

    for _ in range(iterations):
        start = time.perf_counter()
        with conn.cursor() as cur:
            execute_batch(
                cur, "INSERT INTO test_prepared (name, value) VALUES (%s, %s)", data
            )
            conn.commit()
        times.append(time.perf_counter() - start)

    return times


def test_complex_query(conn, iterations):
    """Test more complex query with joins"""
    times = []

    for i in range(iterations):
        start = time.perf_counter()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.name, COUNT(p.id) as product_count
                FROM app.categories c
                LEFT JOIN app.product_categories pc ON c.id = pc.category_id
                LEFT JOIN app.products p ON pc.product_id = p.id
                WHERE c.name LIKE %s
                GROUP BY c.name
                ORDER BY product_count DESC
                LIMIT 10
            """,
                (f"%{i % 5}%",),
            )
            cur.fetchall()
        times.append(time.perf_counter() - start)

    return times


def print_stats(label, times):
    """Print statistics about query times"""
    print(f"\n{label}:")
    print(f"  Iterations: {len(times)}")
    print(f"  Total time: {sum(times):.4f}s")
    print(f"  Average: {statistics.mean(times)*1000:.2f}ms")
    print(f"  Min: {min(times)*1000:.2f}ms")
    print(f"  Max: {max(times)*1000:.2f}ms")
    print(f"  95th percentile: {statistics.quantiles(times, n=100)[94]*1000:.2f}ms")


def main():
    args = parse_args()

    # Connect to database
    conn = psycopg2.connect(args.dsn)

    try:
        # Setup test environment
        setup_test_table(conn)

        print("=== Testing Simple SELECT ===")
        select_times = test_simple_select(conn, args.iterations)
        print_stats("Simple SELECT", select_times)

        print("\n=== Testing Batch Insert ===")
        insert_times = test_batch_insert(conn, args.iterations, args.batch_size)
        print_stats(f"Batch Insert (size={args.batch_size})", insert_times)

        print("\n=== Testing Complex Query ===")
        complex_times = test_complex_query(conn, args.iterations)
        print_stats("Complex Query", complex_times)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
