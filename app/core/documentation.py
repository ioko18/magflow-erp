"""API Documentation Enhancement Utilities.

This module provides tools for generating comprehensive API documentation,
including OpenAPI schema enhancements and interactive documentation.
"""

from typing import Any, Dict

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


class APIDocGenerator:
    """Generate enhanced API documentation."""

    @staticmethod
    def generate_enhanced_openapi_schema(app: FastAPI) -> Dict[str, Any]:
        """Generate enhanced OpenAPI schema with examples and detailed descriptions."""

        def custom_openapi():
            if app.openapi_schema:
                return app.openapi_schema

            openapi_schema = get_openapi(
                title=app.title,
                version=app.version,
                openapi_version="3.0.0",
                description=getattr(app, "description", ""),
                routes=app.routes,
            )

            # Add enhanced security schemes
            openapi_schema["components"]["securitySchemes"] = {
                "JWT": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "Enter JWT token (only the token, without 'Bearer ' prefix)",
                },
                "APIKey": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                    "description": "API key for service-to-service authentication",
                },
            }

            # Add error response schemas
            openapi_schema["components"]["schemas"].update(
                {
                    "ErrorResponse": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string", "example": "ValidationError"},
                            "message": {
                                "type": "string",
                                "example": "Invalid input data",
                            },
                            "details": {"type": "object"},
                        },
                        "required": ["error", "message"],
                    },
                    "ValidationErrorDetail": {
                        "type": "object",
                        "properties": {
                            "field": {"type": "string", "example": "email"},
                            "message": {
                                "type": "string",
                                "example": "Invalid email format",
                            },
                            "value": {"type": "any", "example": "invalid-email"},
                        },
                    },
                },
            )

            app.openapi_schema = openapi_schema
            return app.openapi_schema

        return custom_openapi

    @staticmethod
    def generate_api_examples() -> Dict[str, Any]:
        """Generate API usage examples."""
        return {
            "authentication": {
                "login": {
                    "summary": "User Authentication",
                    "description": "Authenticate user and receive JWT tokens",
                    "request": {
                        "method": "POST",
                        "url": "/api/v1/auth/login",
                        "headers": {"Content-Type": "application/json"},
                        "body": {
                            "email": "user@example.com",
                            "password": "secure_password",
                        },
                    },
                    "response": {
                        "status": 200,
                        "body": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "token_type": "bearer",
                        },
                    },
                },
            },
            "reporting": {
                "get_sales_report": {
                    "summary": "Generate Sales Report",
                    "description": "Generate comprehensive sales analytics report",
                    "request": {
                        "method": "GET",
                        "url": "/api/v1/reports/sales/overview",
                        "headers": {"Authorization": "Bearer {access_token}"},
                        "params": {
                            "start_date": "2024-01-01",
                            "end_date": "2024-01-31",
                        },
                    },
                    "response": {
                        "status": 200,
                        "body": {
                            "id": "report_123",
                            "title": "Sales Overview Report",
                            "summary": {
                                "total_records": 1250,
                                "key_metrics": {
                                    "total_orders": 1250,
                                    "total_revenue": "$125,000.00",
                                },
                            },
                        },
                    },
                },
            },
        }

    @staticmethod
    def generate_deployment_guide() -> str:
        """Generate deployment and configuration guide."""
        return """
# MagFlow ERP - Deployment Guide

## Environment Setup

### 1. Environment Variables
Create a `.env` file with the following variables:

```bash
# Application
APP_ENV=production
APP_NAME=magflow
APP_PORT=8000
DEBUG=false

# Database
DB_HOST=your-database-host
DB_PORT=5432
DB_NAME=magflow_prod
DB_USER=your_db_user
DB_PASS=your_secure_password

# Redis
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# JWT
SECRET_KEY=your-secure-jwt-secret
JWT_ALGORITHM=RS256

# Security
ALLOWED_HOSTS=https://your-domain.com
CORS_ORIGINS=https://your-domain.com
```

### 2. Database Setup
1. Create PostgreSQL database
2. Run migrations: `alembic upgrade head`
3. Create admin user: `python create_admin_user.py`

### 3. SSL/TLS Configuration
- Configure SSL certificates
- Update security headers
- Set up HTTPS redirect

### 4. Monitoring
- Configure Prometheus metrics
- Set up Grafana dashboards
- Configure alerting rules

## Security Best Practices

1. **Use strong passwords** for all database users
2. **Enable SSL/TLS** for all connections
3. **Configure rate limiting** for API endpoints
4. **Set up proper logging** for audit trails
5. **Regular security updates** for all dependencies
6. **Use environment-specific configurations**

## Performance Optimization

1. **Configure connection pooling** for database
2. **Set up Redis caching** for frequently accessed data
3. **Configure proper logging levels** for production
4. **Set up monitoring** for performance metrics
5. **Regular database maintenance** (VACUUM, ANALYZE)

## Backup Strategy

1. **Database backups** - daily automated backups
2. **Configuration backups** - version control for configs
3. **Log retention** - proper log rotation policies
4. **Disaster recovery** - documented recovery procedures
"""


class CodeDocumentationGenerator:
    """Generate code documentation and API references."""

    @staticmethod
    def generate_module_docstring(module_name: str, description: str) -> str:
        """Generate docstring for a module."""
        return f'''"""
{module_name}

{description}

This module provides functionality for {module_name.lower()} operations
including data validation, business logic, and API endpoints.

Classes:
    {module_name}Service: Main service class for {module_name.lower()} operations
    {module_name}Repository: Data access layer for {module_name.lower()} entities
    {module_name}Schema: Pydantic models for {module_name.lower()} data validation

Functions:
    get_{module_name.lower()}: Retrieve {module_name.lower()} data
    create_{module_name.lower()}: Create new {module_name.lower()} record
    update_{module_name.lower()}: Update existing {module_name.lower()} record
    delete_{module_name.lower()}: Delete {module_name.lower()} record

Examples:
    >>> from app.services.{module_name.lower()}_service import {module_name}Service
    >>> service = {module_name}Service(db_session)
    >>> result = await service.get_all()
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class {module_name}Service:
    """Service class for {module_name.lower()} operations."""

    def __init__(self, db: AsyncSession):
        """Initialize {module_name.lower()} service."""
        self.db = db

    async def get_all(self) -> List[Dict[str, Any]]:
        """Get all {module_name.lower()} records."""
        # Implementation here
        pass
'''

    @staticmethod
    def generate_api_endpoint_docstring(
        endpoint: str,
        method: str,
        description: str,
        parameters: Dict[str, Any] = None,
        responses: Dict[str, Any] = None,
    ) -> str:
        """Generate docstring for API endpoint."""
        return f'''    @router.{method.lower()}("{endpoint}")
    async def {method.lower().replace("/", "_")}{endpoint.replace("/", "_").replace("-", "_")}(
        {", ".join([f"{k}: {v}" for k, v in (parameters or {}).items()])}
    ) -> {responses.get("200", "Any") if responses else "Any"}:
        """
        {description}

        **Parameters:**
        {chr(10).join([f"        - **{k}**: {v}" for k, v in (parameters or {}).items()])}

        **Returns:**
        {chr(10).join([f"        - **{k}**: {v}" for k, v in (responses or {}).items()])}

        **Raises:**
            HTTPException: When validation fails or resource not found
        """
        # Implementation here
        pass'''
