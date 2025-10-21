test-emag-client:
	docker compose exec app python test_emag_client.py
seed-orders:
	@echo "Seeding sample orders into local database..."
	@python3 scripts/seed_sample_orders.py
.PHONY: help install test test-unit test-integration test-e2e test-cov lint format type-check check pre-commit-install pre-commit-run pre-commit-update clean start
.PHONY: up up-proxy up-monitoring up-ops down down-keep-data logs prod prod-proxy prod-monitoring prod-otel prod-certs ci ci-down
.PHONY: up-simple down-simple logs-simple ps-simple restart-simple clean-orphans migrate-compose downgrade-compose app-shell db-shell redis-cli compose-lint logs-worker logs-flower health
.PHONY: local-smoke manage-logs seed-suppliers seed-all db-backup db-restore db-restore-force

# Local maintenance defaults (overridable via environment)
MAX_DIR_MB ?= 200
ARCHIVE_EXPIRY_DAYS ?= 30

# Default target
help:
	@echo "🚀 MagFlow ERP - Comenzi disponibile:"
	@echo "  make start        - Pornește serverul (recomandat)"
	@echo "  make install      - Instalează dependințele de dezvoltare"
	@echo "  make test         - Rulează toate testele"
	@echo "  make test-fast    - Rulează rapid un test/fișier fără xdist & coverage (set TEST=<target>)"
	@echo "  make test-unit    - Rulează testele unitare"
	@echo "  make test-cov     - Rulează testele cu raport de acoperire"
	@echo "  make lint         - Rulează linterele"
	@echo "  make format       - Formatează codul"
	@echo "  make check        - Rulează toate verificările"
	@echo "  make clean        - Curăță fișierele temporare"
	@echo "  make local-smoke  - Rulează verificări rapide pentru setup local"
	@echo "  make manage-logs  - Rulează scriptul de întreținere a logurilor"
	@echo ""
	@echo "📖 Pentru documentație completă: http://localhost:8080/docs"
	@echo ""
	@echo "🐳 Docker Compose:"
	@echo "  make up              - docker compose up (dev core)"
	@echo "  make up-simple       - docker compose up using docker-compose.simple.yml"
	@echo "  make up-proxy        - dev with proxy profile"
	@echo "  make up-monitoring   - dev with monitoring profile"
	@echo "  make up-ops          - dev with worker & flower (ops)"
	@echo "  make down            - docker compose down -v (DELETES ALL DATA!)"
	@echo "  make down-keep-data  - docker compose down (keeps volumes/data)"
	@echo "  make down-simple     - docker compose down -v (simple)"
	@echo "  make logs            - tail app logs"
	@echo "  make ps              - docker compose ps"
	@echo "  make restart         - docker compose restart app"
	@echo "  make deep-health     - fetch /health/full"
	@echo "  make logs-simple     - tail app logs (simple stack)"
	@echo "  make ps-simple       - show simple stack status"
	@echo "  make restart-simple  - restart app container (simple)"
	@echo "  make clean-orphans   - remove orphan containers for this project"
	@echo "  make migrate-compose - run alembic upgrade head inside the app container"
	@echo "  make downgrade-compose - run alembic downgrade -1 inside the app container"
	@echo "  make app-shell       - open a shell inside app container"
	@echo "  make db-shell        - psql shell into Postgres"
	@echo "  make redis-cli       - open redis-cli in Redis container"
	@echo "  make logs-worker     - tail Celery worker logs"
	@echo "  make logs-flower     - tail Flower logs"
	@echo "  make compose-lint    - validate docker compose configuration"
	@echo "  make health          - check app HTTP health"
	@echo "  make prod            - production compose (base)"
	@echo "  make prod-proxy      - production with proxy"
	@echo "  make prod-monitoring - production with monitoring"
	@echo "  make prod-otel       - production with OTEL & Jaeger"
	@echo "  make prod-certs      - production with Certbot"
	@echo "  make ci              - CI compose up"
	@echo "  make ci-down         - CI compose down -v"
	@echo ""
	@echo "🗄️  Database:"
	@echo "  make seed-suppliers     - Seed supplier products data"
	@echo "  make seed-all           - Seed all demo data (suppliers, orders, etc.)"
	@echo "  make db-backup          - Backup database to backups/ directory"
	@echo "  make db-restore         - Restore database from latest backup (with confirmation)"
	@echo "  make db-restore-force   - Force restore without confirmation"

# Start the server
start:
	@echo "🔧 Verificarea și instalarea dependințelor..."
	python3.13 -c "import dependency_injector, fastapi, uvicorn, redis.asyncio" 2>/dev/null || { \
		echo "📦 Instalarea dependințelor..."; \
		python3.13 -m pip install dependency-injector fastapi-limiter redis python-jose aiohttp httpx python-multipart --break-system-packages --user; \
	}
	@echo "✅ Toate dependințele sunt gata!"
	@echo "🚀 Pornirea serverului MagFlow ERP pe http://localhost:8080"
	uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# ---------------------------
