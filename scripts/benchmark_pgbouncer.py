#!/usr/bin/env python3
"""
PgBouncer Prepared Statements Benchmark with TLS Support

This script benchmarks prepared statements with PgBouncer in transaction pooling mode.
It tests both prepared and non-prepared queries to compare performance with TLS support.
"""

import argparse
import os
import pathlib
import ssl
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

import psycopg


@dataclass
class BenchmarkConfig:
    """Configuration for the benchmark."""

    dsn: str
    warmup_queries: int = 1000
    test_queries: int = 10000
    num_threads: int = 10
    use_ssl: bool = True
    ssl_cert: str | None = None
    ssl_key: str | None = None
    ssl_root_cert: str | None = None
    connection_timeout: int = 10
    statement_timeout: int = 30


class PgBouncerBenchmark:
    """Benchmark PgBouncer with prepared statements and TLS."""

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.results: dict[str, list[float]] = {
            "prepared": [],
            "unprepared": [],
            "prepared_concurrent": [],
            "unprepared_concurrent": [],
        }
        self.connection_params: dict[str, Any] = {
            "autocommit": True,
            "connect_timeout": config.connection_timeout,
            "options": f"-c statement_timeout={config.statement_timeout}s",
        }

        # Configure SSL if enabled
        if config.use_ssl:
            ssl_context = ssl.create_default_context(
                ssl.Purpose.SERVER_AUTH, cafile=config.ssl_root_cert
            )
            if config.ssl_cert and config.ssl_key:
                ssl_context.load_cert_chain(
                    certfile=config.ssl_cert, keyfile=config.ssl_key
                )
            self.connection_params["sslmode"] = "verify-full"
            self.connection_params["sslcontext"] = ssl_context

    def get_connection(self) -> psycopg.Connection:
        """Get a new connection to the database with configured parameters."""
        try:
            return psycopg.connect(self.config.dsn, **self.connection_params)
        except Exception as e:
            print(f"Error connecting to database: {e}")
            raise

    def warmup(self):
        """Warm up the connection pool and prepare statements."""
        print(f"Warming up with {self.config.warmup_queries} queries...")
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Test both prepared and unprepared queries
                    for i in range(self.config.warmup_queries // 2):
                        # Prepared
                        cur.execute("SELECT $1::int", (i,), prepare=True)
                        cur.fetchone()

                        # Unprepared
                        cur.execute(f"SELECT {i}")
                        cur.fetchone()
            print("Warmup completed successfully.")
        except Exception as e:
            print(f"Warning: Warmup failed: {e}")
            raise

    def run_benchmark(self, use_prepared: bool, num_queries: int) -> list[float]:
        """Run benchmark with or without prepared statements."""
        query = "SELECT $1::text as test, now() as ts"
        times = []

        try:
            with self.get_connection() as conn:
                for i in range(num_queries):
                    try:
                        start_time = time.perf_counter()
                        with conn.cursor() as cur:
                            if use_prepared:
                                cur.execute(query, (f"test_{i}",), prepare=True)
                            else:
                                cur.execute(f"SELECT '{i}' as test, now() as ts")
                            cur.fetchone()
                        end_time = time.perf_counter()
                        times.append((end_time - start_time) * 1000)  # Convert to ms
                    except Exception as e:
                        print(f"Query {i} failed: {e}")
                        continue
        except Exception as e:
            print(f"Connection failed: {e}")
            raise

        return times

    def run_concurrent_benchmark(
        self, use_prepared: bool, num_queries: int, num_threads: int = 10
    ) -> list[float]:
        """Run benchmark with concurrent connections."""
        queries_per_thread = max(1, num_queries // num_threads)
        total_queries = queries_per_thread * num_threads
        print(
            f"Running {total_queries} queries across {num_threads} threads "
            f"({queries_per_thread} queries/thread) - "
            f"{'prepared' if use_prepared else 'unprepared'}"
        )

        def worker(_) -> list[float]:
            try:
                return self.run_benchmark(use_prepared, queries_per_thread)
            except Exception as e:
                print(f"Worker failed: {e}")
                return []

        all_times = []
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]
            for future in as_completed(futures):
                try:
                    result = future.result()
                    all_times.extend(result)
                except Exception as e:
                    print(f"Error in worker: {e}")

        return all_times

    def print_stats(self, times: list[float], label: str):
        """Print statistics for a set of timings."""
        if not times:
            print(f"\n{label.upper()}: No results")
            return

        total_queries = len(times)
        total_time = sum(times) / 1000  # Convert to seconds
        qps = total_queries / total_time if total_time > 0 else 0

        avg = statistics.mean(times)
        median = statistics.median(times)
        min_t = min(times)
        max_t = max(times)
        p95 = statistics.quantiles(times, n=20)[-1] if len(times) > 1 else times[0]

        print(f"\n{label.upper()} STATISTICS:")
        print(f"  Queries:       {total_queries}")
        print(f"  Total time:    {total_time:.2f} s")
        print(f"  Queries/s:     {qps:.2f}")
        print(f"  Average:       {avg:.2f} ms")
        print(f"  Median:        {median:.2f} ms")
        print(f"  Min:           {min_t:.2f} ms")
        print(f"  Max:           {max_t:.2f} ms")
        print(f"  95th %-tile:   {p95:.2f} ms")

    def run(self):
        """Run the full benchmark suite."""
        print("\n" + "=" * 80)
        print(" PgBouncer Prepared Statements Benchmark ")
        print("=" * 80)
        print(f"DSN: {self.config.dsn}")
        print(f"Threads: {self.config.num_threads}")
        print(f"Warmup queries: {self.config.warmup_queries}")
        print(f"Test queries: {self.config.test_queries}")
        print(f"TLS: {'Enabled' if self.config.use_ssl else 'Disabled'}")
        if self.config.use_ssl:
            print(f"SSL Cert: {self.config.ssl_cert}")
            print(f"SSL Key: {self.config.ssl_key}")
            print(f"SSL Root Cert: {self.config.ssl_root_cert}")
        print("-" * 80)

        # Warm up connections
        self.warmup()

        # Run sequential benchmarks
        print("\nRunning sequential benchmarks...")
        self.results["prepared"] = self.run_benchmark(True, self.config.test_queries)
        self.print_stats(self.results["prepared"], "Sequential Prepared")

        self.results["unprepared"] = self.run_benchmark(False, self.config.test_queries)
        self.print_stats(self.results["unprepared"], "Sequential Unprepared")

        # Run concurrent benchmarks
        print("\nRunning concurrent benchmarks...")
        self.results["prepared_concurrent"] = self.run_concurrent_benchmark(
            True, self.config.test_queries, self.config.num_threads
        )
        self.print_stats(self.results["prepared_concurrent"], "Concurrent Prepared")

        self.results["unprepared_concurrent"] = self.run_concurrent_benchmark(
            False, self.config.test_queries, self.config.num_threads
        )
        self.print_stats(self.results["unprepared_concurrent"], "Concurrent Unprepared")

        # Print summary
        self.print_summary()

        # Test with prepared statements
        print("\nTesting with prepared statements...")
        prepared_times = self.run_concurrent_benchmark(
            use_prepared=True,
            num_queries=self.config.test_queries,
            num_threads=self.config.num_threads,
        )
        self.results["prepared"] = prepared_times
        self.print_stats(prepared_times, "Prepared Statements")

        # Test without prepared statements
        print("\nTesting without prepared statements...")
        unprepared_times = self.run_concurrent_benchmark(
            use_prepared=False,
            num_queries=self.config.test_queries,
            num_threads=self.config.num_threads,
        )
        self.results["unprepared"] = unprepared_times
        self.print_stats(unprepared_times, "Unprepared Statements")


def main():
    """Main entry point for the benchmark script."""
    parser = argparse.ArgumentParser(
        description="PgBouncer Prepared Statements Benchmark with TLS"
    )
    parser.add_argument(
        "--dsn",
        default=os.getenv("DATABASE_URL"),
        help="Database connection string (default: $DATABASE_URL)",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=1000,
        help="Number of warmup queries (default: 1000)",
    )
    parser.add_argument(
        "--queries",
        type=int,
        default=10000,
        help="Number of test queries (default: 10000)",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=10,
        help="Number of concurrent threads (default: 10)",
    )
    parser.add_argument(
        "--no-ssl",
        action="store_true",
        help="Disable SSL/TLS (not recommended for production)",
    )
    parser.add_argument(
        "--ssl-cert",
        default=os.getenv("PGSSLCERT"),
        help="Path to SSL client certificate (default: $PGSSLCERT)",
    )
    parser.add_argument(
        "--ssl-key",
        default=os.getenv("PGSSLKEY"),
        help="Path to SSL client key (default: $PGSSLKEY)",
    )
    parser.add_argument(
        "--ssl-root-cert",
        default=os.getenv("PGSSLROOTCERT"),
        help="Path to SSL root certificate (default: $PGSSLROOTCERT)",
    )

    args = parser.parse_args()

    if not args.dsn:
        print(
            "Error: Please provide a database connection string via --dsn or "
            "DATABASE_URL environment variable"
        )
        return

    # Set default SSL paths if not provided
    certs_dir = pathlib.Path(__file__).parent.parent / "certs"
    ssl_cert = args.ssl_cert or str(certs_dir / "postgresql.crt")
    ssl_key = args.ssl_key or str(certs_dir / "postgresql.key")
    ssl_root_cert = args.ssl_root_cert or str(certs_dir / "ca" / "ca.crt")

    config = BenchmarkConfig(
        dsn=args.dsn,
        warmup_queries=args.warmup,
        test_queries=args.queries,
        num_threads=args.threads,
        use_ssl=not args.no_ssl,
        ssl_cert=ssl_cert if not args.no_ssl and os.path.exists(ssl_cert) else None,
        ssl_key=ssl_key if not args.no_ssl and os.path.exists(ssl_key) else None,
        ssl_root_cert=(
            ssl_root_cert if not args.no_ssl and os.path.exists(ssl_root_cert) else None
        ),
    )

    benchmark = PgBouncerBenchmark(config)
    benchmark.run(num_threads=args.threads)


if __name__ == "__main__":
    main()
