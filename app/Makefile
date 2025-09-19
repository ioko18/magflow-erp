.PHONY: help install test test-unit test-integration test-e2e test-cov lint format type-check check pre-commit-install pre-commit-run pre-commit-update clean

# Default target
help:
	@echo "Available commands:"
	@echo "  install           Install development dependencies"
	@echo "  test              Run all tests"
	@echo "  test-unit         Run unit tests"
	@echo "  test-integration  Run integration tests"
	@echo "  test-e2e          Run end-to-end tests"
	@echo "  test-cov          Run tests with coverage report"
	@echo "  lint              Run linters (ruff, black, isort)"
	@echo "  format            Format code (black, isort)"
	@echo "  type-check        Run static type checking"
	@echo "  check             Run all checks (lint, format, type-check)"
	@echo "  pre-commit-install  Install pre-commit hooks"
	@echo "  pre-commit-run     Run pre-commit on all files"
	@echo "  pre-commit-update  Update pre-commit hooks"
	@echo "  clean             Clean up temporary files"

# Install development dependencies
install:
	pip install -r requirements-test.txt
	pre-commit install

# Testing
TEST_ARGS ?= -v --durations=10
TEST_PATH ?= tests/

# Run all tests
test:
	pytest $(TEST_ARGS) $(TEST_PATH)

# Run unit tests
test-unit:
	pytest $(TEST_ARGS) -m "unit" $(TEST_PATH)

# Run integration tests
test-integration:
	pytest $(TEST_ARGS) -m "integration" $(TEST_PATH)

# Run end-to-end tests
test-e2e:
	pytest $(TEST_ARGS) -m "e2e" $(TEST_PATH)

# Run tests with coverage
test-cov:
	pytest $(TEST_ARGS) --cov=app --cov-report=term-missing --cov-report=xml --cov-report=html $(TEST_PATH)

# Linting and formatting
lint:
	ruff check .
	black --check .
	isort --check-only .

format:
	black .
	isort .

# Type checking
type-check:
	mypy .

# Run all checks
check: lint format type-check

# Pre-commit
pre-commit-install:
	pre-commit install

pre-commit-run:
	pre-commit run --all-files

pre-commit-update:
	pre-commit autoupdate

# Clean up
clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".mypy_cache" -exec rm -r {} +
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/ .ruff_cache/ build/ dist/ *.egg-info/
	@chmod +x scripts/run_perf_test.sh
	@DURATION=30s USERS=10 SPAWN_RATE=5 ./scripts/run_perf_test.sh

# Run integration tests
test-int:
	@echo "🚀 Running integration tests..."
	@pytest tests/integration -v --asyncio-mode=auto
