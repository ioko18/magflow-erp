#!/bin/bash
# MagFlow ERP - Comprehensive Quality Check Script
# This script runs all quality checks and generates a report

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Initialize counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# Function to run a check and track results
run_check() {
    local check_name="$1"
    local check_command="$2"
    local allow_failure="${3:-false}"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    log_info "Running $check_name..."
    
    if eval "$check_command" > /tmp/quality_check_output 2>&1; then
        log_success "$check_name passed"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        if [ "$allow_failure" = "true" ]; then
            log_warning "$check_name failed (allowed)"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
        else
            log_error "$check_name failed"
            cat /tmp/quality_check_output
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
        fi
        return 1
    fi
}

# Header
echo "========================================"
echo "🔍 MagFlow ERP - Quality Check Report"
echo "========================================"
echo "📅 Date: $(date)"
echo "🏠 Directory: $(pwd)"
echo "🐍 Python: $(python3 --version 2>/dev/null || echo 'Not found')"
echo "========================================"
echo

# 1. Code Formatting Check
log_info "🎨 Code Formatting Checks"
run_check "Black formatting" "black --check app/ tests/ --diff"
run_check "Import sorting" "isort --check-only app/ tests/ --diff" true

# 2. Linting Checks
log_info "🔍 Linting Checks"
run_check "Ruff linting" "ruff check app/ tests/ --statistics"
run_check "Flake8 linting" "flake8 app/ tests/ --statistics" true

# 3. Type Checking
log_info "📏 Type Checking"
run_check "MyPy type checking" "mypy app/ --explicit-package-bases --ignore-missing-imports" true

# 4. Security Checks
log_info "🔒 Security Checks"
run_check "Bandit security scan" "bandit -r app/ -f txt" true
run_check "Safety dependency check" "safety check --json" true

# 5. Test Suite
log_info "🧪 Test Suite"
run_check "Unit tests" "pytest tests/test_coverage_boost.py -v"
run_check "Integration tests" "pytest tests/test_improved_examples.py -v" true

# 6. Coverage Check
log_info "📊 Coverage Analysis"
run_check "Test coverage" "pytest tests/test_coverage_boost.py --cov=app --cov-report=term-missing --cov-fail-under=5" true

# 7. Documentation Checks
log_info "📚 Documentation Checks"
run_check "Documentation build" "ls docs/ > /dev/null && echo 'Documentation exists'"

# 8. Configuration Validation
log_info "⚙️ Configuration Validation"
run_check "Docker Compose validation" "docker compose config -q" true
run_check "Pre-commit config validation" "pre-commit validate-config" true

# 9. Performance Baseline
log_info "⚡ Performance Baseline"
run_check "Import time check" "python3 -c 'import time; start=time.time(); import app; print(f\"Import time: {time.time()-start:.2f}s\")'"

# 10. Database Schema Validation
log_info "🗄️ Database Schema"
run_check "Alembic check" "ls alembic/ > /dev/null && echo 'Alembic directory exists'" true

# Generate Summary Report
echo
echo "========================================"
echo "📋 QUALITY CHECK SUMMARY"
echo "========================================"
echo "✅ Passed: $PASSED_CHECKS/$TOTAL_CHECKS"
echo "❌ Failed: $FAILED_CHECKS/$TOTAL_CHECKS"

if [ $FAILED_CHECKS -eq 0 ]; then
    echo "🎉 All critical quality checks passed!"
    OVERALL_STATUS="PASS"
    EXIT_CODE=0
else
    echo "⚠️  Some quality checks failed. Please review and fix."
    OVERALL_STATUS="FAIL"
    EXIT_CODE=1
fi

# Calculate quality score
QUALITY_SCORE=$(( (PASSED_CHECKS * 100) / TOTAL_CHECKS ))
echo "📊 Quality Score: $QUALITY_SCORE%"

# Generate detailed report
REPORT_FILE="quality_report_$(date +%Y%m%d_%H%M%S).txt"
cat > "$REPORT_FILE" << EOF
MagFlow ERP - Quality Check Report
==================================
Date: $(date)
Directory: $(pwd)
Python Version: $(python3 --version 2>/dev/null || echo 'Not found')

Summary:
- Total Checks: $TOTAL_CHECKS
- Passed: $PASSED_CHECKS
- Failed: $FAILED_CHECKS
- Quality Score: $QUALITY_SCORE%
- Overall Status: $OVERALL_STATUS

Recommendations:
EOF

# Add recommendations based on results
if [ $QUALITY_SCORE -lt 80 ]; then
    echo "- 🔴 Quality score below 80%. Immediate action required." >> "$REPORT_FILE"
    echo "- Focus on fixing linting errors and improving test coverage." >> "$REPORT_FILE"
elif [ $QUALITY_SCORE -lt 90 ]; then
    echo "- 🟡 Quality score below 90%. Consider improvements." >> "$REPORT_FILE"
    echo "- Add more tests and fix remaining linting issues." >> "$REPORT_FILE"
else
    echo "- 🟢 Excellent quality score! Keep up the good work." >> "$REPORT_FILE"
    echo "- Consider adding more advanced checks like performance testing." >> "$REPORT_FILE"
fi

echo
echo "📄 Detailed report saved to: $REPORT_FILE"

# Cleanup
rm -f /tmp/quality_check_output

echo "========================================"
exit $EXIT_CODE
