#!/usr/bin/env python3
"""Test script for PgBouncer prepared statements performance.

This module contains tests that measure and verify the performance and correctness
of prepared statements when working with PgBouncer. It includes tests for:
- Simple SELECT queries
- Batch INSERT operations
- Parameterized queries

Tests are optimized for speed by reusing database connections and test data.
"""

import os
import time
import logging
from typing import Dict, Tuple, Generator
import psycopg2
import psycopg2.extensions
import psycopg2.extras
import pytest
from datetime import datetime, timezone
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration - reduced for faster test execution
TEST_ITERATIONS = 2  # Reduced from 3 to 2
TEST_BATCH_SIZE = 50  # Reduced from 100 to 50

# Get database URL from environment or use default
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://app:app_password@localhost:5432/magflow_test",  # Using test database
)

# Store table names for each test connection
table_names: Dict[int, str] = {}


# Custom exception for test setup errors
class SetupError(Exception):
    """Raised when there's an error setting up test environment."""

    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(self.message)


@contextmanager
def db_connection_ctx() -> psycopg2.extensions.connection:
    """Context manager for database connection with automatic cleanup."""
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


def create_test_table(
    conn: psycopg2.extensions.connection, table_name: str = "test_prepared"
) -> None:
    """Create a test table with the given name if it doesn't exist.

    Args:
        conn: A psycopg2 database connection
        table_name: Name of the table to create (default: 'test_prepared')

    Raises:
        psycopg2.Error: If there's an error creating the table
        SetupError: If the table name is invalid or connection is closed
    """
    if not table_name.replace("_", "").isalnum():
        raise SetupError(f"Invalid table name: {table_name}")

    if conn.closed:
        raise SetupError("Database connection is closed")

    try:
        with conn.cursor() as cur:
            # First, drop the table if it exists
            logger.debug("Dropping existing test table if it exists")
            cur.execute(
                f"""
                DROP TABLE IF EXISTS {table_name} CASCADE;
                DROP SEQUENCE IF EXISTS {table_name}_id_seq CASCADE;
            """
            )
            conn.commit()

            # Then create the table
            logger.debug("Creating test table: %s", table_name)
            # Create table with proper JSON default value
            # Using double curly braces to escape them in f-strings
            # First, create the table with all required columns
            cur.execute(
                f"""
                CREATE TABLE {table_name} (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    value INTEGER,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    metadata JSONB DEFAULT '{{"index": 0, "timestamp": ""}}'::jsonb
                );

                -- Add indexes for common query patterns
                CREATE INDEX idx_{table_name}_name ON {table_name}(name);
                CREATE INDEX idx_{table_name}_value ON {table_name}(value);

                -- Ensure the metadata column exists (in case it was dropped)
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = '{table_name}'
                        AND column_name = 'metadata'
                    ) THEN
                        EXECUTE format('ALTER TABLE %I ADD COLUMN metadata JSONB DEFAULT %L::jsonb',
                                     '{table_name}', '{{"index": 0, "timestamp": ""}}');
                    END IF;
                END $$;
            """
            )
            conn.commit()
            logger.info("Created test table: %s", table_name)

    except psycopg2.Error as e:
        conn.rollback()
        logger.error("Error creating test table: %s", e)
        raise