# Docker Compose shortcuts
# ---------------------------
up:
	docker compose up

ps:
	docker compose ps

up-proxy:
	docker compose --profile proxy up

up-monitoring:
	docker compose --profile monitoring up

up-ops:
	docker compose --profile ops up

down:
	@echo "⚠️  WARNING: This will DELETE ALL DATA (volumes will be removed)!"
	@echo "⚠️  Use 'make down-keep-data' to keep your data."
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose down -v; \
	else \
		echo "Cancelled."; \
	fi

down-keep-data:
	@echo "🔄 Stopping containers (keeping data)..."
	docker compose down

restart:
	docker compose restart app

logs:
	docker compose logs -f app

deep-health:
	curl -s http://localhost:8000/health/full | jq . || curl -s http://localhost:8000/health/full

# Simple stack helpers (docker-compose.simple.yml)
up-simple:
	docker compose -f docker-compose.simple.yml up -d

down-simple:
	docker compose -f docker-compose.simple.yml down -v

logs-simple:
	docker compose -f docker-compose.simple.yml logs -f app

ps-simple:
	docker compose -f docker-compose.simple.yml ps

restart-simple:
	docker compose -f docker-compose.simple.yml restart app

clean-orphans:
	docker compose -f docker-compose.simple.yml down --remove-orphans || true

migrate-compose:
	docker compose exec app alembic upgrade head

downgrade-compose:
	docker compose exec app alembic downgrade -1

app-shell:
	docker compose exec app /bin/sh

db-shell:
	docker compose exec db psql -U $$DB_USER -d $$DB_NAME -h 127.0.0.1 -p 5432 || docker compose exec db psql -U app -d magflow -h 127.0.0.1 -p 5432

redis-cli:
	docker compose exec redis redis-cli -a $$REDIS_PASSWORD || docker compose exec redis redis-cli

logs-worker:
	docker compose logs -f worker

logs-flower:
	docker compose logs -f flower

compose-lint:
	docker compose config -q && echo "Compose config is valid"

health:
	curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8000/health

prod:
	docker compose -f docker-compose.production.yml up -d

prod-proxy:
	docker compose -f docker-compose.production.yml --profile proxy up -d

prod-monitoring:
	docker compose -f docker-compose.production.yml --profile monitoring up -d

prod-otel:
	docker compose -f docker-compose.production.yml --profile otel up -d

prod-certs:
	docker compose -f docker-compose.production.yml --profile certs up -d

ci:
	docker compose -f docker-compose.ci.yml up --build

ci-down:
	docker compose -f docker-compose.ci.yml down -v

# Install development dependencies
install:
	@echo "📦 Instalarea dependințelor de dezvoltare..."
	python3.13 -m pip install -r requirements-test.txt --break-system-packages --user
	pre-commit install
	@echo "✅ Dependențe instalate cu succes!"

# Testing
TEST_ARGS ?= -v --durations=10
TEST_PATH ?= tests/
TEST ?= tests/

# Run all tests
test:
	pytest $(TEST_ARGS) $(TEST_PATH)

# Run focused test without xdist/coverage
test-fast:
	pytest -n 0 --no-cov $(TEST)

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

# Celery-specific commands
celery-test:
	@echo "🧪 Running Celery task tests..."
	pytest tests/test_celery_tasks.py -v

celery-worker:
	@echo "🐝 Starting Celery worker..."
	celery -A app.worker.celery_app worker -Q default -c 2 --loglevel=INFO

celery-flower:
	@echo "🌸 Starting Flower dashboard..."
	celery -A app.worker.celery_app flower

celery-ready:
	@echo "🔍 Checking Celery readiness..."
	curl -s http://localhost:8000/api/v1/tasks/ready || echo "❌ Celery not ready"

# Security and dependency scanning
security-scan:
	@echo "🔒 Running security scan..."
	safety check
	bandit -r app/ -f json -o security-report.json

dependency-scan:
	@echo "📦 Checking for dependency vulnerabilities..."
	pip-audit

# CI workflow targets
ci-test:
	@echo "🧪 Running CI tests..."
	pytest tests/ --cov=app --cov-report=xml --cov-report=term-missing -q

ci-lint:
	@echo "🔍 Running CI linting..."
	ruff check .
	black --check .

ci-format:
	@echo "📝 Running CI formatting..."
	black .
	isort .

ci-type-check:
	@echo "📏 Running CI type checking..."
	mypy .

ci-all: ci-lint ci-format ci-type-check ci-test
	@echo "✅ All CI checks passed!"

# Performance testing
local-smoke:
	@echo "⚙️  Local smoke tests"
	@PYTHONPATH=. python3 tests/scripts/test_db_direct.py
	@PYTHONPATH=. python3 tests/scripts/test_app_db.py
	@pytest tests/unit -q

# Optimized performance testing
local-smoke-optimized:
	@echo "🚀 Simple and reliable performance tests with monitoring"
	@PYTHONPATH=. python3 tests/scripts/test_db_direct.py
	@PYTHONPATH=. python3 tests/scripts/test_app_db.py
	@python3 -m pytest tests/test_simple_performance.py -v --tb=short --disable-warnings --asyncio-mode=auto

