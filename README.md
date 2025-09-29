# MagFlow ERP

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116.1-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**MagFlow ERP** is a modern, comprehensive Enterprise Resource Planning system built with FastAPI, SQLAlchemy, and PostgreSQL. It provides complete inventory management, sales, purchasing, and financial operations with real-time analytics and monitoring.

## 🧪 Testing

MagFlow uses `pytest` for testing with a comprehensive test suite including unit, integration, and API tests.

### Running Tests

```bash
# Install test dependencies
pip install -e ".[test]"

# Run all tests
./run_tests.py

# Run specific test types
./run_tests.py --unit           # Run only unit tests
./run_tests.py --integration    # Run only integration tests
./run_tests.py --api            # Run only API tests

# Run specific test file or directory
./run_tests.py tests/unit/emag  # Run all unit tests for eMAG
./run_tests.py tests/test_db.py # Run specific test file

# Run with coverage report (HTML and console)
./run_tests.py --cov

# Run with verbose output
./run_tests.py -v

# Run tests matching a specific marker
./run_tests.py -m "not slow"    # Run all tests except slow ones
```

### Test Structure

```
tests/
├── api/                # API test cases
├── config/             # Test configuration
├── database/           # Database tests
├── fixtures/           # Test fixtures
├── integration/        # Integration tests
│   └── emag/          # eMAG platform integration tests
├── load/               # Load testing
├── performance/        # Performance tests
├── reports/            # Test reports
├── scripts/            # Test utility scripts
├── security/           # Security tests
├── test_data/          # Test data files
└── unit/               # Unit tests
    └── emag/          # eMAG unit tests
```

### Writing Tests

- **Unit Tests**: Test individual functions and classes in isolation
- **Integration Tests**: Test interactions between components
- **API Tests**: Test API endpoints and responses

Example test file:

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to MagFlow ERP"}
```

### Test Coverage

To generate a coverage report:

```bash
./run_tests.py --cov
```

This will generate:

- Console report showing coverage percentage
- HTML report in `htmlcov/` directory
- XML report for CI integration

## 🚀 Features

### Core Modules

- **📦 Inventory Management**: Warehouses, stock tracking, reservations, transfers
- **💰 Sales Management**: Orders, invoices, payments, quotes, customers
- **🛒 Purchase Management**: Orders, receipts, suppliers, requisitions
- **👥 User Management**: Authentication, authorization, roles, permissions
- **📊 Analytics & Reporting**: Real-time metrics, dashboards, alerts
- **🔗 External Integrations**: eMAG marketplace integration
- **📱 RESTful API**: Complete API with automatic documentation
- **🔐 Security**: JWT authentication, RBAC, SSL/TLS, audit logging
- **📈 Monitoring**: Health checks, metrics, alerts, observability

### Technical Features

- **⚡ Async/Await**: Full async support for high performance
- **🗄️ Database**: PostgreSQL with async SQLAlchemy
- **🔄 Caching**: Redis for performance optimization
- **📋 Queue**: Background job processing
- **🐳 Containerized**: Docker and Docker Compose ready
- **☸️ Kubernetes**: K8s deployment configurations
- **📊 Metrics**: Prometheus and Grafana monitoring
- **🔍 Logging**: Structured logging with ELK stack ready
- **🧪 Testing**: Comprehensive test suite with 70+ tests
- **📝 Documentation**: Complete API docs and guides (see `docs/integrations/emag/README.md` for the eMAG integration index)

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Development](#development)
- [Deployment](#deployment)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 6+ (optional, for caching)
- Docker & Docker Compose (optional)

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/magflow-erp.git
cd magflow-erp
```

### 2. Environment Setup

```bash
# Copy environment file
cp .env.example .env

# Edit .env with your configuration
vim .env
```

### 3. Install Dependencies

```bash
# Using pip
pip install -r requirements.txt

# Or using conda
conda env create -f environment.yml
conda activate magflow-erp
```

### 4. Database Setup

```bash
# Initialize database
python -c "from app.db.base import engine; from app.models import *; print('Database ready')"

# Or using Docker
docker-compose up -d postgres
```

### 5. Start the Application

```bash
# Development server
uvicorn app.main:app --reload

# Production server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# With workers
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 6. Access the Application

- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Application**: http://localhost:8000

## 📦 Installation

### Option 1: Local Development

```bash
# 1. Clone repository
git clone <repository-url>
cd magflow-erp

# 2. Setup Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your settings

### Getting Started

