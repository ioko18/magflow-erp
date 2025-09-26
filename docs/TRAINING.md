# MagFlow ERP - User Training Guide

[![FastAPI](https://img.shields.io/badge/FastAPI-0.116.1-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

Comprehensive user training guide and tutorials for MagFlow ERP system.

## 📋 Table of Contents

- [Getting Started](#getting-started)
- [User Interface](#user-interface)
- [Inventory Management](#inventory-management)
- [Sales Management](#sales-management)
- [Purchase Management](#purchase-management)
- [User Management](#user-management)
- [Reports & Analytics](#reports--analytics)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

## 🚀 Getting Started

### System Overview

**MagFlow ERP** is a comprehensive Enterprise Resource Planning system that helps businesses manage:

- **📦 Inventory**: Products, warehouses, stock levels
- **💰 Sales**: Customers, orders, invoices, payments
- **🛒 Purchasing**: Suppliers, orders, receipts
- **👥 Users**: Authentication, roles, permissions
- **📊 Analytics**: Reports, dashboards, insights

### First Login

1. **Access the Application**

   - Open your browser
   - Go to: `http://localhost:8000` (or your server URL)
   - Click on "API Documentation" or go directly to `/docs`

1. **Authentication**

   ```bash
   # Get authentication token
   curl -X POST "http://localhost:8000/api/v1/auth/access-token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin&password=admin"
   ```

1. **Explore the Interface**

   - Visit `/docs` for interactive API documentation
   - Try the health check endpoint: `/health`
   - Explore available endpoints in the documentation

### Navigation Guide

#### Main Sections

- **Authentication** (`/api/v1/auth/`): Login and user management
- **Inventory** (`/api/v1/inventory/`): Product and stock management
- **Sales** (`/api/v1/sales-orders/`): Order and customer management
- **Purchasing** (`/api/v1/purchase-orders/`): Supplier and procurement
- **Users** (`/api/v1/users/`): User administration
- **System** (`/health`, `/metrics`): Health and monitoring

## 🖥️ User Interface

### API Documentation Interface

#### Swagger UI (`/docs`)

- Interactive API documentation
- Try API endpoints directly from browser
- View request/response schemas
- Test authentication and authorization

#### ReDoc Interface (`/redoc`)

- Alternative API documentation
- Clean, readable format
- Easy navigation between endpoints

### Making API Requests

#### Using cURL

```bash
# Health check
curl http://localhost:8000/health

# Get inventory with authentication
curl -X GET "http://localhost:8000/api/v1/inventory/" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Create new product
curl -X POST "http://localhost:8000/api/v1/inventory/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sample Product",
    "sku": "SP001",
    "description": "Sample product description",
    "category_id": 1,
    "unit_cost": 10.99
  }'
```

#### Using HTTPie

```bash
# Login
http POST localhost:8000/api/v1/auth/access-token \
  username=admin password=admin

# Get inventory
http GET localhost:8000/api/v1/inventory/ \
  Authorization:"Bearer YOUR_TOKEN"

# Create customer
http POST localhost:8000/api/v1/customers/ \
  Authorization:"Bearer YOUR_TOKEN" \
  name="John Doe" \
  email="john@example.com" \
  phone="+40700123456"
```

#### Using Python

```python
import httpx
import asyncio

async def api_example():
    # Authentication
    auth_data = {
        "username": "admin",
        "password": "admin"
    }

    async with httpx.AsyncClient() as client:
        # Login
        auth_response = await client.post(
            "http://localhost:8000/api/v1/auth/access-token",
            data=auth_data
        )
        token = auth_response.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        # Get inventory
        inventory = await client.get(
            "http://localhost:8000/api/v1/inventory/",
            headers=headers
        )

        # Create sales order
        order_data = {
            "customer_id": 1,
            "order_date": "2024-01-15",
            "lines": [
                {
                    "inventory_item_id": 1,
                    "quantity": 2,
                    "unit_price": 100.00
                }
            ]
        }

        order = await client.post(
            "http://localhost:8000/api/v1/sales-orders/",
            json=order_data,
            headers=headers
        )

        print(f"Created order: {order.json()['order_number']}")

# Run the example
asyncio.run(api_example())
```

## 📦 Inventory Management

### Managing Products

#### Creating Products

```bash
# Create a new product
curl -X POST "http://localhost:8000/api/v1/inventory/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Wireless Mouse",
    "sku": "WM001",
    "description": "Ergonomic wireless mouse with USB receiver",
    "category_id": 1,
    "unit_cost": 25.99,
    "stock_quantity": 100,
    "min_stock_level": 10,
    "max_stock_level": 200
  }'
```

#### Updating Stock Levels

```bash
# Adjust stock quantity
curl -X POST "http://localhost:8000/api/v1/inventory/1/adjust-stock" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "adjustment": 50,
    "reason": "New shipment received",
    "warehouse_id": 1
  }'
```

#### Searching Products

```bash
# Search products
curl -X GET "http://localhost:8000/api/v1/inventory/?search=laptop&category_id=1" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get low stock items
curl -X GET "http://localhost:8000/api/v1/inventory/?low_stock=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Managing Categories

#### Creating Categories

```bash
# Create category hierarchy
curl -X POST "http://localhost:8000/api/v1/categories/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Electronics",
    "description": "Electronic devices and components"
  }'

# Create subcategory
curl -X POST "http://localhost:8000/api/v1/categories/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Laptops",
    "description": "Laptop computers",
    "parent_id": 1
  }'
```

### Managing Warehouses

#### Creating Warehouses

```bash
# Create warehouse
curl -X POST "http://localhost:8000/api/v1/warehouses/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Main Warehouse",
    "location": "Bucharest, Romania",
    "description": "Primary storage facility"
  }'
```

#### Stock Movement

```bash
# Transfer stock between warehouses
curl -X POST "http://localhost:8000/api/v1/stock-movements/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "item_id": 1,
    "from_warehouse_id": 1,
    "to_warehouse_id": 2,
    "quantity": 25,
    "movement_type": "TRANSFER",
    "reason": "Stock rebalancing"
  }'
```

## 💰 Sales Management

### Managing Customers

#### Creating Customers

```bash
# Create new customer
curl -X POST "http://localhost:8000/api/v1/customers/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corporation",
    "email": "orders@acme.com",
    "phone": "+40700123456",
    "address": "123 Business St, Bucharest, Romania",
    "tax_id": "RO12345678",
    "payment_terms": "Net 30",
    "credit_limit": 10000.00
  }'
```

#### Customer Search

```bash
# Search customers
curl -X GET "http://localhost:8000/api/v1/customers/?search=acme" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get customer orders
curl -X GET "http://localhost:8000/api/v1/sales-orders/?customer_id=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Sales Orders

#### Creating Orders

```bash
# Create sales order
curl -X POST "http://localhost:8000/api/v1/sales-orders/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "order_date": "2024-01-15",
    "lines": [
      {
        "inventory_item_id": 1,
        "quantity": 5,
        "unit_price": 1200.00
      },
      {
        "inventory_item_id": 2,
        "quantity": 2,
        "unit_price": 25.99
      }
    ]
  }'
```

#### Order Processing

```bash
# Update order status
curl -X PUT "http://localhost:8000/api/v1/sales-orders/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "confirmed"
  }'

# Ship order
curl -X PUT "http://localhost:8000/api/v1/sales-orders/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "shipped"
  }'
```

### Invoices

#### Creating Invoices

```bash
# Create invoice from order
curl -X POST "http://localhost:8000/api/v1/invoices/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": 1,
    "invoice_date": "2024-01-15",
    "due_date": "2024-02-14"
  }'
```

#### Invoice Management

```bash
# Get invoice PDF (if implemented)
curl -X GET "http://localhost:8000/api/v1/invoices/1/pdf" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  --output invoice_001.pdf

# Update payment status
curl -X PUT "http://localhost:8000/api/v1/invoices/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "paid"
  }'
```

## 🛒 Purchase Management

### Managing Suppliers

#### Creating Suppliers

```bash
# Create supplier
curl -X POST "http://localhost:8000/api/v1/suppliers/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tech Solutions Ltd",
    "email": "orders@techsolutions.com",
    "phone": "+40700654321",
    "address": "456 Supplier Ave, Cluj, Romania",
    "tax_id": "RO87654321",
    "payment_terms": "Net 15",
    "lead_time_days": 7
  }'
```

#### Supplier Evaluation

```bash
# Get supplier performance
curl -X GET "http://localhost:8000/api/v1/suppliers/1/performance" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get supplier orders
curl -X GET "http://localhost:8000/api/v1/purchase-orders/?supplier_id=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Purchase Orders

#### Creating Purchase Orders

```bash
# Create purchase order
curl -X POST "http://localhost:8000/api/v1/purchase-orders/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "supplier_id": 1,
    "order_date": "2024-01-10",
    "expected_delivery": "2024-01-20",
    "lines": [
      {
        "inventory_item_id": 1,
        "quantity": 50,
        "unit_price": 1000.00
      }
    ]
  }'
```

#### Order Processing

```bash
# Update order status
curl -X PUT "http://localhost:8000/api/v1/purchase-orders/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "confirmed"
  }'

# Receive items
curl -X POST "http://localhost:8000/api/v1/purchase-orders/1/receive" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "received_items": [
      {
        "item_id": 1,
        "quantity": 50,
        "condition": "good"
      }
    ]
  }'
```

### Purchase Receipts

#### Creating Receipts

```bash
# Create purchase receipt
curl -X POST "http://localhost:8000/api/v1/purchase-receipts/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": 1,
    "supplier_id": 1,
    "receipt_date": "2024-01-20",
    "items": [
      {
        "inventory_item_id": 1,
        "quantity": 50,
        "unit_price": 1000.00,
        "condition": "good"
      }
    ]
  }'