# Run performance benchmarks
performance-benchmark:
	@echo "📊 Running comprehensive performance benchmarks"
	@python3 run_performance_tests.py --benchmark tests/test_optimized_products_api.py

# Run optimized tests with parallel execution
test-optimized:
	@echo "⚡ Running optimized tests with performance monitoring"
	@python3 run_performance_tests.py --parallel tests/unit

manage-logs:
	@echo "🗂️  Archiving și curățare loguri locale"
	MAX_DIR_MB=$(MAX_DIR_MB) ARCHIVE_EXPIRY_DAYS=$(ARCHIVE_EXPIRY_DAYS) ./scripts/manage_logs.sh

# Database operations
db-migrate:
	@echo "🗄️ Running database migrations..."
	alembic upgrade head
db-rollback:
	@echo "⏪ Rolling back last migration..."
	alembic downgrade -1

db-seed:
	@echo "🌱 Seeding database with test data..."
	python scripts/seed_test_data.py

# Monitoring and health checks
health-check:
	@echo "💚 Checking application health..."
	curl -s http://localhost:8000/health || echo "❌ Health check failed"

metrics:
	@echo "📊 Checking metrics endpoints..."
	curl -s http://localhost:8000/metrics || echo "❌ Metrics unavailable"

# Development helpers
dev-setup: install pre-commit-install
	@echo "🛠️ Development environment setup complete!"

dev-clean:
	@echo "🧹 Deep cleaning development environment..."
	make clean
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	docker system prune -f

# Production deployment helpers
deploy-check:
	@echo "🚀 Running pre-deployment checks..."
	make ci-all
	make health-check

deploy-rollback:
	@echo "⏪ Rolling back deployment..."
	@echo "⚠️  Manual rollback required - check deployment logs"

# Documentation
docs-serve:
	@echo "📚 Starting documentation server..."
	mkdocs serve

docs-build:
	@echo "📝 Building documentation..."
	mkdocs build

# Container operations
build:
	@echo "🏗️ Building application container..."
	docker build -t magflow-app .

build-prod:
	@echo "🏭 Building production container..."
	docker build -f Dockerfile.production -t magflow-app-prod .

# Kubernetes operations (if needed)
k8s-deploy:
	@echo "☸️ Deploying to Kubernetes..."
	kubectl apply -f deployment/kubernetes/

k8s-status:
	@echo "📊 Checking Kubernetes status..."
	kubectl get pods -o wide

# Database seeding and backup operations
seed-suppliers:
	@echo "🌱 Seeding supplier products data..."
	docker compose exec app python scripts/seed_supplier_products.py || \
	python3 scripts/seed_supplier_products.py

seed-all: seed-suppliers
	@echo "🌱 Seeding all demo data..."
	@echo "  ✅ Supplier products seeded"
	@echo "  ℹ️  Add more seed commands here as needed"

db-backup:
	@echo "💾 Creating database backup..."
	@mkdir -p backups
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	docker compose exec -T db pg_dump -U app -d magflow | gzip > backups/magflow_$$TIMESTAMP.sql.gz && \
	echo "✅ Backup created: backups/magflow_$$TIMESTAMP.sql.gz"

db-restore:
	@echo "📥 Restoring database from latest backup..."
	@LATEST=$$(ls -t backups/magflow_*.sql.gz 2>/dev/null | head -1); \
	if [ -z "$$LATEST" ]; then \
		echo "❌ No backup files found in backups/"; \
		exit 1; \
	fi; \
	echo "⚠️  This will DROP and recreate the database!"; \
	echo "Restoring from: $$LATEST"; \
	read -p "Continue? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "🗑️  Dropping database..."; \
		docker compose exec -T db psql -U app -d postgres -c "DROP DATABASE IF EXISTS magflow;" && \
		docker compose exec -T db psql -U app -d postgres -c "CREATE DATABASE magflow;" && \
		echo "📥 Restoring data..."; \
		gunzip -c $$LATEST | docker compose exec -T db psql -U app -d magflow > /dev/null 2>&1 && \
		echo "✅ Database restored successfully!"; \
	else \
		echo "Cancelled."; \
	fi

db-restore-force:
	@echo "📥 Force restoring database (no confirmation)..."
	@LATEST=$$(ls -t backups/magflow_*.sql.gz 2>/dev/null | head -1); \
	if [ -z "$$LATEST" ]; then \
		echo "❌ No backup files found in backups/"; \
		exit 1; \
	fi; \
	echo "Restoring from: $$LATEST"; \
	docker compose exec -T db psql -U app -d postgres -c "DROP DATABASE IF EXISTS magflow;" && \
	docker compose exec -T db psql -U app -d postgres -c "CREATE DATABASE magflow;" && \
	gunzip -c $$LATEST | docker compose exec -T db psql -U app -d magflow > /dev/null 2>&1 && \
	echo "✅ Database restored successfully!"
