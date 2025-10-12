#!/usr/bin/env python3
"""
Test runner for MagFlow ERP project.

Usage:
    ./run_tests.py [options] [test_paths...]

Options:
    -h, --help      Show this help
    -v, --verbose   Verbose output
    -k EXPR         Only run tests which match the given substring expression
    -m MARKER       Only run tests matching given mark expression
    --unit          Run only unit tests
    --integration   Run only integration tests
    --api           Run only API tests
    --all           Run all tests (default)
    --cov           Run with coverage report
    --no-cov        Disable coverage report
"""
import argparse
import subprocess
import sys
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.absolute()
TEST_DIR = PROJECT_ROOT / "tests"

def run_tests(test_paths=None, marker=None, verbose=False, coverage=True):
    """Run tests with the given options."""
    cmd = [sys.executable, "-m", "pytest", "-v" if verbose else "-v"]

    # Add coverage if enabled
    if coverage:
        cmd.extend([
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-config=.coveragerc"
        ])

    # Add marker if specified
    if marker:
        cmd.append(f"-m {marker}")

    # Add test paths
    if test_paths:
        cmd.extend(str(path) for path in test_paths)
    else:
        cmd.append(str(TEST_DIR))

    # Run the command
    return subprocess.call(cmd)

def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(description="Run MagFlow ERP tests")
    parser.add_argument(
        "test_paths", nargs="*",
        help="Test files or directories to run"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "-k", metavar="EXPR",
        help="Only run tests which match the given substring expression"
    )
    parser.add_argument(
        "-m", metavar="MARKER",
        help="Only run tests matching given mark expression"
    )
    parser.add_argument(
        "--unit", action="store_const", dest="marker", const="unit",
        help="Run only unit tests"
    )
    parser.add_argument(
        "--integration", action="store_const", dest="marker", const="integration",
        help="Run only integration tests"
    )
    parser.add_argument(
        "--api", action="store_const", dest="marker", const="api",
        help="Run only API tests"
    )
    parser.add_argument(
        "--cov/--no-cov", dest="coverage", default=True,
        help="Enable/disable coverage reporting (default: enabled)"
    )

    args = parser.parse_args()

    # Set default marker if test type is specified
    if not args.marker and any((args.unit, args.integration, args.api)):
        if args.unit:
            args.marker = "unit"
        elif args.integration:
            args.marker = "integration"
        elif args.api:
            args.marker = "api"

    # Run tests
    return run_tests(
        test_paths=args.test_paths,
        marker=args.marker,
        verbose=args.verbose,
        coverage=args.coverage
    )

if __name__ == "__main__":
    sys.exit(main())