```

## 👥 User Management

### User Authentication

#### Login Process

```bash
# Authenticate user
curl -X POST "http://localhost:8000/api/v1/auth/access-token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin"

# Response
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### Token Usage

```bash
# Use token in requests
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Refresh token (if implemented)
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Authorization: Bearer YOUR_REFRESH_TOKEN"
```

### User Management

#### Creating Users

```bash
# Create new user (admin only)
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@company.com",
    "username": "newuser",
    "password": "securepassword",
    "full_name": "New User",
    "role": "user"
  }'
```

#### Managing Roles

```bash
# Get user roles
curl -X GET "http://localhost:8000/api/v1/users/1/roles" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Assign role
curl -X POST "http://localhost:8000/api/v1/users/1/roles" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role_id": 2
  }'
```

## 📊 Reports & Analytics

### Basic Reports

#### Sales Reports

```bash
# Daily sales summary
curl -X GET "http://localhost:8000/api/v1/reports/sales/daily?date=2024-01-15" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Monthly sales report
curl -X GET "http://localhost:8000/api/v1/reports/sales/monthly?year=2024&month=1" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Sales by customer
curl -X GET "http://localhost:8000/api/v1/reports/sales/by-customer?customer_id=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Inventory Reports

```bash
# Low stock report
curl -X GET "http://localhost:8000/api/v1/reports/inventory/low-stock" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Stock movement report
curl -X GET "http://localhost:8000/api/v1/reports/inventory/movements?date_from=2024-01-01&date_to=2024-01-31" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Inventory valuation
curl -X GET "http://localhost:8000/api/v1/reports/inventory/valuation" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Analytics

