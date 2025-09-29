"""Test PgBouncer TLS and prepared statements configuration."""

import os
import ssl
import time

import pytest
import psycopg

# Skip these tests by default since they require a running PgBouncer with TLS
pytestmark = pytest.mark.skipif(
    os.getenv("TEST_PGBOUNCER") != "true",
    reason="PgBouncer tests require TEST_PGBOUNCER=true environment variable",
)


@pytest.fixture(scope="module")
def pgbouncer_dsn() -> str:
    """Get PgBouncer DSN from environment or use default."""
    return os.getenv(
        "TEST_PGBOUNCER_DSN", "postgresql://postgres:postgres@localhost:6432/postgres"
    )


@pytest.fixture(scope="module")
def ssl_context() -> ssl.SSLContext:
    """Create SSL context for PgBouncer connection."""
    ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

    # Optional: Configure client certificates if available
    ca_cert = os.getenv("PGBOUNCER_CA_CERT")
    client_cert = os.getenv("PGBOUNCER_CLIENT_CERT")
    client_key = os.getenv("PGBOUNCER_CLIENT_KEY")

    if ca_cert:
        ssl_context.load_verify_locations(cafile=ca_cert)

    if client_cert and client_key:
        ssl_context.load_cert_chain(certfile=client_cert, keyfile=client_key)

    return ssl_context


def test_tls_connection(pgbouncer_dsn: str, ssl_context: ssl.SSLContext) -> None:
    """Test TLS connection to PgBouncer."""
    start_time = time.time()
    with psycopg.connect(pgbouncer_dsn, sslcontext=ssl_context) as conn:
        with conn.cursor() as cur:
            # Test basic query
            cur.execute("SELECT 1")
            result = cur.fetchone()
            assert result[0] == 1

            # Check if SSL is being used
            cur.execute("SHOW ssl")
            ssl_enabled = cur.fetchone()[0] == "on"
            assert ssl_enabled is True

            # Get PgBouncer version
            cur.execute("SHOW VERSION")
            version = cur.fetchone()[0]
            assert version is not None

            # Check prepared statements configuration
            cur.execute("SHOW config")
            config = dict(row for row in cur.fetchall())

            assert (
                config.get("pool_mode") == "transaction"
            )  # or "session" based on your config
            assert int(config.get("default_pool_size", 0)) > 0

            query_time = (time.time() - start_time) * 1000
            print(f"\nPgBouncer TLS test completed in {query_time:.2f}ms")


@pytest.mark.parametrize("num_queries", [5])  # Reduced from 10 to 5 for faster tests
def test_prepared_statements(
    pgbouncer_dsn: str,
    ssl_context: ssl.SSLContext,
    num_queries: int,
) -> None:
    """Test prepared statements with PgBouncer."""
    results = []
    query = "SELECT $1::text as test, now() as ts"

    with psycopg.connect(pgbouncer_dsn, sslcontext=ssl_context) as conn:
        for i in range(num_queries):
            start_time = time.time()
            with conn.cursor() as cur:
                # Test prepared statement
                cur.execute(query, (f"test_{i}",), prepare=True)
                result = cur.fetchone()
                assert result is not None
                assert result[0] == f"test_{i}"

                # Test unprepared statement for comparison
                cur.execute(f"SELECT 'test_{i}' as test, now() as ts")
                unprepared_result = cur.fetchone()
                assert unprepared_result is not None
                assert unprepared_result[0] == f"test_{i}"

                # Record timing
                query_time = (time.time() - start_time) * 1000
                results.append(
                    {
                        "iteration": i,
                        "query_time_ms": query_time,
                        "result": result[0],
                    }
                )

    # Verify results
    assert len(results) == num_queries

    # Log performance metrics
    times = [r["query_time_ms"] for r in results]
    avg_time = sum(times) / len(times)
    print(f"\nPrepared statements test completed with {num_queries} queries")
    print(f"  - Average time per query: {avg_time:.2f}ms")
    print(f"  - Min time: {min(times):.2f}ms")
    print(f"  - Max time: {max(times):.2f}ms")