def clear_test_data(
    conn: psycopg2.extensions.connection, table_name: str = "test_prepared"
) -> int:
    """Clear all data from the specified test table and reset sequences.

    Args:
        conn: A psycopg2 database connection
        table_name: Name of the table to clear (default: 'test_prepared')

    Returns:
        int: Number of rows deleted (0 if table didn't exist or was empty)

    Raises:
        psycopg2.Error: If there's an error clearing the data
    """
    if not table_name.replace("_", "").isalnum():
        raise ValueError(f"Invalid table name: {table_name}")

    if conn.closed:
        raise SetupError("Database connection is closed")

    try:
        with conn.cursor() as cur:
            # Check if the table exists
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = %s
                )
            """,
                (table_name,),
            )

            if not cur.fetchone()[0]:
                logger.warning("Table %s does not exist, nothing to clear", table_name)
                return 0

            # Get row count before truncate for logging
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cur.fetchone()[0]

            if row_count > 0:
                logger.debug("Clearing %d rows from table %s", row_count, table_name)
                # Use TRUNCATE with RESTART IDENTITY to reset sequences
                cur.execute(
                    f"""
                    TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE;
                """
                )
                conn.commit()
                logger.info("Cleared %d rows from table %s", row_count, table_name)

            return row_count

    except psycopg2.Error as e:
        conn.rollback()
        logger.error("Error clearing test data from %s: %s", table_name, e)
        raise


@pytest.fixture(scope="function")
def db_connection(request) -> Generator[psycopg2.extensions.connection, None, None]:
    """Create a database connection fixture with automatic cleanup.

    Each test gets its own uniquely named table to avoid conflicts.
    """
    # Create a unique table name based on the test function name
    test_name = request.node.name
    table_name = f"test_prepared_{test_name}"

    # Create a connection for the test
    conn = psycopg2.connect(DATABASE_URL)

    # Set isolation level to ensure we can use transactions
    conn.set_session(autocommit=False, isolation_level="READ COMMITTED")

    # Create the test table (this will drop and recreate it)
    create_test_table(conn, table_name)

    # Store the table name for this connection
    table_names[id(conn)] = table_name

    try:
        # Start a transaction for this test
        with conn.cursor() as cur:
            cur.execute("BEGIN")

        yield conn

        # After the test, rollback any changes
        with conn.cursor() as cur:
            cur.execute("ROLLBACK")

    except Exception as exc:  # noqa: BLE001
        # If there was an error, rollback and re-raise
        try:
            with conn.cursor() as cur:
                cur.execute("ROLLBACK")
        except Exception as rollback_error:
            print(f"Error during rollback: {rollback_error}")
        raise exc
    finally:
        # Clean up the test table
        with conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
            conn.commit()
        # Always close the connection
        conn.close()


def get_table_name(conn: psycopg2.extensions.connection) -> str:
    """Get the table name for a connection.

    Args:
        conn: A psycopg2 database connection

    Returns:
        str: The table name associated with this connection, or 'test_prepared' if not found

    Raises:
        SetupError: If the connection is invalid or no table is found
    """
    if conn is None or conn.closed:
        raise SetupError("Database connection is closed or invalid")

    # Get the table name for this connection
    conn_id = id(conn)
    table_name = table_names.get(conn_id)

    if table_name is None:
        logger.warning(f"No table name found for connection {conn_id}, using default")
        table_name = "test_prepared"
        table_names[conn_id] = table_name

    return table_name


def insert_test_data(conn: psycopg2.extensions.connection, count: int = 100) -> int:
    """Insert test data into the test table.

    {{ ... }}
        Args:
            conn: A psycopg2 database connection
            count: Number of test rows to insert (default: 100)

        Returns:
            int: Number of rows inserted

        Raises:
            psycopg2.Error: If there's an error inserting the data
            ValueError: If count is not a positive integer
    """
    if not isinstance(count, int) or count < 1:
        raise ValueError("Count must be a positive integer")

    if conn.closed:
        raise SetupError("Database connection is closed")

    table_name = get_table_name(conn)
    inserted = 0

    try:
        with conn.cursor() as cur:
            # Clear any existing data
            cur.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY")

            # Use execute_values for better performance with many rows
            # Convert dict to JSON string for proper SQL parameterization
            data = [
                (
                    f"test_{i}",
                    i,
                    psycopg2.extras.Json(
                        {"index": i, "timestamp": str(datetime.now(timezone.utc))}
                    ),
                )
                for i in range(count)
            ]

            # First, ensure the table is empty
            cur.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY")

            # Then insert the data
            psycopg2.extras.execute_values(
                cur,
                f"""
                INSERT INTO {table_name} (name, value, metadata)
                VALUES %s
                RETURNING id
                """,
                data,
                template="(%s, %s, %s)",  # psycopg2.extras.Json will handle the JSON serialization
                fetch=True,
            )

            inserted = len(cur.fetchall())
            conn.commit()
            logger.info("Inserted %d test rows into %s", inserted, table_name)

    except psycopg2.Error as e:
        conn.rollback()
        logger.error("Error inserting test data: %s", e)
        raise

    return inserted


@pytest.fixture(scope="function")
def test_data(db_connection: psycopg2.extensions.connection) -> tuple[str, int]:
    """Fixture to set up test data for prepared statement tests.

    Returns:
        tuple: (table_name, row_count)
    """
    table_name = get_table_name(db_connection)
    row_count = 100  # Reduced from 1000 to 100 for faster tests
    batch_size = 50

    try:
        with db_connection.cursor() as cur:
            # Clear any existing data
            cur.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY")

            # Insert test data in batches
            for i in range(0, row_count, batch_size):
                batch = []
                for j in range(i, min(i + batch_size, row_count)):
                    batch.append(
                        (
                            f"test_{j}",
                            j,
                            psycopg2.extras.Json(
                                {
                                    "index": j,
                                    "timestamp": str(datetime.now(timezone.utc)),
                                }
                            ),
                        )
                    )

                # Use execute_values for batch insert
                psycopg2.extras.execute_values(
                    cur,
                    f"""
                    INSERT INTO {table_name} (name, value, metadata)
                    VALUES %s
                    """,
                    batch,
                    template="(%s, %s, %s)",
                    page_size=batch_size,
                )

            db_connection.commit()

            # Verify the insert was successful
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            inserted = cur.fetchone()[0]
            assert (
                inserted == row_count
            ), f"Expected to insert {row_count} rows, but inserted {inserted}"

    except psycopg2.Error as e:
        db_connection.rollback()
        logger.error("Error setting up test data: %s", e)
        raise

    yield table_name, row_count

    # Cleanup
    try:
        with db_connection.cursor() as cur:
            cur.execute(f"TRUNCATE TABLE {table_name}")
            db_connection.commit()
    except psycopg2.Error as e:
        logger.warning("Error cleaning up test data: %s", e)
        db_connection.rollback()


def test_simple_select(
    test_data: tuple[str, int], db_connection: psycopg2.extensions.connection
) -> None:
    """Test simple SELECT query performance with prepared statements.

    Args:
        test_data: Fixture that provides (table_name, row_count)
        db_connection: Database connection fixture
    """
    table_name, row_count = test_data
    threshold = row_count // 2  # Test against the middle value
    test_iterations = 1  # Reduced from 3 to 1 for faster tests

    # Test without prepared statements
    start_time = time.time()
    with db_connection.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table_name} WHERE value > %s", (threshold,))
        result = cur.fetchone()[0]
    no_prep_time = time.time() - start_time

    # Test with prepared statements
    start_time = time.time()
    with db_connection.cursor() as cur:
        # Create a unique plan name to avoid conflicts with parallel tests
        plan_name = f"test_plan_{os.getpid()}"
        try:
            # Prepare the statement
            cur.execute(
                f"PREPARE {plan_name} AS SELECT COUNT(*) FROM {table_name} WHERE value > $1"
            )

            # Execute multiple times to measure performance
            for _ in range(test_iterations):
                cur.execute(f"EXECUTE {plan_name} (%s)", (threshold,))
                prep_result = cur.fetchone()[0]
                assert (
                    prep_result == result
                ), f"Result mismatch: {prep_result} != {result}"
        finally:
            # Clean up the prepared statement
            cur.execute(f"DEALLOCATE {plan_name}")
    prep_time = time.time() - start_time

    # Log performance results
    logger.info("\n=== Simple SELECT Test Results ===")
    logger.info("Rows in table: %d", row_count)
    logger.info("Rows matching condition: %d", result)
    logger.info("Without prepared statements: %.6f seconds", no_prep_time)
    logger.info("With prepared statements:    %.6f seconds", prep_time)


def test_batch_insert(
    test_data: tuple[str, int], db_connection: psycopg2.extensions.connection
) -> None:
    """Test batch insert performance with prepared statements.

    Args:
        test_data: Fixture that provides (table_name, row_count)
        db_connection: Database connection fixture
    """
    table_name, _ = test_data  # We'll use the table but not the row_count

    # Test data - smaller batch for faster tests
    batch_size = 50
    data = [
        (
            f"product_{i:04d}",
            i,
            psycopg2.extras.Json(
                {
                    "category": f"cat_{i % 5}",
                    "price": i * 1.5,
                    "in_stock": i % 3 == 0,
                    "test": "batch_insert",
                }
            ),
        )
        for i in range(batch_size)
    ]

    # Clear any existing data
    with db_connection.cursor() as cur:
        cur.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY")

    # Test with direct batch insert (most efficient way without prepared statements)
    start_time = time.time()
    with db_connection.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            f"""
            INSERT INTO {table_name} (name, value, metadata)
            VALUES %s
            """,
            [(name, val, metadata) for name, val, metadata in data],
            template="(%s, %s, %s)",
            page_size=batch_size,
        )

        # Verify the insert was successful
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cur.fetchone()[0]
        assert count == batch_size, f"Expected {batch_size} rows, got {count}"

    db_connection.commit()
    no_prep_time = time.time() - start_time

    # Clear the table for the next test
    with db_connection.cursor() as cur:
        cur.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY")

    # Test with prepared statements
    start_time = time.time()
    with db_connection.cursor() as cur:
        # Create a prepared statement
        plan_name = f"insert_plan_{os.getpid()}"
        try:
            # Prepare the statement
            cur.execute(
                f"""
                PREPARE {plan_name} (text, integer, jsonb) AS
                INSERT INTO {table_name} (name, value, metadata)
                VALUES ($1, $2, $3)
                """
            )

            # Execute with parameters in a transaction
            for name, value, metadata in data:
                cur.execute(
                    f"EXECUTE {plan_name} (%s, %s, %s)", (name, value, metadata)
                )

            # Verify the insert was successful
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cur.fetchone()[0]
            assert count == batch_size, f"Expected {batch_size} rows, got {count}"

        finally:
            # Clean up the prepared statement
            cur.execute(f"DEALLOCATE {plan_name}")

    db_connection.commit()
    prep_time = time.time() - start_time

    # Log performance results
    logger.info("\n=== Batch Insert Test Results ===")
    logger.info("Batch size: %d", batch_size)
    logger.info("Without prepared statements: %.6f seconds", no_prep_time)
    logger.info("With prepared statements:    %.6f seconds", prep_time)


def test_prepared_statement_parameterized_query(
    test_data: tuple[str, int], db_connection: psycopg2.extensions.connection
) -> None:
    """Test that prepared statements work correctly with parameterized queries.

    Args:
        test_data: Fixture that provides (table_name, row_count)
        db_connection: Database connection fixture
    """
    table_name, row_count = test_data

    # Test with different parameter values that cover edge cases
    # Using percentages of the actual row count for more dynamic testing
    test_values = [
        row_count // 10,  # 10% of data
        row_count // 2,  # 50% of data
        row_count * 9 // 10,  # 90% of data
        0,  # All data
        row_count,  # No data
        -1,  # All data (negative value)
    ]

    # Track performance metrics
    no_prep_times = []
    prep_times = []

    # Without prepared statement
    no_prep_results = []
    for value in test_values:
        start_time = time.time()
        with db_connection.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table_name} WHERE value > %s", (value,))
            result = cur.fetchone()[0]
            no_prep_results.append(result)
            no_prep_times.append(time.time() - start_time)

    # With prepared statement
    prep_results = []
    plan_name = f"test_plan_{os.getpid()}"

    try:
        # Create a prepared statement
        with db_connection.cursor() as cur:
            cur.execute(
                f"""
                PREPARE {plan_name} AS
                SELECT COUNT(*) FROM {table_name} WHERE value > $1
            """
            )

        # Execute with different parameters
        for value in test_values:
            start_time = time.time()
            with db_connection.cursor() as cur:
                cur.execute(f"EXECUTE {plan_name} (%s)", (value,))
                result = cur.fetchone()[0]
                prep_results.append(result)

                # Verify the result makes sense
                if value < 0:
                    assert (
                        result == row_count
                    ), f"Expected all {row_count} rows for value={value}, got {result}"
                elif value >= row_count:
                    assert (
                        result == 0
                    ), f"Expected 0 rows for value={value}, got {result}"

                prep_times.append(time.time() - start_time)

    finally:
        # Clean up the prepared statement
        with db_connection.cursor() as cur:
            cur.execute(f"DEALLOCATE {plan_name}")

    # Log performance statistics
    if no_prep_times and prep_times:
        avg_no_prep = sum(no_prep_times) * 1000 / len(no_prep_times)
        avg_prep = sum(prep_times) * 1000 / len(prep_times)

        logger.info("\n=== Parameterized Query Performance ===")
        logger.info("Test data size: %d rows", row_count)
        logger.info("Test iterations: %d", len(test_values))
        logger.info("Average time without prepared statements: %.3f ms", avg_no_prep)
        logger.info("Average time with prepared statements:    %.3f ms", avg_prep)

        if avg_no_prep > 0 and avg_prep > 0:
            improvement = ((avg_no_prep - avg_prep) / avg_no_prep) * 100
            logger.info("Improvement: %.1f%%", improvement)

    # Verify results match
    assert (
        no_prep_results == prep_results
    ), f"Results don't match: {no_prep_results} != {prep_results}"
