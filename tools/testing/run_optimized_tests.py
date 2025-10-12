#!/usr/bin/env python3
"""
Optimized Test Runner for MagFlow ERP
=====================================

This script runs the optimized test suite with performance monitoring
and provides detailed performance reports.

Usage:
    python run_optimized_tests.py [test_path]

Examples:
    python run_optimized_tests.py                    # Run all unit tests
    python run_optimized_tests.py tests/unit         # Run unit tests only
    python run_optimized_tests.py tests/unit/test_products_api_new.py  # Run specific test file
"""

import os
import subprocess
import sys
import time
from pathlib import Path


def setup_environment():
    """Setup optimized test environment."""
    # Set environment variables for testing
    os.environ["TESTING"] = "true"
    os.environ["ENVIRONMENT"] = "test"
    os.environ["SQL_ECHO"] = "false"
    os.environ["LOG_LEVEL"] = "ERROR"

    # Use optimized pytest configuration
    pytest_config = Path(__file__).parent / "pytest.ini.optimized"
    if pytest_config.exists():
        os.environ["PYTEST_CONFIG"] = str(pytest_config)


def run_optimized_tests(test_path="tests/unit"):
    """Run optimized tests with performance monitoring."""
    setup_environment()

    print("🚀 MagFlow ERP Optimized Test Runner")
    print("=" * 50)
    print(f"Running tests from: {test_path}")
    print("Optimizations enabled:")
    print("  ✅ Session-scoped database engine")
    print("  ✅ Connection pooling optimization")
    print("  ✅ Schema caching")
    print("  ✅ Transaction isolation")
    print("  ✅ Fixture optimization")
    print("=" * 50)

    start_time = time.time()

    # Build pytest command with optimizations
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        test_path,
        "-v",
        "--tb=short",
        "--durations=10",
        "--asyncio-mode=auto",
        "--disable-warnings",
        "--no-cov",
        "-p",
        "no:warnings",
        "--maxfail=5",
    ]

    try:
        # Run the tests
        result = subprocess.run(cmd, capture_output=False, text=True)

        total_time = time.time() - start_time

        print("\n" + "=" * 50)
        print("🏁 Test Execution Complete")
        print("=" * 50)
        print(f"Total execution time: {total_time:.2f}s")

        if result.returncode == 0:
            print("✅ All tests passed!")
            print("\n🎯 Performance Target: <0.1s setup time per test")
            print("📊 Check the performance report above for detailed metrics")
        else:
            print("❌ Some tests failed")
            print(f"Exit code: {result.returncode}")

        return result.returncode

    except KeyboardInterrupt:
        print("\n⏹️  Test execution interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        return 1


def main():
    """Main entry point."""
    test_path = sys.argv[1] if len(sys.argv) > 1 else "tests/unit"

    # Ensure we're in the project root
    project_root = Path(__file__).parent
    os.chdir(project_root)

    exit_code = run_optimized_tests(test_path)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
