#!/usr/bin/env python3
"""Test database operations with prepared statements."""

import os
import uuid
import pytest
import psycopg2
from psycopg2.extras import execute_batch
from typing import Generator, Optional

# Get database connection string from environment or use default
DEFAULT_DSN = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://app:app_password_change_me@localhost:5432/magflow",
)

# Test configuration
TEST_ITERATIONS = 3
TEST_BATCH_SIZE = 3

# Generate a unique table name for this test run
TEST_TABLE_NAME = f"test_products_{str(uuid.uuid4()).replace('-', '_')}"


def create_test_table(conn: psycopg2.extensions.connection) -> None:
    """Create the test table with the unique name."""
    with conn.cursor() as cur:
        cur.execute(
            f"""
            CREATE TABLE {TEST_TABLE_NAME} (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                price DECIMAL(10,2),
                stock INTEGER,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """
        )
        conn.commit()


def drop_test_table(conn: psycopg2.extensions.connection) -> None:
    """Drop the test table if it exists."""
    with conn.cursor() as cur:
        cur.execute(
            f"""
            DROP TABLE IF EXISTS {TEST_TABLE_NAME} CASCADE;
            DROP SEQUENCE IF EXISTS {TEST_TABLE_NAME}_id_seq CASCADE;
        """
        )
        conn.commit()


@pytest.fixture(scope="function")
def db_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """Create a database connection fixture with automatic cleanup."""
    conn: Optional[psycopg2.extensions.connection] = None
    try:
        conn = psycopg2.connect(DEFAULT_DSN)
        conn.autocommit = False

        # Clean up any existing test table (in case of previous failures)
        drop_test_table(conn)

        # Create fresh test table
        create_test_table(conn)

        yield conn

    except psycopg2.Error as e:
        print(f"Database error: {e}")
        raise
    finally:
        if conn is not None:
            try:
                # Clean up
                drop_test_table(conn)
                conn.close()
            except Exception as e:
                print(f"Error during cleanup: {e}")
                conn.close()


def insert_test_data(conn: psycopg2.extensions.connection, count: int) -> None:
    """Insert test data into the test table."""
    data = [(f"Product {i}", i * 10.5, i * 2) for i in range(1, count + 1)]
    with conn.cursor() as cur:
        execute_batch(
            cur,
            f"INSERT INTO {TEST_TABLE_NAME} (name, price, stock) VALUES (%s, %s, %s)",
            data,
        )
        conn.commit()


def test_simple_select(db_connection: psycopg2.extensions.connection) -> None:
    """Test simple SELECT query with prepared statements."""
    # Insert test data
    insert_test_data(db_connection, 5)

    # Test simple SELECT
    with db_connection.cursor() as cur:
        cur.execute(f"SELECT * FROM {TEST_TABLE_NAME} WHERE price > %s", (20,))
        results = cur.fetchall()
        assert len(results) >= 2  # At least 2 products should have price > 20


def test_batch_insert(db_connection: psycopg2.extensions.connection) -> None:
    """Test batch insert performance with prepared statements."""
    data = [(f"Batch Product {i}", i * 5.5, i) for i in range(TEST_BATCH_SIZE)]

    # Test batch insert
    with db_connection.cursor() as cur:
        execute_batch(
            cur,
            f"INSERT INTO {TEST_TABLE_NAME} (name, price, stock) VALUES (%s, %s, %s)",
            data,
        )
        db_connection.commit()

    # Verify the data was inserted
    with db_connection.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {TEST_TABLE_NAME}")
        count = cur.fetchone()[0]
        assert count == TEST_BATCH_SIZE


def test_parameterized_query(db_connection: psycopg2.extensions.connection) -> None:
    """Test parameterized queries with different parameter types."""
    # Insert test data
    insert_test_data(db_connection, 3)

    # Test with different parameter types
    with db_connection.cursor() as cur:
        # Test with integer parameter
        cur.execute(f"SELECT * FROM {TEST_TABLE_NAME} WHERE stock > %s", (1,))
        results = cur.fetchall()
        assert len(results) >= 1

        # Test with string parameter
        cur.execute(
            f"SELECT * FROM {TEST_TABLE_NAME} WHERE name LIKE %s", ("Product%",)
        )
        results = cur.fetchall()
        assert len(results) == 3

        # Test with NULL value
        cur.execute(
            f"INSERT INTO {TEST_TABLE_NAME} (name, price, stock) VALUES (%s, %s, %s)",
            ("Special Product", None, None),
        )
        db_connection.commit()

        cur.execute(f"SELECT * FROM {TEST_TABLE_NAME} WHERE price IS NULL")
        result = cur.fetchone()
        assert result is not None
        assert result[1] == "Special Product"  # name
        assert result[2] is None  # price
        assert result[3] is None  # stock