#### Dashboard Data

```bash
# Get dashboard metrics
curl -X GET "http://localhost:8000/api/v1/analytics/dashboard" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response
{
  "sales_today": 12500.00,
  "orders_today": 15,
  "low_stock_items": 5,
  "pending_orders": 3,
  "top_products": [
    {"name": "Laptop", "sales": 5000.00},
    {"name": "Mouse", "sales": 1250.00}
  ]
}
```

#### Trend Analysis

```bash
# Sales trends
curl -X GET "http://localhost:8000/api/v1/analytics/sales-trends?days=30" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Inventory turnover
curl -X GET "http://localhost:8000/api/v1/analytics/inventory-turnover?months=6" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## ✅ Best Practices

### API Usage Best Practices

#### Authentication

- Always store tokens securely
- Use HTTPS in production
- Implement token refresh logic
- Set appropriate token expiration times

#### Error Handling

- Always check HTTP status codes
- Handle rate limiting gracefully
- Implement retry logic for transient errors
- Log errors for debugging

#### Data Management

- Use pagination for large datasets
- Implement proper data validation
- Use appropriate data types
- Maintain data integrity

#### Performance

- Use caching for frequently accessed data
- Implement connection pooling
- Use async operations when possible
- Monitor API response times

### Security Best Practices

#### Access Control

- Use appropriate authentication methods
- Implement role-based permissions
- Validate user input thoroughly
- Use parameterized queries

#### Data Protection

- Encrypt sensitive data
- Use secure communication (HTTPS)
- Implement audit logging
- Regular security updates

#### API Security

- Rate limiting to prevent abuse
- Input validation and sanitization
- CORS configuration
- API versioning

### Data Management Best Practices

#### Inventory Management

- Regular stock audits
- Proper categorization
- Minimum stock level monitoring
- Stock movement tracking

#### Sales Management

- Customer data accuracy
- Order processing workflow
- Invoice management
- Payment tracking

#### Purchase Management

- Supplier evaluation
- Purchase order tracking
- Receipt verification
- Cost management

## 🔧 Troubleshooting

### Common User Issues

#### Authentication Problems

```bash
# Check if server is running
curl http://localhost:8000/health