1. Install dependencies: `pip install -r requirements.txt`
2. Run database migrations: `alembic upgrade head`
3. (Optional) Seed sample orders for local testing: `make seed-orders`
4. Start the development server: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# 1. Clone repository
git clone <repository-url>
cd magflow-erp

# 2. Start services (recommended shortcuts)
# Minimal core stack (app + db + redis):
make up-simple

# Full stack with background processing:
docker compose up -d app db redis worker beat

# Or start everything defined in docker-compose.yml:
docker compose up -d

# Verify container health (app, db, redis, worker, beat)
docker compose ps

# 3. Initialize database
docker-compose exec app python scripts/init_db.py

# 4. Access application
# Full stack API: http://localhost:8000
# Simple stack API: http://localhost:8001
# Database (full): via PgBouncer at localhost:6432
# Database (simple): direct Postgres localhost:5433 -> 5432 in container
# Redis (simple): localhost:6380 -> 6379 in container
```

### Option 3: Production Deployment

```bash
# 1. Clone repository
git clone <repository-url>
cd magflow-erp

# 2. Setup production environment
cp .env.example .env.production
# Edit production configuration

# 3. Build and deploy
docker-compose -f docker-compose.prod.yml up -d

# 4. Run database migrations
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head
```

## ⚙️ Configuration

### Environment Variables

```bash
# Database
POSTGRES_SERVER=localhost
POSTGRES_USER=magflow
POSTGRES_PASSWORD=your_password
POSTGRES_DB=magflow
SQLALCHEMY_DATABASE_URI=postgresql+asyncpg://magflow:password@localhost/magflow

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALGORITHM=HS256

# Application
APP_ENV=development
DEBUG=True
API_V1_STR=/api/v1

# External APIs
EMAG_API_URL=https://marketplace-api.emag.ro/api-3
EMAG_MAIN_USERNAME=your_username
EMAG_MAIN_PASSWORD=your_password
EMAG_FBE_USERNAME=your_fbe_username
EMAG_FBE_PASSWORD=your_fbe_password

# Redis (for caching)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Monitoring
SENTRY_DSN=your_sentry_dsn
LOG_LEVEL=INFO
```

### Configuration Files

- `config/mapping_default.json` - Field mapping configuration
- `config/examples/.env.emag.example` - EMAG integration example
- `app/core/config.py` - Application configuration
- `alembic.ini` - Database migration configuration

## 📖 Usage

### Basic API Usage

```python
import httpx

# Authentication
auth_response = httpx.post(
    "http://localhost:8000/api/v1/auth/access-token",
    data={"username": "admin", "password": "admin"}
)
token = auth_response.json()["access_token"]

# API calls with authentication
headers = {"Authorization": f"Bearer {token}"}
response = httpx.get("http://localhost:8000/api/v1/users/me", headers=headers)
```

### Inventory Management

```python
# Create warehouse
warehouse = httpx.post(
    "http://localhost:8000/api/v1/warehouses/",
    json={"name": "Main Warehouse", "location": "Bucharest"},
    headers=headers
)

# Add inventory item
item = httpx.post(
    "http://localhost:8000/api/v1/inventory/",
    json={
        "name": "Laptop",
        "sku": "LT001",
        "description": "Gaming Laptop",
        "category_id": 1,
        "unit_cost": 1000.00
    },
    headers=headers
)
```

### Sales Management

```python
# Create customer
customer = httpx.post(
    "http://localhost:8000/api/v1/customers/",
    json={
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+40700123456"
    },
    headers=headers
)

# Create sales order
order = httpx.post(
    "http://localhost:8000/api/v1/sales-orders/",
    json={
        "customer_id": customer.json()["id"],
        "order_date": "2024-01-15",
        "lines": [
            {
                "inventory_item_id": item.json()["id"],
                "quantity": 2,
                "unit_price": 1200.00
            }
        ]
    },
    headers=headers
)
```

## 📚 API Documentation

### Authentication

- **POST** `/api/v1/auth/access-token` - Login and get JWT token
- **POST** `/api/v1/auth/register` - Register new user
- **GET** `/api/v1/users/me` - Get current user info

### Inventory

- **GET** `/api/v1/inventory/` - List inventory items
- **POST** `/api/v1/inventory/` - Create inventory item
- **GET** `/api/v1/warehouses/` - List warehouses
- **POST** `/api/v1/warehouses/` - Create warehouse

### Sales

- **GET** `/api/v1/customers/` - List customers
- **POST** `/api/v1/customers/` - Create customer
- **GET** `/api/v1/sales-orders/` - List sales orders
- **POST** `/api/v1/sales-orders/` - Create sales order

### Purchasing

- **GET** `/api/v1/suppliers/` - List suppliers
- **POST** `/api/v1/suppliers/` - Create supplier
- **GET** `/api/v1/purchase-orders/` - List purchase orders
- **POST** `/api/v1/purchase-orders/` - Create purchase order

### Health & Monitoring

- **GET** `/health` - Health check endpoint
- **GET** `/health/detailed` - Detailed health information
- **GET** `/metrics` - Prometheus metrics

## 🛠️ Development

### Project Structure

```
magflow-erp/
├── app/                    # Main application
│   ├── api/               # API endpoints
│   ├── core/              # Core configuration
│   ├── crud/              # Database operations
│   ├── models/            # Database models
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # Business logic
│   └── main.py           # Application entry point
├── scripts/               # Utility scripts
├── tests/                 # Test suite
├── docs/                  # Documentation
├── deployment/            # Deployment configs
└── docker-compose.yml     # Development environment
```

### Development Commands

```bash
# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Format code
black app/

