#!/usr/bin/env python3
"""
Analyze performance test results and generate a report.
"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestResult:
    name: str
    rps: float
    p50: float
    p95: float
    p99: float
    error_rate: float
    prepared_statements: bool

    def __str__(self):
        return (
            f"{self.name} (Prepared: {self.prepared_statements}):\n"
            f"  RPS: {self.rps:.1f}\n"
            f"  Latency (ms): p50={self.p50:.1f} | p95={self.p95:.1f} | p99={self.p99:.1f}\n"
            f"  Error Rate: {self.error_rate:.2%}"
        )


def parse_stats_file(file_path: Path) -> TestResult | None:
    """Parse a single Locust stats file."""
    try:
        with open(file_path) as f:
            data = json.load(f)

        # Extract test name and prepared statements setting from filename
        name = file_path.stem.replace("_stats", "")
        prepared = "prepared_on" in name

        # Find the "Total" entry which contains aggregate stats
        total_stats = next((s for s in data if s["name"] == "Total"), None)
        if not total_stats:
            return None

        return TestResult(
            name=name.replace("_prepared_on", "").replace("_prepared_off", ""),
            rps=total_stats["total_rps"],
            p50=total_stats["response_time_percentile_50"],
            p95=total_stats["response_time_percentile_95"],
            p99=total_stats["response_time_percentile_99"],
            error_rate=total_stats["fail_ratio"],
            prepared_statements=prepared,
        )
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing {file_path}: {e}")
        return None


def analyze_pgbouncer_metrics(before: Path, after: Path) -> dict[str, float]:
    """Compare PgBouncer metrics before and after test."""

    def parse_metrics(file_path: Path) -> dict[str, float]:
        metrics = {}
        try:
            with open(file_path) as f:
                for line in f:
                    if line.startswith("#") or not line.strip():
                        continue
                    name, value = line.split()
                    metrics[name] = float(value)
        except (FileNotFoundError, ValueError) as e:
            print(f"Error parsing metrics file {file_path}: {e}")
        return metrics

    before_metrics = parse_metrics(before)
    after_metrics = parse_metrics(after)

    # Calculate deltas for key metrics
    deltas = {}
    for key in before_metrics:
        if key in after_metrics:
            deltas[key] = after_metrics[key] - before_metrics.get(key, 0)

    return deltas


def generate_report(results: list[TestResult], results_dir: Path):
    """Generate a performance test report."""
    if not results:
        print("No test results to analyze.")
        return

    # Group results by test name
    tests = {}
    for result in results:
        if result.name not in tests:
            tests[result.name] = []
        tests[result.name].append(result)

    # Generate report
    print("\n📊 Performance Test Report\n" + "=" * 50)

    for test_name, test_results in tests.items():
        print(f"\n🔍 {test_name.upper()}")
        print("-" * (len(test_name) + 2))

        # Compare prepared vs non-prepared
        prepared = [r for r in test_results if r.prepared_statements]
        not_prepared = [r for r in test_results if not r.prepared_statements]

        if prepared:
            print("\nWith Prepared Statements:")
            for r in prepared:
                print(f"  {r}")

        if not_prepared:
            print("\nWithout Prepared Statements:")
            for r in not_prepared:
                print(f"  {r}")

        # Compare performance
        if prepared and not_prepared:
            prep = prepared[0]
            no_prep = not_prepared[0]

            print("\nComparison (Prepared vs Not Prepared):")
            print(
                f"  RPS: {prep.rps:.1f} vs {no_prep.rps:.1f} "
                f"({(prep.rps / no_prep.rps - 1) * 100:+.1f}%)"
            )
            print(
                f"  p95 Latency: {prep.p95:.1f}ms vs {no_prep.p95:.1f}ms "
                f"({(no_prep.p95 / prep.p95 - 1) * 100:+.1f}%)"
            )
            print(f"  Error Rate: {prep.error_rate:.2%} vs {no_prep.error_rate:.2%}")

    # Check for PgBouncer metrics
    pgbouncer_files = list(results_dir.glob("*_pgbouncer_*.prom"))
    if pgbouncer_files:
        print("\n📈 PgBouncer Metrics:")
        print("-" * 20)

        # Group by test
        test_metrics = {}
        for file in pgbouncer_files:
            parts = file.stem.split("_")
            test_name = parts[0]
            metric_type = parts[-1]  # 'before' or 'after'

            if test_name not in test_metrics:
                test_metrics[test_name] = {}
            test_metrics[test_name][metric_type] = file

        # Analyze each test
        for test_name, files in test_metrics.items():
            if "before" in files and "after" in files:
                print(f"\n{test_name}:")
                deltas = analyze_pgbouncer_metrics(files["before"], files["after"])
                for metric, value in deltas.items():
                    print(f"  {metric}: {value:.2f}")

    print("\n✅ Analysis complete!")


def main():
    parser = argparse.ArgumentParser(description="Analyze performance test results")
    parser.add_argument(
        "--results-dir",
        type=str,
        default="./load/results",
        help="Directory containing test results",
    )
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    if not results_dir.exists():
        print(f"Error: Results directory '{results_dir}' not found")
        return 1

    # Find and parse all stats files
    stats_files = list(results_dir.glob("*_stats.json"))
    if not stats_files:
        print(f"No stats files found in {results_dir}")
        return 1

    results = []
    for file in stats_files:
        result = parse_stats_file(file)
        if result:
            results.append(result)

    # Generate the report
    generate_report(results, results_dir)
    return 0


if __name__ == "__main__":
    exit(main())
