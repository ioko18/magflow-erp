#!/usr/bin/env python3
"""
Test script to verify PgBouncer TLS and prepared statements configuration.
"""

import ssl
import psycopg
import argparse
import time
from typing import Dict, Any
import json


def test_tls_connection(dsn: str, ssl_context: ssl.SSLContext) -> Dict[str, Any]:
    """Test TLS connection to PgBouncer."""
    start_time = time.time()
    try:
        with psycopg.connect(dsn, sslcontext=ssl_context) as conn:
            with conn.cursor() as cur:
                # Test basic query
                cur.execute("SELECT 1")
                cur.fetchone()  # Verify query works

                # Check if SSL is being used
                cur.execute("SHOW ssl")
                ssl_enabled = cur.fetchone()[0] == "on"

                # Get PgBouncer version
                cur.execute("SHOW VERSION")
                version = cur.fetchone()[0]

                # Check prepared statements
                cur.execute("SHOW config")
                config = dict(row for row in cur.fetchall())

                return {
                    "status": "success",
                    "ssl_enabled": ssl_enabled,
                    "version": version,
                    "config": {
                        "max_prepared_statements": config.get(
                            "max_prepared_statements"
                        ),
                        "server_reset_query": config.get("server_reset_query"),
                        "pool_mode": config.get("pool_mode"),
                        "default_pool_size": config.get("default_pool_size"),
                    },
                    "query_time_ms": (time.time() - start_time) * 1000,
                }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "query_time_ms": (time.time() - start_time) * 1000,
        }


def test_prepared_statements(
    dsn: str, ssl_context: ssl.SSLContext, num_queries: int = 10
) -> Dict[str, Any]:
    """Test prepared statements with PgBouncer."""
    results = []
    query = "SELECT $1::text as test, now() as ts"

    try:
        with psycopg.connect(dsn, sslcontext=ssl_context) as conn:
            for i in range(num_queries):
                start_time = time.time()
                with conn.cursor() as cur:
                    # Test prepared statement
                    cur.execute(query, (f"test_{i}",), prepare=True)
                    result = cur.fetchone()

                    # Test unprepared statement for comparison
                    cur.execute(f"SELECT 'test_{i}' as test, now() as ts")

                    results.append(
                        {
                            "iteration": i,
                            "query_time_ms": (time.time() - start_time) * 1000,
                            "result": result[0] if result else None,
                        }
                    )

        # Calculate statistics
        times = [r["query_time_ms"] for r in results]
        return {
            "status": "success",
            "num_queries": len(results),
            "avg_time_ms": sum(times) / len(times),
            "min_time_ms": min(times),
            "max_time_ms": max(times),
            "results": results[:5],  # Return first 5 results as sample
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "results_so_far": results}


def main():
    parser = argparse.ArgumentParser(
        description="Test PgBouncer TLS and Prepared Statements"
    )
    parser.add_argument("--dsn", required=True, help="Database connection string")
    parser.add_argument("--ca-cert", help="Path to CA certificate")
    parser.add_argument("--client-cert", help="Path to client certificate")
    parser.add_argument("--client-key", help="Path to client key")
    parser.add_argument(
        "--test-prepared", action="store_true", help="Test prepared statements"
    )
    parser.add_argument(
        "--num-queries", type=int, default=10, help="Number of queries to test"
    )

    args = parser.parse_args()

    # Set up SSL context
    ssl_context = ssl.create_default_context(
        ssl.Purpose.SERVER_AUTH, cafile=args.ca_cert
    )

    if args.client_cert and args.client_key:
        ssl_context.load_cert_chain(certfile=args.client_cert, keyfile=args.client_key)

    # Test TLS connection
    print("Testing TLS connection...")
    tls_result = test_tls_connection(args.dsn, ssl_context)
    print(json.dumps(tls_result, indent=2))

    if tls_result["status"] != "success":
        print("TLS connection test failed")
        return

    # Test prepared statements if requested
    if args.test_prepared:
        print("\nTesting prepared statements...")
        prep_result = test_prepared_statements(args.dsn, ssl_context, args.num_queries)
        print(json.dumps(prep_result, indent=2))


if __name__ == "__main__":
    main()
