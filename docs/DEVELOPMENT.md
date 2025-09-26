# MagFlow ERP - Development Guide

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116.1-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)

Comprehensive development setup and contribution guide for MagFlow ERP.

## 📋 Table of Contents

- [Development Environment Setup](#development-environment-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Database Development](#database-development)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [API Development](#api-development)
- [Debugging](#debugging)
- [Performance Optimization](#performance-optimization)
- [Troubleshooting](#troubleshooting)

## 🛠️ Development Environment Setup

### Prerequisites

#### System Requirements

- **Operating System**: Linux, macOS, or Windows (WSL recommended)
- **Python**: 3.11 or higher
- **PostgreSQL**: 15 or higher
- **Redis**: 6 or higher (optional, for caching)
- **Git**: Latest version
- **Docker & Docker Compose**: For containerized development

#### Hardware Requirements

- **RAM**: Minimum 4GB, recommended 8GB
- **Storage**: Minimum 10GB free space
- **Network**: Internet connection for package installation

### Option 1: Local Development Setup

#### 1. Clone the Repository

```bash
git clone https://github.com/your-org/magflow-erp.git
cd magflow-erp
```

#### 2. Setup Python Environment

**Using venv (Recommended):**

```bash
# Create virtual environment
python -m venv venv

# Activate environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

**Using conda:**

```bash
# Create conda environment
conda env create -f environment.yml

# Activate environment
conda activate magflow-erp
```

#### 3. Install Dependencies

```bash
# Install from requirements.txt
pip install -r requirements.txt

# Or install with all development dependencies
pip install -r requirements-dev.txt
```

#### 4. Environment Configuration

**Copy environment template:**

```bash
cp .env.example .env
```

**Edit `.env` with development settings:**

```bash
# Database Configuration
POSTGRES_SERVER=localhost
POSTGRES_USER=magflow_dev
POSTGRES_PASSWORD=dev_password
POSTGRES_DB=magflow_dev
SQLALCHEMY_DATABASE_URI=postgresql+asyncpg://magflow_dev:dev_password@localhost/magflow_dev

# Security (Development Only)
SECRET_KEY=development-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=60
ALGORITHM=HS256

# Application
APP_ENV=development
DEBUG=True
API_V1_STR=/api/v1

# Redis (Optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=json

# External APIs (Optional for development)
EMAG_API_URL=https://api.emag.test
EMAG_API_USERNAME=test@example.com
EMAG_API_PASSWORD=test-password
```

#### 5. Database Setup

**Install PostgreSQL:**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# macOS with Homebrew
brew install postgresql
brew services start postgresql

# Create database user and database
sudo -u postgres psql
```

**In PostgreSQL:**

```sql
CREATE USER magflow_dev WITH PASSWORD 'dev_password';
CREATE DATABASE magflow_dev OWNER magflow_dev;
GRANT ALL PRIVILEGES ON DATABASE magflow_dev TO magflow_dev;
\q
```

**Setup Database Schema:**

```bash
# Run database migrations
alembic upgrade head

# Or initialize database with sample data
python scripts/init_db.py
```

#### 6. Start Development Server

**Standard FastAPI server:**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**With additional options:**

```bash
# With debug logging
LOG_LEVEL=DEBUG uvicorn app.main:app --reload --log-level debug

# With workers
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --reload

# With HTTPS (for testing SSL)
uvicorn app.main:app --reload --ssl-keyfile=certs/server.key --ssl-certfile=certs/server.crt
```

#### 7. Verify Setup

**Access the application:**

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Database**: Check logs for successful connection

**Run a quick test:**

```bash
# Test database connection
python -c "from app.db.base import engine; print('Database connected successfully')"

# Test API
curl http://localhost:8000/health
```

### Option 2: Docker Development Setup

#### 1. Prerequisites

```bash
# Install Docker and Docker Compose
# On Ubuntu/Debian:
sudo apt update
sudo apt install docker.io docker-compose

# On macOS:
# Install Docker Desktop from https://docs.docker.com/desktop/mac/install/

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker
```

#### 2. Clone and Setup

```bash
git clone https://github.com/your-org/magflow-erp.git
cd magflow-erp

# Copy environment file
cp .env.example .env

# Edit .env for Docker development
# Set POSTGRES_SERVER=postgres (Docker service name)
```

#### 3. Start All Services

```bash
# Start the complete development stack
docker-compose up -d

# Check running containers
docker-compose ps

# View logs
docker-compose logs -f app
```

#### 4. Database Setup

```bash
# Wait for PostgreSQL to be ready
docker-compose exec postgres pg_isready -U magflow -d magflow

# Initialize database schema
docker-compose exec app alembic upgrade head

# Or use the initialization script
docker-compose exec app python scripts/init_db.py
```

#### 5. Access the Application

- **API**: http://localhost:8000
- **Database**: localhost:5432
- **Redis**: localhost:6379
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090

### Option 3: Production Development Setup

#### 1. Environment Configuration

```bash
# Copy production environment template
cp .env.example .env.production

# Edit with production settings
vim .env.production
```

#### 2. Production Database Setup

```bash
# Create production database
createdb magflow_prod

# Or use Docker
docker run --name postgres-prod -e POSTGRES_DB=magflow_prod \
  -e POSTGRES_USER=magflow -e POSTGRES_PASSWORD=prod_password \
  -p 5432:5432 -d postgres:15
```

#### 3. Production Deployment

```bash
# Build production image
docker build -t magflow-erp:prod .

# Run with production configuration
docker run -d --name magflow-prod \
  -p 8000:8000 \
  --env-file .env.production \
  magflow-erp:prod

# Or use docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

## 🏗️ Project Structure

### Core Application Structure

```
magflow-erp/
├── app/                          # Main application package
│   ├── api/                      # API endpoints and routes
│   │   ├── v1/                   # API version 1
│   │   │   ├── endpoints/        # Route handlers
│   │   │   └── deps.py          # Dependencies
│   ├── core/                     # Core configuration
│   │   ├── config.py            # Settings and configuration
│   │   ├── security.py          # Security utilities
│   │   └── database.py          # Database connection
│   ├── crud/                     # Database operations
│   │   ├── base.py              # Base CRUD class
│   │   ├── user.py              # User CRUD operations
│   │   └── inventory.py         # Inventory CRUD operations
│   ├── models/                   # SQLAlchemy models
│   │   ├── user.py              # User model
│   │   ├── inventory.py         # Inventory model
│   │   └── base.py              # Base model class
│   ├── schemas/                  # Pydantic schemas
│   │   ├── user.py              # User schemas
│   │   ├── inventory.py         # Inventory schemas
│   │   └── base.py              # Base schema class
│   ├── services/                 # Business logic
│   │   ├── user_service.py      # User business logic
│   │   ├── inventory_service.py # Inventory business logic
│   │   └── auth_service.py      # Authentication service
│   ├── main.py                  # Application entry point
│   └── __init__.py              # Package initialization
├── scripts/                      # Utility scripts
├── tests/                        # Test suite
├── docs/                         # Documentation
├── deployment/                   # Deployment configurations
├── monitoring/                   # Monitoring setup
├── logs/                         # Application logs
├── config/                       # Configuration files
├── bin/                          # Executables
└── docker-compose.yml           # Development environment
```

### Directory Responsibilities

#### `/app/` - Main Application

- **api/**: FastAPI route definitions and endpoint handlers
- **core/**: Core configuration, database setup, security
- **crud/**: Database operations (Create, Read, Update, Delete)
- **models/**: SQLAlchemy database models
- **schemas/**: Pydantic request/response schemas
- **services/**: Business logic and service layer
- **main.py**: FastAPI application instance and startup events

#### `/scripts/` - Utility Scripts

- **init_db.py**: Database initialization
- **setup-\*.sh**: Environment setup scripts
- **generate\_\*.py**: Code generation utilities
- **check\_\*.py**: Validation and health check scripts

#### `/tests/` - Test Suite

- **unit/**: Unit tests for individual components
- **integration/**: Integration tests for API endpoints
- **conftest.py**: Pytest fixtures and configuration
- **test\_\*.py**: Test files organized by functionality

#### `/docs/` - Documentation

- **API.md**: Comprehensive API documentation
- **README.md**: Project overview and setup guide
- **deployment/**: Deployment guides
- **architecture/**: Architecture documentation

#### `/deployment/` - Deployment Configurations

- **docker/**: Docker configurations
- **kubernetes/**: Kubernetes manifests
- **docker-compose*.yml*\*: Docker Compose files

#### `/monitoring/` - Monitoring Setup

- **grafana/**: Grafana dashboards
- **prometheus/**: Prometheus configuration
- **alerts.py**: Alert definitions
- **database_metrics.py**: Database monitoring

## 🔄 Development Workflow

### 1. Feature Development Process

#### Create a Feature Branch

```bash
# Create and checkout new branch
git checkout -b feature/new-feature-name

# Or for bug fixes
git checkout -b bugfix/issue-description

# Or for hotfixes
git checkout -b hotfix/critical-issue
```

#### Make Changes

```bash
# 1. Create/update models if needed
# app/models/new_model.py

# 2. Create/update schemas
# app/schemas/new_schema.py

# 3. Create CRUD operations
# app/crud/new_crud.py

# 4. Create service layer
# app/services/new_service.py

# 5. Create API endpoints
# app/api/v1/endpoints/new_endpoints.py

# 6. Add to main router
# app/api/v1/api.py
```

#### Test Your Changes

```bash
# Run specific tests
pytest tests/ -k "new_feature"

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run integration tests
pytest tests/integration/ -v
```

#### Format and Lint Code

```bash
# Format code
black app/

# Check types
mypy app/

# Run linter
ruff check app/

# Fix auto-fixable issues
ruff check app/ --fix

# Format all Python files
black . && ruff check . --fix
```

#### Commit Your Changes

```bash
# Stage changes
git add .

# Write descriptive commit message
git commit -m "feat: add new feature

- Add new model for feature
- Create API endpoints
- Add comprehensive tests
- Update documentation

Resolves #123"

# Push to remote
git push origin feature/new-feature-name
```

### 2. Code Review Process

#### Before Submitting PR

- [ ] All tests pass
- [ ] Code formatted with black
- [ ] Type checking passes with mypy
- [ ] Linting passes with ruff
- [ ] Minimum 80% test coverage
- [ ] Documentation updated
- [ ] Commit messages follow conventional commits

#### PR Template

```markdown
## Description
Brief description of changes

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
- Test case 1
- Test case 2
- Test case 3

## Related Issues
- Closes #123
- Related to #456

## Screenshots
[If applicable, add screenshots]

## Checklist
- [ ] Tests pass
- [ ] Code formatted
- [ ] Documentation updated
- [ ] Reviewed by at least one team member
```

### 3. Database Development Workflow

#### Creating Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "add_new_table"

# Create empty migration
alembic revision -m "add_new_table"

# Edit the migration file
vim alembic/versions/xxx_add_new_table.py
```

#### Migration File Structure

```python
"""Add new table

Revision ID: xxx
Revises: yyy
Create Date: 2024-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = 'xxx'
down_revision = 'yyy'
branch_labels = None
depends_on = None

def upgrade():
    # Migration up code
    op.create_table('new_table',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(50), nullable=False)
    )

def downgrade():
    # Migration down code
    op.drop_table('new_table')
```

#### Running Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade specific revision
alembic upgrade xxx

# Downgrade one revision
alembic downgrade -1

# Downgrade specific revision
alembic downgrade yyy

# Check current revision
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic heads
```

## 🧪 Testing

### Test Organization

```
tests/
├── conftest.py              # Global fixtures and configuration
├── unit/                     # Unit tests
│   ├── test_models.py       # Model tests
│   ├── test_services.py     # Service tests
│   └── test_crud.py         # CRUD tests
├── integration/             # Integration tests
│   ├── test_api.py          # API endpoint tests
│   ├── test_auth.py         # Authentication tests
│   └── test_database.py     # Database integration tests
└── test_examples.py         # Example tests and documentation
```

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_models.py

# Run specific test function
pytest tests/unit/test_models.py::test_user_creation -v

# Run tests matching pattern
pytest -k "test_user" -v

# Run tests excluding slow ones
pytest -m "not slow"

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term-missing

# Run with parallel execution
pytest -n auto

# Run specific test categories
pytest tests/unit/ -v                    # Unit tests
pytest tests/integration/ -v            # Integration tests
pytest tests/ --maxfail=5               # Stop after 5 failures
```

### Writing Tests

#### Unit Test Example

```python
# tests/unit/test_user_service.py
import pytest
from app.services.user_service import UserService
from app.models.user import User

class TestUserService:
    async def test_create_user(self, db_session):
        """Test user creation functionality."""
        user_service = UserService(db_session)

        # Test data
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "securepassword"
        }

        # Execute
        user = await user_service.create_user(user_data)

        # Assert
        assert user.email == user_data["email"]
        assert user.username == user_data["username"]
        assert user.is_active is True

    async def test_get_user_by_email(self, db_session, test_user):
        """Test getting user by email."""
        user_service = UserService(db_session)

        # Execute
        user = await user_service.get_user_by_email(test_user.email)

        # Assert
        assert user is not None
        assert user.id == test_user.id
```

#### Integration Test Example

```python
# tests/integration/test_api_auth.py
import pytest
from httpx import AsyncClient

class TestAuthAPI:
    async def test_login_success(self, client: AsyncClient):
        """Test successful login."""
        response = await client.post(
            "/api/v1/auth/access-token",
            data={
                "username": "testuser",
                "password": "testpassword"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Test login with invalid credentials."""
        response = await client.post(
            "/api/v1/auth/access-token",
            data={
                "username": "wronguser",
                "password": "wrongpassword"
            }
        )

        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]
```

### Test Configuration

#### Pytest Configuration

```python
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -ra
    -q
    --strict-markers
    --strict-config
    --cov=app
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

#### Conftest.py (Global Fixtures)

```python
# tests/conftest.py
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.base import Base
from app.core.config import settings

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(settings.TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(db_engine):
    """Create test database session."""
    async_session = sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

@pytest_asyncio.fixture
async def client():
    """Create test HTTP client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user."""
    from app.crud.user import user_crud
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword"
    }
    user = await user_crud.create_user(db_session, user_data)
    yield user
```

## 🛠️ Code Quality

### Formatting and Linting

#### Black (Code Formatter)

```bash
# Format all Python files
black .

# Check formatting
black --check .

# Format specific directory
black app/
```

#### Ruff (Linter)

```bash
# Check all files
ruff check .

# Check specific directory
ruff check app/

# Fix auto-fixable issues
ruff check . --fix

# Check specific rules
ruff check . --select E,W,F

# Check and ignore specific errors
ruff check . --ignore E501
```

#### MyPy (Type Checking)

```bash
# Type check all files
mypy app/

# Type check with specific settings
mypy app/ --ignore-missing-imports

# Check with strict mode
mypy app/ --strict
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

### Code Quality Tools Setup

```bash
# Install pre-commit
pip install pre-commit

# Install pre-commit hooks
pre-commit install

# Run all pre-commit hooks
pre-commit run --all-files

# Run on specific files
pre-commit run --files app/main.py
```

## 🔧 API Development

### Creating New Endpoints

#### 1. Define Pydantic Schemas

```python
# app/schemas/item.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float

class ItemCreate(ItemBase):
    pass

class ItemUpdate(ItemBase):
    name: Optional[str] = None
    price: Optional[float] = None

class Item(ItemBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

#### 2. Create Database Model

```python
# app/models/item.py
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

from app.db.base import Base

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    price = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

#### 3. Create CRUD Operations

```python
# app/crud/item.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.crud.base import CRUDBase
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemUpdate

class CRUDItem(CRUDBase[Item, ItemCreate, ItemUpdate]):
    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[Item]:
        result = await db.execute(select(Item).where(Item.name == name))
        return result.scalar_one_or_none()

    async def get_multi_by_price_range(
        self, db: AsyncSession, min_price: float, max_price: float
    ) -> List[Item]:
        result = await db.execute(
            select(Item).where(Item.price.between(min_price, max_price))
        )
        return result.scalars().all()

crud_item = CRUDItem(Item)
```

#### 4. Create API Endpoints

```python
# app/api/v1/endpoints/items.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, models
from app.api import deps
from app.schemas.item import Item, ItemCreate, ItemUpdate

router = APIRouter()

@router.get("/", response_model=List[Item])
async def get_items(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
):
    """Get all items with pagination."""
    items = await crud.item.get_multi(db, skip=skip, limit=limit)
    return items

@router.post("/", response_model=Item)
async def create_item(
    item_in: ItemCreate,
    db: AsyncSession = Depends(deps.get_db),
):
    """Create a new item."""
    item = await crud.item.create(db, obj_in=item_in)
    return item

@router.get("/{item_id}", response_model=Item)
async def get_item(
    item_id: int,
    db: AsyncSession = Depends(deps.get_db),
):
    """Get item by ID."""
    item = await crud.item.get(db, id=item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.put("/{item_id}", response_model=Item)
async def update_item(
    item_id: int,
    item_in: ItemUpdate,
    db: AsyncSession = Depends(deps.get_db),
):
    """Update item."""
    item = await crud.item.get(db, id=item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item = await crud.item.update(db, db_obj=item, obj_in=item_in)
    return item

@router.delete("/{item_id}")
async def delete_item(
    item_id: int,
    db: AsyncSession = Depends(deps.get_db),
):
    """Delete item."""
    item = await crud.item.get(db, id=item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await crud.item.remove(db, id=item_id)
    return {"message": "Item deleted"}
```

#### 5. Add to Main API Router

```python
# app/api/v1/api.py
from fastapi import APIRouter
from app.api.v1.endpoints import items, users, auth

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(items.router, prefix="/items", tags=["items"])
```

#### 6. Create Tests

```python
# tests/unit/test_item_crud.py
import pytest
from app.crud.item import crud_item
from app.models.item import Item
from app.schemas.item import ItemCreate

class TestCRUDItem:
    async def test_create_item(self, db_session):
        item_data = ItemCreate(
            name="Test Item",
            description="Test Description",
            price=10.99
        )
        item = await crud_item.create(db_session, obj_in=item_data)
        assert item.name == "Test Item"
        assert item.price == 10.99

# tests/integration/test_api_items.py
class TestItemsAPI:
    async def test_get_items(self, client: AsyncClient):
        response = await client.get("/api/v1/items/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
```

### API Best Practices

#### Error Handling

```python
from fastapi import HTTPException
from pydantic import ValidationError

@router.post("/items/")
async def create_item(item: ItemCreate):
    try:
        # Your logic here
        pass
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
```

#### Response Models

```python
# Use Pydantic models for responses
@router.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    return item

# Use List for multiple items
@router.get("/items/", response_model=List[Item])
async def get_items():
    return items
```

#### Query Parameters

```python
@router.get("/items/")
async def get_items(
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Items to return"),
    search: str = Query(None, description="Search query"),
    sort_by: str = Query("name", description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order")
):
    # Implementation
    pass
```

#### Path Parameters

```python
@router.get("/items/{item_id}")
async def get_item(item_id: int = Path(..., gt=0, description="Item ID")):
    # Implementation
    pass

@router.get("/users/{user_id}/items/{item_id}")
async def get_user_item(
    user_id: int = Path(..., description="User ID"),
    item_id: int = Path(..., description="Item ID")
):
    # Implementation
    pass
```

## 🔍 Debugging

### Debug Mode Setup

```bash
# Start with debug logging
export LOG_LEVEL=DEBUG
export SQL_ECHO=1

# Run with debug options
uvicorn app.main:app --reload --log-level debug
```

### Common Debug Commands

```bash
# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Test database connection
python -c "from app.db.base import engine; print('Database connected')"

# Test Redis connection
python -c "import redis; r = redis.Redis(); r.ping(); print('Redis connected')"

# Check for circular imports
python -m py_compile app/main.py

# Verify dependencies
pip list | grep -E "(fastapi|sqlalchemy|uvicorn|alembic)"
```

### Database Debugging

```python
# Enable SQL query logging
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Test database operations
from app.db.base import get_db
from app.crud.user import user_crud

async def debug_db():
    async for session in get_db():
        users = await user_crud.get_multi(session)
        print(f"Found {len(users)} users")
        break
```

### API Debugging

```bash
# Test API endpoints
curl -v http://localhost:8000/health

# Test with authentication
curl -X POST http://localhost:8000/api/v1/auth/access-token \
  -d "username=admin&password=admin"

# Check API documentation
open http://localhost:8000/docs

# Test with HTTPie
http POST localhost:8000/api/v1/auth/access-token \
  username=admin password=admin
```

## 🚀 Performance Optimization

### Database Performance

```python
# Use connection pooling
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True
)

# Use indexes for queries
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, index=True)
    username = Column(String, index=True)

# Use query optimization
async def get_active_users(db: AsyncSession):
    # Good: Uses index
    result = await db.execute(
        select(User).where(User.is_active == True)
    )
    return result.scalars().all()
```

### Caching Strategy

```python
# app/services/cache_service.py
from typing import Optional
import redis.asyncio as redis
from app.core.config import settings

class CacheService:
    def __init__(self):
        self.redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )

    async def get_cached_data(self, key: str) -> Optional[str]:
        return await self.redis.get(key)

    async def set_cached_data(self, key: str, value: str, expire: int = 3600):
        await self.redis.setex(key, expire, value)

# Usage in service
cache_service = CacheService()

async def get_user_with_cache(user_id: int):
    cache_key = f"user:{user_id}"
    cached_user = await cache_service.get_cached_data(cache_key)

    if cached_user:
        return json.loads(cached_user)

    # Fetch from database
    user = await user_crud.get(db, id=user_id)

    # Cache for 1 hour
    await cache_service.set_cached_data(
        cache_key, json.dumps(user), 3600
    )

    return user
```

### Async Optimization

```python
# Good async patterns
async def get_multiple_users(user_ids: List[int]):
    # Use asyncio.gather for concurrent requests
    tasks = [get_user(user_id) for user_id in user_ids]
    users = await asyncio.gather(*tasks, return_exceptions=True)
    return [user for user in users if not isinstance(user, Exception)]

# Bad: sequential processing
async def get_multiple_users_bad(user_ids: List[int]):
    users = []
    for user_id in user_ids:
        user = await get_user(user_id)
        users.append(user)
    return users
```

## 🔧 Troubleshooting

### Common Development Issues

#### Import Errors

```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Verify app structure
find app/ -name "*.py" | head -10

# Check for circular imports
python -c "import app.main"

# Fix __init__.py files
find app/ -name "__init__.py" | xargs ls -la
```

#### Database Issues

```bash
# Check database connection
python -c "from app.db.base import engine; print('Connected')"

# Check PostgreSQL service
sudo systemctl status postgresql

# Check database URL
echo $DATABASE_URL

# Verify database exists
psql -l | grep magflow
```

#### Permission Issues

```bash
# Fix file permissions
find app/ -name "*.py" | xargs chmod 644
find scripts/ -name "*.sh" | xargs chmod +x
chmod 600 certs/*.key

# Fix directory permissions
chmod 755 app/
chmod 755 scripts/
```

#### Testing Issues

```bash
# Run specific failing test
pytest tests/unit/test_user.py::TestUser::test_create_user -v -s

# Debug test with pdb
pytest tests/unit/test_user.py::TestUser::test_create_user -v -s --pdb

# Check test coverage
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### Performance Issues

#### Memory Leaks

```python
# Check memory usage
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"

# Monitor memory over time
watch -n 1 'python -c "import psutil,os; p=psutil.Process(os.getpid()); print(f\"Memory: {p.memory_info().rss/1024/1024:.1f}MB CPU: {p.cpu_percent()}%\")"'
```

#### Slow Queries

```python
# Enable SQL query logging
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Use database query analyzer
python scripts/analyze_queries.py

# Check slow queries in PostgreSQL
psql -c "SELECT query, calls, total_time, mean_time FROM pg_stat_statements WHERE mean_time > 100 ORDER BY mean_time DESC LIMIT 10;"
```

#### High CPU Usage

```bash
# Check CPU usage
top -p $(pgrep -f "uvicorn\|python")

# Profile application
python -m cProfile -s time app/main.py

# Use line profiler
pip install line_profiler
kernprof -l app/services/user_service.py
python -m line_profiler app/services/user_service.py.lprof
```

### Development Tools

#### Environment Debugging

```bash
# Check all environment variables
env | grep -E "(DATABASE|REDIS|SECRET|DEBUG|LOG)" | sort

# Verify .env file is loaded
python -c "from app.core.config import settings; print('Settings loaded')"

# Check current working directory
pwd && ls -la
```

#### Dependency Issues

```bash
# Check for dependency conflicts
pip check

# List installed packages
pip list

# Check for outdated packages
pip list --outdated

# Verify specific package
pip show fastapi
pip show sqlalchemy
```

#### Git Issues

```bash
# Check git status
git status

# Check for uncommitted changes
git diff

# Check recent commits
git log --oneline -10

# Check for untracked files
git ls-files --others --exclude-standard
```

______________________________________________________________________

**MagFlow ERP Development Guide** - Complete Development Setup and Workflow 🛠️
