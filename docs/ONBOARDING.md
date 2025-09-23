# MagFlow ERP - Developer Onboarding Guide

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116.1-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)

Comprehensive developer onboarding guide for new team members joining MagFlow ERP project.

## 📋 Table of Contents

- [Welcome](#welcome)
- [Project Overview](#project-overview)
- [Development Environment Setup](#development-environment-setup)
- [Understanding the Architecture](#understanding-the-architecture)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing Strategy](#testing-strategy)
- [Contributing Guidelines](#contributing-guidelines)
- [Common Tasks](#common-tasks)
- [Resources & Documentation](#resources--documentation)

## 🎉 Welcome

### Welcome to MagFlow ERP!

Congratulations on joining the MagFlow ERP development team! This guide will help you get up to speed quickly and start contributing effectively to the project.

### What You'll Learn

By the end of this onboarding guide, you'll be able to:
- ✅ Set up your development environment
- ✅ Understand the project architecture
- ✅ Follow our development workflow
- ✅ Write code that follows our standards
- ✅ Run tests and debug issues
- ✅ Contribute new features and fix bugs

### Timeline

**Week 1: Environment & Basics**
- Set up development environment
- Understand project structure
- Run existing tests
- Make your first simple contribution

**Week 2: Core Features**
- Understand main modules (inventory, sales, purchasing)
- Learn API patterns
- Implement a small feature
- Write comprehensive tests

**Week 3: Advanced Features**
- Database migrations
- External integrations
- Performance optimization
- Security considerations

## 🏗️ Project Overview

### What is MagFlow ERP?

**MagFlow ERP** is a modern, comprehensive Enterprise Resource Planning system built with cutting-edge technologies:

- **Backend**: FastAPI (Python async web framework)
- **Database**: PostgreSQL with async SQLAlchemy
- **Cache**: Redis for performance optimization
- **API**: RESTful API with automatic OpenAPI documentation
- **Authentication**: JWT tokens with role-based access control
- **Monitoring**: Prometheus, Grafana, and comprehensive health checks

### Key Features

#### Core Modules
- **📦 Inventory Management**: Products, warehouses, stock tracking
- **💰 Sales Management**: Orders, invoices, customers, payments
- **🛒 Purchase Management**: Orders, suppliers, receipts
- **👥 User Management**: Authentication, roles, permissions
- **📊 Analytics**: Real-time metrics and dashboards
- **🔗 External Integrations**: eMAG marketplace integration

#### Technical Features
- **⚡ Async/Await**: Full async support for high performance
- **🐳 Containerized**: Docker and Kubernetes ready
- **📊 Monitoring**: Complete observability stack
- **🔐 Security**: Production-ready security features
- **🧪 Testing**: Comprehensive test suite (70+ tests)
- **📝 Documentation**: Complete API and developer docs

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
├── monitoring/            # Monitoring setup
└── docker-compose.yml     # Development environment
```

## 🛠️ Development Environment Setup

### Prerequisites

#### System Requirements
- **Operating System**: Linux, macOS, or Windows (WSL recommended)
- **Python**: 3.11 or higher
- **PostgreSQL**: 15 or higher
- **Redis**: 6 or higher
- **Git**: Latest version
- **Docker**: Latest version

#### Hardware Requirements
- **RAM**: Minimum 4GB, recommended 8GB
- **Storage**: Minimum 10GB free space
- **Internet**: Required for package installation

### Quick Setup (5 minutes)

#### 1. Clone Repository
```bash
git clone https://github.com/your-org/magflow-erp.git
cd magflow-erp
```

#### 2. Setup Environment
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

#### 3. Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
vim .env
```

#### 4. Start Development Environment
```bash
# Start all services with Docker
docker-compose up -d

# Or run locally
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 5. Verify Setup
```bash
# Check health
curl http://localhost:8000/health

# Access API docs
open http://localhost:8000/docs

# Run tests
pytest tests/
```

### Detailed Setup

#### Option 1: Local Development
```bash
# 1. Install Python 3.11
# Ubuntu/Debian:
sudo apt update && sudo apt install python3.11 python3.11-venv

# macOS:
brew install python@3.11

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Setup PostgreSQL
sudo apt install postgresql postgresql-contrib  # Ubuntu
createdb magflow_dev
psql -c "CREATE USER magflow_dev WITH PASSWORD 'dev_password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE magflow_dev TO magflow_dev;"

# 5. Setup Redis
sudo apt install redis-server  # Ubuntu
redis-server --daemonize yes

# 6. Configure environment
cp .env.example .env
# Edit .env with database credentials

# 7. Run migrations
alembic upgrade head

# 8. Start application
uvicorn app.main:app --reload
```

#### Option 2: Docker Development
```bash
# 1. Install Docker
# Follow Docker installation guide for your OS

# 2. Clone and setup
git clone https://github.com/your-org/magflow-erp.git
cd magflow-erp

# 3. Start services
docker-compose up -d

# 4. Wait for services to be ready
docker-compose exec app python -c "from app.db.base import engine; print('Database connected')"

# 5. Access application
# API: http://localhost:8000
# Database: localhost:5432
# Redis: localhost:6379
```

#### Option 3: Production Setup
```bash
# 1. Setup production environment
cp .env.example .env.production
# Edit production configuration

# 2. Build production image
docker build -t magflow-erp:production .

# 3. Run production environment
docker-compose -f docker-compose.prod.yml up -d

# 4. Run database migrations
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head
```

## 🏗️ Understanding the Architecture

### Application Architecture

#### Layered Architecture
```
┌─────────────────┐
│   API Layer     │  ← FastAPI routes and endpoints
├─────────────────┤
│  Service Layer  │  ← Business logic and orchestration
├─────────────────┤
│   CRUD Layer    │  ← Database operations
├─────────────────┤
│   Model Layer   │  ← SQLAlchemy models
├─────────────────┤
│  Database Layer │  ← PostgreSQL database
└─────────────────┘
```

#### Key Components

**API Layer (`app/api/`)**
- FastAPI route definitions
- Request/response handling
- Authentication and authorization
- Input validation and serialization

**Service Layer (`app/services/`)**
- Business logic implementation
- Orchestration of operations
- External API integrations
- Complex calculations

**CRUD Layer (`app/crud/`)**
- Database operations (Create, Read, Update, Delete)
- Query optimization
- Data validation
- Error handling

**Model Layer (`app/models/`)**
- SQLAlchemy model definitions
- Database relationships
- Constraints and indexes
- Data validation

### Code Organization

#### API Structure
```python
# app/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app import crud, models, schemas
from app.api import deps

router = APIRouter()

@router.get("/", response_model=List[schemas.User])
async def get_users(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
):
    """Get all users with pagination."""
    users = await crud.user.get_multi(db, skip=skip, limit=limit)
    return users

@router.post("/", response_model=schemas.User)
async def create_user(
    user_in: schemas.UserCreate,
    db: AsyncSession = Depends(deps.get_db),
):
    """Create a new user."""
    # Check if user exists
    user = await crud.user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists"
        )

    user = await crud.user.create(db, obj_in=user_in)
    return user
```

#### Service Layer
```python
# app/services/user_service.py
from typing import List, Optional
from app.crud.user import user_crud
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

class UserService:
    def __init__(self, db_session):
        self.db_session = db_session

    async def create_user(self, user_data: UserCreate) -> User:
        """Create new user with validation."""
        # Business logic for user creation
        # Email validation, password hashing, etc.
        user = await user_crud.create(self.db_session, obj_in=user_data)
        return user

    async def get_user_with_permissions(self, user_id: int) -> Optional[User]:
        """Get user with their permissions loaded."""
        user = await user_crud.get(self.db_session, id=user_id)
        if user:
            await self.db_session.refresh(user, ["roles"])
        return user

    async def update_user_role(self, user_id: int, role_id: int) -> User:
        """Update user role with validation."""
        # Business logic for role assignment
        user = await user_crud.get(self.db_session, id=user_id)
        if not user:
            raise ValueError("User not found")

        # Validate role assignment permissions
        # Update user role
        user = await user_crud.update_role(self.db_session, user, role_id)
        return user
```

#### CRUD Layer
```python
# app/crud/base.py
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.sql import Select

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: int) -> Optional[ModelType]:
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        result = await db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = obj_in.dict()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType
    ) -> ModelType:
        obj_data = db_obj.__dict__
        update_data = obj_in.dict(exclude_unset=True)

        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, *, id: int) -> Optional[ModelType]:
        result = await db.execute(
            select(self.model).where(self.model.id == id)
        )
        obj = result.scalar_one_or_none()

        if obj:
            await db.delete(obj)
            await db.commit()

        return obj
```

### Database Models

#### User Model
```python
# app/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String)
    phone = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    orders = relationship("SalesOrder", back_populates="customer")
    created_orders = relationship("SalesOrder", back_populates="created_by_user")
    roles = relationship("UserRole", back_populates="user")
```

#### Inventory Model
```python
# app/models/inventory.py
from sqlalchemy import Column, Integer, String, Text, DECIMAL, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    sku = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text)
    category_id = Column(Integer, ForeignKey("categories.id"))
    unit_cost = Column(DECIMAL(10, 2), nullable=False)
    stock_quantity = Column(Integer, default=0)
    min_stock_level = Column(Integer, default=0)
    max_stock_level = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    category = relationship("Category", back_populates="items")
    order_items = relationship("SalesOrderItem", back_populates="item")
    stock_movements = relationship("StockMovement", back_populates="item")
```

### API Patterns

#### Standard CRUD Operations
```python
# Standard pattern for all entities
@router.get("/{id}", response_model=Schema)
async def get_item(id: int, db: AsyncSession = Depends(deps.get_db)):
    item = await crud.item.get(db, id=id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.post("/", response_model=Schema)
async def create_item(item_in: CreateSchema, db: AsyncSession = Depends(deps.get_db)):
    # Validation logic
    item = await crud.item.create(db, obj_in=item_in)
    return item

@router.put("/{id}", response_model=Schema)
async def update_item(
    id: int,
    item_in: UpdateSchema,
    db: AsyncSession = Depends(deps.get_db)
):
    item = await crud.item.get(db, id=id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item = await crud.item.update(db, db_obj=item, obj_in=item_in)
    return item

@router.delete("/{id}")
async def delete_item(id: int, db: AsyncSession = Depends(deps.get_db)):
    item = await crud.item.get(db, id=id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await crud.item.remove(db, id=id)
    return {"message": "Item deleted"}
```

#### Error Handling
```python
# Consistent error handling
from fastapi import HTTPException
from pydantic import ValidationError

@router.post("/")
async def create_item(item: CreateSchema):
    try:
        # Business logic
        item = await crud.item.create(db, obj_in=item)
        return item
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating item: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

## 🔄 Development Workflow

### 1. Feature Development Process

#### Create Feature Branch
```bash
# Create and checkout new branch
git checkout -b feature/new-feature-name

# Or for bug fixes
git checkout -b bugfix/issue-description

# Or for hotfixes
git checkout -b hotfix/critical-issue
```

#### Implement Feature
```bash
# 1. Create models if needed
touch app/models/new_model.py

# 2. Create schemas
touch app/schemas/new_schema.py

# 3. Create CRUD operations
touch app/crud/new_crud.py

# 4. Create service layer
touch app/services/new_service.py

# 5. Create API endpoints
touch app/api/v1/endpoints/new_endpoints.py

# 6. Add to main router
vim app/api/v1/api.py
```

#### Test Implementation
```bash
# Run specific tests
pytest tests/ -k "new_feature"

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run integration tests
pytest tests/integration/ -v
```

#### Code Quality
```bash
# Format code
black app/

# Check types
mypy app/

# Run linter
ruff check app/

# Format all files
black . && ruff check . --fix
```

#### Commit Changes
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

### 3. Database Development

#### Creating Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "add_user_preferences"

# Create empty migration
alembic revision -m "add_user_preferences"

# Edit migration file
vim alembic/versions/xxxx_add_user_preferences.py
```

#### Running Migrations
```bash
# Upgrade to latest
alembic upgrade head

# Check current revision
alembic current

# Show migration history
alembic history
```

## 🧪 Testing Strategy

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
└── test_examples.py         # Example tests
```

### Writing Tests

#### Unit Test Example
```python
# tests/unit/test_user_service.py
import pytest
from app.services.user_service import UserService

class TestUserService:
    async def test_create_user(self, db_session):
        """Test user creation functionality."""
        user_service = UserService(db_session)

        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "securepassword"
        }

        user = await user_service.create_user(user_data)

        assert user.email == user_data["email"]
        assert user.username == user_data["username"]
        assert user.is_active is True
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
```

## 📏 Code Standards

### Python Standards

#### PEP 8 Compliance
```python
# Good
def calculate_total_price(quantity: int, unit_price: float) -> float:
    """Calculate total price for given quantity."""
    return quantity * unit_price

# Bad
def calc_tot_price(qty, price):
    return qty * price
```

#### Type Hints
```python
# Always use type hints
from typing import List, Optional, Dict, Any

async def get_users(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100
) -> List[User]:
    """Get users with pagination."""
    pass

def process_order(
    order_id: int,
    user: Optional[User] = None
) -> Dict[str, Any]:
    """Process order with optional user context."""
    pass
```

### FastAPI Standards

#### Route Organization
```python
# Group related routes
@router.get("/users/", response_model=List[User])
async def get_users():
    pass

@router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int):
    pass

@router.post("/users/", response_model=User)
async def create_user(user: UserCreate):
    pass
```

#### Error Handling
```python
# Consistent error responses
@router.post("/users/")
async def create_user(user: UserCreate):
    try:
        # Business logic
        return await crud.user.create(db, obj_in=user)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

## 🤝 Contributing Guidelines

### Development Workflow

#### 1. Fork and Clone
```bash
git clone https://github.com/your-username/magflow-erp.git
cd magflow-erp
git checkout -b feature/your-feature-name
```

#### 2. Make Changes
```bash
# Follow the patterns established in the codebase
# Add tests for new functionality
# Update documentation
# Follow code standards
```

#### 3. Test Thoroughly
```bash
# Run full test suite
pytest tests/

# Check code quality
black . && ruff check . && mypy app/

# Test with different scenarios
pytest tests/ -k "your_feature" -v
```

#### 4. Submit Pull Request
```bash
# Commit changes
git add .
git commit -m "feat: add your feature

- Add new functionality
- Include tests
- Update documentation

Resolves #123"

# Push to GitHub
git push origin feature/your-feature-name

# Create Pull Request
```

### Code Review Checklist

#### Before Submitting
- [ ] Code follows PEP 8 and project style
- [ ] Type hints are used appropriately
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] No linting errors
- [ ] Minimum 80% test coverage

#### During Code Review
- [ ] Functionality works as expected
- [ ] Code is readable and maintainable
- [ ] Tests are comprehensive
- [ ] Performance considerations addressed
- [ ] Security implications considered

## 📚 Resources & Documentation

### Documentation Links

#### Project Documentation
- **README.md**: Project overview and setup
- **API.md**: Comprehensive API documentation
- **DATABASE.md**: Database schema and design
- **DEPLOYMENT.md**: Deployment guides
- **MONITORING.md**: Monitoring and troubleshooting
- **TRAINING.md**: User training materials

#### External Resources
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org/
- **PostgreSQL Docs**: https://www.postgresql.org/docs/
- **Alembic Docs**: https://alembic.sqlalchemy.org/

### Development Tools

#### IDE Setup
- **VSCode**: Python extension, Pylint, Black formatter
- **PyCharm**: Professional Python IDE
- **Vim**: Python syntax highlighting, ALE linter

#### Development Servers
```bash
# Development server
uvicorn app.main:app --reload

# Production server
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# Debug server
uvicorn app.main:app --reload --log-level debug
```

### Support Channels

#### Team Communication
- **Slack**: #magflow-dev channel
- **Email**: dev-team@magflow-erp.com
- **GitHub Issues**: For bug reports and features

#### Code Review
- **GitHub PRs**: All code changes require review
- **Code Owners**: Senior developers for final approval
- **CI/CD**: Automated testing on all PRs

---

**MagFlow ERP Developer Onboarding Guide** - Welcome to the Team! 🚀
