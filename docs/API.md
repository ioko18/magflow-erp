# MagFlow ERP API Documentation

[![FastAPI](https://img.shields.io/badge/FastAPI-0.116.1-green.svg)](https://fastapi.tiangolo.com/)
[![OpenAPI](https://img.shields.io/badge/OpenAPI-3.0-blue.svg)](https://swagger.io/specification/)

Comprehensive API documentation for MagFlow ERP system.

## 📋 Table of Contents

- [Authentication](#authentication)
- [User Management](#user-management)
- [Inventory Management](#inventory-management)
- [Sales Management](#sales-management)
- [Purchase Management](#purchase-management)
- [System & Monitoring](#system--monitoring)
- [Error Handling](#error-handling)
- [API Examples](#api-examples)

## 🔐 Authentication

All API endpoints require authentication using JWT tokens.

### Login & Token Management

#### POST `/api/v1/auth/access-token`

Get JWT access token for authentication.

**Request:**

```json
{
  "username": "admin",
  "password": "admin"
}
```

**Response:**

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Usage:**

```bash
curl -X POST "http://localhost:8000/api/v1/auth/access-token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin"
```

#### POST `/api/v1/auth/register`

Register a new user account.

**Request:**

```json
{
  "email": "user@example.com",
  "username": "newuser",
  "password": "securepassword",
  "full_name": "New User"
}
```

#### GET `/api/v1/users/me`

Get current user information.

**Headers:**

```
Authorization: Bearer <your_jwt_token>
```

## 👥 User Management

### Users

#### GET `/api/v1/users/`

List all users with pagination.

**Parameters:**

- `skip` (int, optional): Number of users to skip (default: 0)
- `limit` (int, optional): Number of users to return (default: 100)

**Response:**

```json
{
  "users": [
    {
      "id": 1,
      "email": "admin@example.com",
      "username": "admin",
      "full_name": "Administrator",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 100
}
```

#### POST `/api/v1/users/`

Create a new user.

**Request:**

```json
{
  "email": "user@example.com",
  "username": "newuser",
  "password": "securepassword",
  "full_name": "New User"
}
```

#### GET `/api/v1/users/{user_id}`

Get user by ID.

#### PUT `/api/v1/users/{user_id}`

Update user information.

#### DELETE `/api/v1/users/{user_id}`

Delete user (soft delete).

### Roles & Permissions

#### GET `/api/v1/roles/`

List all roles.

**Response:**

```json
{
  "roles": [
    {
      "id": 1,
      "name": "admin",
      "description": "Administrator role"
    },
    {
      "id": 2,
      "name": "user",
      "description": "Regular user role"
    }
  ]
}
```

#### GET `/api/v1/permissions/`

List all permissions.

## 📦 Inventory Management

### Inventory Items

#### GET `/api/v1/inventory/`

List all inventory items with pagination and filters.

**Parameters:**

- `skip` (int, optional): Number of items to skip
- `limit` (int, optional): Number of items to return
- `search` (str, optional): Search in name and description
- `category_id` (int, optional): Filter by category
- `warehouse_id` (int, optional): Filter by warehouse
- `low_stock` (bool, optional): Show only low stock items

**Response:**

```json
{
  "items": [
    {
      "id": 1,
      "name": "Gaming Laptop",
      "sku": "LT001",
      "description": "High-performance gaming laptop",
      "category_id": 1,
      "unit_cost": 1000.00,
      "stock_quantity": 50,
      "min_stock_level": 5,
      "max_stock_level": 100,
      "created_at": "2024-01-01T00:00:00"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 100
}
```

#### POST `/api/v1/inventory/`

Create a new inventory item.

**Request:**

```json
{
  "name": "Gaming Laptop",
  "sku": "LT001",
  "description": "High-performance gaming laptop",
  "category_id": 1,
  "unit_cost": 1000.00,
  "stock_quantity": 50,
  "min_stock_level": 5,
  "max_stock_level": 100
}
```

#### GET `/api/v1/inventory/{item_id}`

Get inventory item by ID.

#### PUT `/api/v1/inventory/{item_id}`

Update inventory item.

#### DELETE `/api/v1/inventory/{item_id}`

Delete inventory item.

#### POST `/api/v1/inventory/{item_id}/adjust-stock`

Adjust stock quantity.

**Request:**

```json
{
  "adjustment": 10,
  "reason": "Initial stock",
  "warehouse_id": 1
}
```

### Categories

#### GET `/api/v1/categories/`

List all categories.

**Response:**

```json
{
  "categories": [
    {
      "id": 1,
      "name": "Electronics",
      "description": "Electronic devices and components"
    }
  ]
}
```

#### POST `/api/v1/categories/`

Create a new category.

#### PUT `/api/v1/categories/{category_id}`

Update category.

#### DELETE `/api/v1/categories/{category_id}`

Delete category.

### Warehouses

#### GET `/api/v1/warehouses/`

List all warehouses.

**Response:**

```json
{
  "warehouses": [
    {
      "id": 1,
      "name": "Main Warehouse",
      "location": "Bucharest",
      "is_active": true
    }
  ]
}
```

#### POST `/api/v1/warehouses/`

Create a new warehouse.

**Request:**

```json
{
  "name": "Secondary Warehouse",
  "location": "Cluj",
  "description": "Secondary storage facility"
}
```

### Stock Movements

#### GET `/api/v1/stock-movements/`

List stock movements with pagination.

**Parameters:**

- `skip` (int, optional): Number of movements to skip
- `limit` (int, optional): Number of movements to return
- `item_id` (int, optional): Filter by inventory item
- `warehouse_id` (int, optional): Filter by warehouse

**Response:**

```json
{
  "movements": [
    {
      "id": 1,
      "item_id": 1,
      "warehouse_id": 1,
      "quantity": 10,
      "movement_type": "IN",
      "reason": "Purchase receipt",
      "created_at": "2024-01-01T10:00:00"
    }
  ],
  "total": 1
}
```

## 💰 Sales Management

### Customers

#### GET `/api/v1/customers/`

List all customers.

**Parameters:**

- `skip` (int, optional): Number of customers to skip
- `limit` (int, optional): Number of customers to return
- `search` (str, optional): Search in name and email

**Response:**

```json
{
  "customers": [
    {
      "id": 1,
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "+40700123456",
      "address": "Bucharest, Romania",
      "created_at": "2024-01-01T00:00:00"
    }
  ],
  "total": 1
}
```

#### POST `/api/v1/customers/`

Create a new customer.

**Request:**

```json
{
  "name": "Jane Smith",
  "email": "jane@example.com",
  "phone": "+40700654321",
  "address": "Cluj, Romania"
}
```

#### GET `/api/v1/customers/{customer_id}`

Get customer by ID.

#### PUT `/api/v1/customers/{customer_id}`

Update customer.

#### DELETE `/api/v1/customers/{customer_id}`

Delete customer.

### Sales Orders

#### GET `/api/v1/sales-orders/`

List sales orders.

**Parameters:**

- `skip` (int, optional): Number of orders to skip
- `limit` (int, optional): Number of orders to return
- `customer_id` (int, optional): Filter by customer
- `status` (str, optional): Filter by status
- `date_from` (date, optional): Filter from date
- `date_to` (date, optional): Filter to date

**Response:**

```json
{
  "orders": [
    {
      "id": 1,
      "order_number": "SO2024001",
      "customer_id": 1,
      "order_date": "2024-01-15",
      "status": "confirmed",
      "total_amount": 2400.00,
      "lines": [
        {
          "id": 1,
          "inventory_item_id": 1,
          "quantity": 2,
          "unit_price": 1200.00,
          "line_total": 2400.00
        }
      ]
    }
  ],
  "total": 1
}
```

#### POST `/api/v1/sales-orders/`

Create a new sales order.

**Request:**

```json
{
  "customer_id": 1,
  "order_date": "2024-01-15",
  "lines": [
    {
      "inventory_item_id": 1,
      "quantity": 2,
      "unit_price": 1200.00
    }
  ]
}
```

#### GET `/api/v1/sales-orders/{order_id}`

Get sales order by ID.

#### PUT `/api/v1/sales-orders/{order_id}`

Update sales order.

#### DELETE `/api/v1/sales-orders/{order_id}`

Cancel sales order.

### Sales Quotes

#### GET `/api/v1/sales-quotes/`

List sales quotes.

#### POST `/api/v1/sales-quotes/`

Create a new sales quote.

#### PUT `/api/v1/sales-quotes/{quote_id}/convert`

Convert quote to sales order.

### Invoices

#### GET `/api/v1/invoices/`

List invoices.

#### POST `/api/v1/invoices/`

Create invoice from sales order.

#### GET `/api/v1/invoices/{invoice_id}/pdf`

Download invoice PDF.

## 🛒 Purchase Management

### Suppliers

#### GET `/api/v1/suppliers/`

List all suppliers.

**Response:**

```json
{
  "suppliers": [
    {
      "id": 1,
      "name": "Tech Supplier Ltd",
      "email": "orders@techsupplier.com",
      "phone": "+40700123456",
      "address": "Supplier Address",
      "is_active": true
    }
  ],
  "total": 1
}
```

#### POST `/api/v1/suppliers/`

Create a new supplier.

**Request:**

```json
{
  "name": "New Supplier Ltd",
  "email": "contact@newsupplier.com",
  "phone": "+40700654321",
  "address": "New Supplier Address"
}
```

#### GET `/api/v1/suppliers/{supplier_id}`

Get supplier by ID.

#### PUT `/api/v1/suppliers/{supplier_id}`

Update supplier.

#### DELETE `/api/v1/suppliers/{supplier_id}`

Delete supplier.

### Purchase Orders

#### GET `/api/v1/purchase-orders/`

List purchase orders.

**Parameters:**

- `skip` (int, optional): Number of orders to skip
- `limit` (int, optional): Number of orders to return
- `supplier_id` (int, optional): Filter by supplier
- `status` (str, optional): Filter by status
- `date_from` (date, optional): Filter from date
- `date_to` (date, optional): Filter to date

**Response:**

```json
{
  "orders": [
    {
      "id": 1,
      "order_number": "PO2024001",
      "supplier_id": 1,
      "order_date": "2024-01-10",
      "status": "pending",
      "total_amount": 5000.00,
      "lines": [
        {
          "id": 1,
          "inventory_item_id": 1,
          "quantity": 5,
          "unit_price": 1000.00,
          "line_total": 5000.00
        }
      ]
    }
  ],
  "total": 1
}
```

#### POST `/api/v1/purchase-orders/`

Create a new purchase order.

**Request:**

```json
{
  "supplier_id": 1,
  "order_date": "2024-01-10",
  "expected_delivery": "2024-01-20",
  "lines": [
    {
      "inventory_item_id": 1,
      "quantity": 5,
      "unit_price": 1000.00
    }
  ]
}
```

#### GET `/api/v1/purchase-orders/{order_id}`

Get purchase order by ID.

#### PUT `/api/v1/purchase-orders/{order_id}`

Update purchase order.

#### DELETE `/api/v1/purchase-orders/{order_id}`

Cancel purchase order.

### Purchase Receipts

#### GET `/api/v1/purchase-receipts/`

List purchase receipts.

#### POST `/api/v1/purchase-receipts/`

Create purchase receipt.

#### PUT `/api/v1/purchase-receipts/{receipt_id}/receive`

Mark items as received.

### Purchase Requisitions

#### GET `/api/v1/purchase-requisitions/`

List purchase requisitions.

#### POST `/api/v1/purchase-requisitions/`

Create purchase requisition.

#### PUT `/api/v1/purchase-requisitions/{req_id}/approve`

Approve requisition.

## 🔧 System & Monitoring

### Health Checks

#### GET `/health`

Basic health check endpoint.

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### GET `/health/detailed`

Detailed health information.

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "checks": {
    "database": {
      "status": "healthy",
      "response_time": 12.3
    },
    "redis": {
      "status": "healthy",
      "response_time": 1.2
    },
    "external_apis": {
      "emag": {
        "status": "healthy",
        "response_time": 150.5
      }
    }
  }
}
```

#### GET `/health/database`

Database-specific health check.

#### GET `/health/external`

External services health check.

### Metrics

#### GET `/metrics`

Prometheus-compatible metrics endpoint.

**Response:** Prometheus format metrics for:

- Request counts and latency
- Database connection pool status
- Memory and CPU usage
- Custom business metrics

### System Information

#### GET `/api/v1/system/info`

Get system information.

**Response:**

```json
{
  "version": "1.0.0",
  "environment": "development",
  "database_version": "PostgreSQL 15.0",
  "python_version": "3.11.0",
  "dependencies": {
    "fastapi": "0.116.1",
    "sqlalchemy": "2.0.0",
    "pydantic": "2.0.0"
  }
}
```

## ❌ Error Handling

### Error Response Format

All API errors follow a consistent format:

**Validation Error:**

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Input validation failed",
    "details": {
      "field": "email",
      "message": "Invalid email format"
    }
  }
}
```

**Authentication Error:**

```json
{
  "error": {
    "code": "AUTHENTICATION_ERROR",
    "message": "Invalid credentials",
    "details": {
      "reason": "Invalid username or password"
    }
  }
}
```

**Business Logic Error:**

```json
{
  "error": {
    "code": "INSUFFICIENT_STOCK",
    "message": "Insufficient stock for this operation",
    "details": {
      "item_id": 1,
      "available": 5,
      "requested": 10
    }
  }
}
```

### HTTP Status Codes

- **200 OK**: Success
- **201 Created**: Resource created successfully
- **204 No Content**: Success with no content to return
- **400 Bad Request**: Invalid input data
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Access denied
- **404 Not Found**: Resource not found
- **409 Conflict**: Business rule violation
- **422 Unprocessable Entity**: Validation error
- **500 Internal Server Error**: Server error
- **503 Service Unavailable**: Service temporarily unavailable

## 📝 API Examples

### Python Client Example

```python
import httpx
import asyncio

class MagFlowClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.token = None

    async def authenticate(self, username: str, password: str):
        """Authenticate and get JWT token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/auth/access-token",
                data={"username": username, "password": password}
            )
            response.raise_for_status()
            self.token = response.json()["access_token"]
            return self.token

    async def get_inventory(self):
        """Get inventory items."""
        headers = {"Authorization": f"Bearer {self.token}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/inventory/",
                headers=headers
            )
            response.raise_for_status()
            return response.json()

    async def create_order(self, customer_id: int, items: list):
        """Create a sales order."""
        headers = {"Authorization": f"Bearer {self.token}"}
        order_data = {
            "customer_id": customer_id,
            "order_date": "2024-01-15",
            "lines": items
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/sales-orders/",
                json=order_data,
                headers=headers
            )
            response.raise_for_status()
            return response.json()

# Usage example
async def main():
    client = MagFlowClient()

    # Authenticate
    token = await client.authenticate("admin", "admin")
    print(f"Token: {token[:50]}...")

    # Get inventory
    inventory = await client.get_inventory()
    print(f"Inventory items: {len(inventory['items'])}")

    # Create order
    order = await client.create_order(
        customer_id=1,
        items=[{
            "inventory_item_id": 1,
            "quantity": 2,
            "unit_price": 1000.00
        }]
    )
    print(f"Order created: {order['order_number']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### JavaScript Client Example

```javascript
class MagFlowAPI {
    constructor(baseURL = 'http://localhost:8000') {
        this.baseURL = baseURL;
        this.token = null;
    }

    async authenticate(username, password) {
        const response = await fetch(`${this.baseURL}/api/v1/auth/access-token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                username: username,
                password: password
            })
        });

        if (!response.ok) {
            throw new Error('Authentication failed');
        }

        const data = await response.json();
        this.token = data.access_token;
        return data;
    }

    async getInventory() {
        const response = await fetch(`${this.baseURL}/api/v1/inventory/`, {
            headers: {
                'Authorization': `Bearer ${this.token}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to fetch inventory');
        }

        return await response.json();
    }

    async createCustomer(customerData) {
        const response = await fetch(`${this.baseURL}/api/v1/customers/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.token}`
            },
            body: JSON.stringify(customerData)
        });

        if (!response.ok) {
            throw new Error('Failed to create customer');
        }

        return await response.json();
    }
}

// Usage
const api = new MagFlowAPI();
await api.authenticate('admin', 'admin');
const inventory = await api.getInventory();
console.log('Inventory items:', inventory.items.length);
```

### cURL Examples

```bash
# Authentication
curl -X POST "http://localhost:8000/api/v1/auth/access-token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin"

# Get current user (replace TOKEN with actual token)
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer TOKEN"

# List inventory
curl -X GET "http://localhost:8000/api/v1/inventory/" \
  -H "Authorization: Bearer TOKEN"

# Create customer
curl -X POST "http://localhost:8000/api/v1/customers/" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+40700123456"
  }'

# Create sales order
curl -X POST "http://localhost:8000/api/v1/sales-orders/" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "order_date": "2024-01-15",
    "lines": [
      {
        "inventory_item_id": 1,
        "quantity": 2,
        "unit_price": 1200.00
      }
    ]
  }'
```

## 📋 Best Practices

### Authentication

- Always store JWT tokens securely
- Implement token refresh logic
- Use HTTPS in production
- Validate tokens on every request

### Error Handling

- Implement proper error handling for all API calls
- Log errors for debugging
- Provide meaningful error messages to users
- Handle network timeouts gracefully

### Performance

- Use pagination for large datasets
- Implement caching for frequently accessed data
- Use connection pooling for database connections
- Monitor API response times

### Security

- Validate all input data
- Use parameterized queries to prevent SQL injection
- Implement rate limiting
- Use HTTPS for all API calls
- Regularly update dependencies

______________________________________________________________________

**MagFlow ERP API** - Complete API Documentation 📚