# Check types
mypy app/

# Run linter
ruff check app/

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Database Operations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Run migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Check migration status
alembic current
alembic history
```

## 🚀 Deployment

### Environment Setup

```bash
# Development
cp .env.example .env
# Edit .env with development settings

# Production
cp .env.example .env.production
# Edit .env.production with production settings
```

### Docker Deployment

```bash
# Build and run
docker-compose up -d

# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Scale application
docker-compose up -d --scale app=3
```

### Kubernetes Deployment

```bash
# Apply configurations
kubectl apply -f deployment/kubernetes/

# Check deployment status
kubectl get pods
kubectl get services
kubectl get ingress

# View logs
kubectl logs -f deployment/magflow-erp
```

## 📊 Monitoring

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health information
curl http://localhost:8000/health/detailed

# Database health
curl http://localhost:8000/health/database

# External services health
curl http://localhost:8000/health/external
```

### Metrics & Analytics

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
- **Application Metrics**: http://localhost:8000/metrics

### Logs

```bash
# Application logs
tail -f logs/app.log

# Docker logs
docker-compose logs -f app

# Kubernetes logs
kubectl logs -f deployment/magflow-erp
```

## 🔧 Troubleshooting

### Common Issues

#### Database Connection Issues

```bash
# Check database connectivity
python -c "from app.db.base import engine; print('Database connected')"

# Check PostgreSQL logs
docker-compose logs postgres

# Verify database URL in .env
echo $DATABASE_URL
```

#### Permission Issues

```bash
# Fix file permissions
chmod +x scripts/*.sh
chmod 600 certs/*.key
chmod 644 certs/*.pem
```

#### Import Errors

```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Verify dependencies
pip list | grep -E "(fastapi|sqlalchemy|uvicorn)"

# Check for circular imports
python -m py_compile app/main.py
```

### Debug Mode

```bash
# Start with debug logging
export LOG_LEVEL=DEBUG
python -m uvicorn app.main:app --reload --log-level debug

# Enable SQL query logging
export SQL_ECHO=1
```

### Performance Issues

```bash
# Check memory usage
ps aux | grep python

# Monitor database performance
python scripts/database_metrics.py

# Check Redis performance
redis-cli INFO
```

## 🤝 Contributing

### Development Workflow

1. Fork the repository
1. Create a feature branch: `git checkout -b feature/new-feature`
1. Make your changes and add tests
1. Run the test suite: `pytest tests/`
1. Format code: `black app/ && ruff check app/`
1. Commit your changes: `git commit -am 'Add new feature'`
1. Push to the branch: `git push origin feature/new-feature`
1. Submit a Pull Request

### Code Standards

- Follow PEP 8 style guidelines
- Use type hints for all functions
- Write comprehensive docstrings
- Add tests for new functionality
- Update documentation for API changes

### Testing Requirements

- Unit tests for all new functions
- Integration tests for API endpoints
- Minimum 80% code coverage
- Tests should be fast and isolated

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **FastAPI** - Modern, fast web framework for building APIs
- **SQLAlchemy** - The Python SQL toolkit and Object Relational Mapper
- **PostgreSQL** - Advanced open source relational database
- **Redis** - In-memory data structure store
- **Docker** - Containerization platform
- **Kubernetes** - Container orchestration system

## 📞 Support

For support and questions:

- 📧 Email: support@magflow-erp.com
- 📱 Issues: [GitHub Issues](https://github.com/your-org/magflow-erp/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/your-org/magflow-erp/discussions)

______________________________________________________________________

**MagFlow ERP** - Enterprise Resource Planning Made Simple 🚀
