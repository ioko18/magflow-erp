#!/bin/bash
# MagFlow ERP - Enhanced Test Runner with Environment Setup
# This script sets up the test environment and runs pytest with complete output

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PARALLEL=false
COVERAGE=false
VERBOSE=false
TIMEOUT=300
WORKERS=4

# Parse command line arguments
function show_help() {
    echo "Usage: $0 [OPTIONS] [PYTEST_ARGS...]"
    echo ""
    echo "Options:"
    echo "  -p, --parallel     Enable parallel test execution"
    echo "  -c, --coverage     Enable coverage reporting"
    echo "  -v, --verbose      Enable verbose output"
    echo "  -t, --timeout SEC  Set test timeout in seconds (default: 300)"
    echo "  -w, --workers NUM  Number of parallel workers (default: 4)"
    echo "  -h, --help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                           # Run tests normally"
    echo "  $0 -p -c                     # Run with parallel execution and coverage"
    echo "  $0 -t 600 -w 2              # Run with 10min timeout and 2 workers"
    echo "  $0 -m \"not slow\"            # Run specific pytest markers"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -w|--workers)
            WORKERS="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            break
            ;;
    esac
done

# Print header
echo -e "${BLUE}🚀 MagFlow ERP - Enhanced Test Runner${NC}"
echo "===================================="
echo ""

# Set test environment variables
export APP_ENV=test
export SECRET_KEY="test-secret-key-for-pytest-123456789012345678901234567890"
export JWT_SECRET_KEY="test-jwt-secret-key-123456789012345678901234567890"
export REFRESH_SECRET_KEY="test-refresh-secret-key-123456789012345678901234567890"
export ALGORITHM="HS256"
export DATABASE_URL="sqlite+aiosqlite:///./test_magflow.db"
export ACCESS_TOKEN_EXPIRE_MINUTES=30
export REFRESH_TOKEN_EXPIRE_DAYS=7
export EMAIL_RESET_TOKEN_EXPIRE_HOURS=24
export REDIS_URL="redis://localhost:6379/0"

# Set Python path
export PYTHONPATH="${PYTHONPATH}:."
export PYTHONDONTWRITEBYTECODE=1

# Display configuration
echo -e "${BLUE}🔧 Test Environment Configuration:${NC}"
echo "  Environment: $APP_ENV"
echo "  Database: $DATABASE_URL"
echo "  Parallel: $PARALLEL ($WORKERS workers)"
echo "  Coverage: $COVERAGE"
echo "  Timeout: ${TIMEOUT}s"
echo "  Verbose: $VERBOSE"
echo ""

# Build pytest arguments - start with minimal set
PYTEST_ARGS=("-v")

# Add parallel execution
if [ "$PARALLEL" = true ]; then
    echo -e "${YELLOW}🔄 Enabling parallel execution with $WORKERS workers${NC}"
    PYTEST_ARGS+=("-n" "$WORKERS")
fi

# Add coverage reporting
if [ "$COVERAGE" = true ]; then
    echo -e "${YELLOW}📊 Enabling coverage reporting${NC}"
    PYTEST_ARGS+=("--cov=app" "--cov-report=term-missing" "--cov-report=html:htmlcov" "--cov-fail-under=60")
fi

# Add verbose output
if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS+=("-s" "--log-cli-level=INFO")
fi

# Clean up any existing test database
if [[ "$DATABASE_URL" == sqlite* ]]; then
    TEST_DB_PATH=$(echo "$DATABASE_URL" | sed 's|sqlite:///||')
    if [ -f "$TEST_DB_PATH" ]; then
        echo -e "${YELLOW}🗑️  Removing existing test database: $TEST_DB_PATH${NC}"
        rm -f "$TEST_DB_PATH"
    fi
fi

# Function to show test results summary
function show_test_summary() {
    local exit_code=$?
    echo ""
    echo -e "${BLUE}📊 Test Execution Summary${NC}"
    echo "========================="
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ All tests PASSED successfully!${NC}"
        echo "🎉 Test suite completed without failures"
        if [ "$COVERAGE" = true ]; then
            echo -e "${GREEN}📈 Coverage report generated in htmlcov/index.html${NC}"
        fi
    else
        echo -e "${RED}❌ Some tests FAILED${NC}"
        echo "🔍 Check the output above for detailed error information"
        echo "💡 Try running: $0 -v  # for more verbose output"
    fi
    echo ""
    return $exit_code
}

# Trap to ensure we show summary even if interrupted
trap show_test_summary EXIT

# Run the tests with complete output
echo -e "${BLUE}🧪 Running tests...${NC}"
echo "Arguments: $@"
echo ""

# Use python3 and ensure we capture all output
python3 -m pytest "${PYTEST_ARGS[@]}" "$@"

# Show summary (this will also be called by trap)
show_test_summary

# Exit with the same code as pytest
exit $exit_code