# Test login credentials
curl -X POST "http://localhost:8000/api/v1/auth/access-token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpassword"

# Verify token
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### API Connection Issues

```bash
# Check server status
curl -v http://localhost:8000/health

# Test basic connectivity
ping localhost

# Check firewall settings
sudo ufw status

# Verify port availability
netstat -tlnp | grep :8000
```

#### Data Issues

```bash
# Check database connectivity
python -c "from app.db.base import engine; print('Database connected')"

# Verify data integrity
curl -X GET "http://localhost:8000/api/v1/inventory/" \
  -H "Authorization: Bearer YOUR_TOKEN" | jq '.items | length'

# Check user permissions
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer YOUR_TOKEN" | jq '.'
```

### Performance Issues

#### Slow Response Times

```bash
# Check system resources
htop

# Monitor database performance
curl http://localhost:8000/health/detailed | jq '.checks.database.response_time'

# Check Redis performance
redis-cli info | grep -E "(used_memory|connected_clients)"
```

#### Memory Issues

```bash
# Check memory usage
free -h

# Monitor application memory
curl http://localhost:8000/health/detailed | jq '.system.memory_usage'

# Check for memory leaks
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

## ❓ FAQ

### General Questions

#### Q: How do I reset my password?

**A:** Contact your system administrator or use the password reset functionality if available.

#### Q: How do I add a new product category?

**A:** Use the categories API endpoint:

```bash
curl -X POST "http://localhost:8000/api/v1/categories/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "New Category", "description": "Category description"}'
```

#### Q: How do I check system status?

**A:** Use the health check endpoint:

```bash
curl http://localhost:8000/health
```

### Technical Questions

#### Q: What are the system requirements?

**A:**

- Python 3.11+
- PostgreSQL 15+
- Redis 6+ (optional)
- 4GB RAM minimum
- 10GB storage minimum

#### Q: How do I backup my data?

**A:** Use the database backup tools:

```bash
# Create database backup
pg_dump magflow > magflow_backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
psql magflow < magflow_backup_20240115_120000.sql
```

#### Q: How do I monitor system performance?

**A:** Use the monitoring endpoints:

```bash
curl http://localhost:8000/metrics  # Prometheus metrics
curl http://localhost:8000/health/detailed  # Detailed health info
```

### Business Questions

#### Q: How do I create a sales order?

**A:** Use the sales orders API:

```bash
curl -X POST "http://localhost:8000/api/v1/sales-orders/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "order_date": "2024-01-15",
    "lines": [{"inventory_item_id": 1, "quantity": 2, "unit_price": 100.00}]
  }'
```

#### Q: How do I check inventory levels?

**A:** Use the inventory API:

```bash
curl -X GET "http://localhost:8000/api/v1/inventory/?low_stock=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Q: How do I generate reports?

**A:** Use the reports API:

```bash
curl -X GET "http://localhost:8000/api/v1/reports/sales/daily?date=2024-01-15" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

______________________________________________________________________

**MagFlow ERP User Training Guide** - Complete User Training and Tutorial Documentation 👥
