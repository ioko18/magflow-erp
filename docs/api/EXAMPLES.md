# API Examples

This document provides copy-paste examples for using the MagFlow ERP Catalog API.

## Table of Contents
- [Authentication](#authentication)
- [Products](#products)
  - [List Products](#list-products)
  - [Get Product by ID](#get-product-by-id)
  - [Create Product](#create-product)
  - [Update Product](#update-product)
  - [Delete Product](#delete-product)
- [Brands](#brands)
  - [List Brands](#list-brands)
  - [Get Brand by ID](#get-brand-by-id)
- [Characteristics](#characteristics)
  - [List Characteristics](#list-characteristics)
  - [Get Characteristic Values](#get-characteristic-values)
- [Pagination](#pagination)
- [Filtering](#filtering)
- [Sorting](#sorting)
- [Error Handling](#error-handling)

## Authentication

All API requests require a valid JWT token in the `Authorization` header:

```http
GET /api/endpoint
Authorization: Bearer your_jwt_token_here
```

To obtain a token, use the authentication endpoint:

```bash
curl -X POST https://api.example.com/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

## Products

### List Products

**Request:**
```http
GET /catalog/products?q=wireless&category_id=1&min_price=50&max_price=200&in_stock=true&limit=10&sort_by=price&sort_direction=asc
```

**Response:**
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Wireless Headphones",
      "description": "High-quality wireless headphones with noise cancellation",
      "sku": "WH-1000XM4",
      "price": 199.99,
      "status": "active",
      "is_active": true,
      "stock_quantity": 15,
      "category_id": 1,
      "created_at": "2023-10-15T12:00:00Z",
      "updated_at": "2023-10-15T12:00:00Z"
    }
  ],
  "meta": {
    "total_items": 1,
    "total_pages": 1,
    "page": 1,
    "per_page": 10,
    "has_next": false,
    "has_prev": false,
    "next_cursor": null,
    "prev_cursor": null
  }
}
```

### Get Product by ID

**Request:**
```http
GET /catalog/products/550e8400-e29b-41d4-a716-446655440000
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Wireless Headphones",
  "description": "High-quality wireless headphones with noise cancellation",
  "sku": "WH-1000XM4",
  "price": 199.99,
  "status": "active",
  "is_active": true,
  "stock_quantity": 15,
  "category_id": 1,
  "created_at": "2023-10-15T12:00:00Z",
  "updated_at": "2023-10-15T12:00:00Z"
}
```

### Create Product

**Request:**
```http
POST /catalog/products
Content-Type: application/json

{
  "name": "New Wireless Earbuds",
  "description": "True wireless earbuds with 24h battery life",
  "sku": "TWE-2023",
  "price": 129.99,
  "status": "draft",
  "is_active": true,
  "stock_quantity": 0,
  "category_id": 1
}
```

**Response (201 Created):**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655441111",
  "name": "New Wireless Earbuds",
  "description": "True wireless earbuds with 24h battery life",
  "sku": "TWE-2023",
  "price": 129.99,
  "status": "draft",
  "is_active": true,
  "stock_quantity": 0,
  "category_id": 1,
  "created_at": "2023-10-16T10:30:00Z",
  "updated_at": "2023-10-16T10:30:00Z"
}
```

### Update Product

**Request:**
```http
PUT /catalog/products/660e8400-e29b-41d4-a716-446655441111
Content-Type: application/json

{
  "price": 119.99,
  "stock_quantity": 50,
  "status": "active"
}
```

**Response (200 OK):**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655441111",
  "name": "New Wireless Earbuds",
  "description": "True wireless earbuds with 24h battery life",
  "sku": "TWE-2023",
  "price": 119.99,
  "status": "active",
  "is_active": true,
  "stock_quantity": 50,
  "category_id": 1,
  "created_at": "2023-10-16T10:30:00Z",
  "updated_at": "2023-10-16T11:45:00Z"
}
```

### Delete Product

**Request:**
```http
DELETE /catalog/products/660e8400-e29b-41d4-a716-446655441111
```

**Response (204 No Content)**

## Brands

### List Brands

**Request:**
```http
GET /catalog/brands?limit=5
```

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "name": "Sony",
      "slug": "sony",
      "is_active": true,
      "created_at": "2023-10-15T12:00:00Z",
      "updated_at": "2023-10-15T12:00:00Z"
    },
    {
      "id": 2,
      "name": "Bose",
      "slug": "bose",
      "is_active": true,
      "created_at": "2023-10-15T12:00:00Z",
      "updated_at": "2023-10-15T12:00:00Z"
    }
  ],
  "meta": {
    "total_items": 2,
    "total_pages": 1,
    "page": 1,
    "per_page": 5,
    "has_next": false,
    "has_prev": false,
    "next_cursor": null,
    "prev_cursor": null
  }
}
```

### Get Brand by ID

**Request:**
```http
GET /catalog/brands/1
```

**Response:**
```json
{
  "id": 1,
  "name": "Sony",
  "slug": "sony",
  "is_active": true,
  "created_at": "2023-10-15T12:00:00Z",
  "updated_at": "2023-10-15T12:00:00Z"
}
```

## Characteristics

### List Characteristics

**Request:**
```http
GET /catalog/characteristics?category_id=1
```

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "name": "Color",
      "code": "color",
      "type": "select",
      "is_required": true,
      "is_filterable": true,
      "is_variant": true,
      "category_id": 1,
      "values": [
        {
          "id": 1,
          "value": "Black",
          "is_default": true,
          "position": 0
        },
        {
          "id": 2,
          "value": "White",
          "is_default": false,
          "position": 1
        }
      ],
      "created_at": "2023-10-15T12:00:00Z",
      "updated_at": "2023-10-15T12:00:00Z"
    },
    {
      "id": 2,
      "name": "Storage",
      "code": "storage",
      "type": "select",
      "is_required": true,
      "is_filterable": true,
      "is_variant": true,
      "category_id": 1,
      "values": [
        {
          "id": 3,
          "value": "64GB",
          "is_default": true,
          "position": 0
        },
        {
          "id": 4,
          "value": "128GB",
          "is_default": false,
          "position": 1
        },
        {
          "id": 5,
          "value": "256GB",
          "is_default": false,
          "position": 2
        }
      ],
      "created_at": "2023-10-15T12:00:00Z",
      "updated_at": "2023-10-15T12:00:00Z"
    }
  ],
  "meta": {
    "total_items": 2,
    "total_pages": 1,
    "page": 1,
    "per_page": 20,
    "has_next": false,
    "has_prev": false,
    "next_cursor": null,
    "prev_cursor": null
  }
}
```

### Get Characteristic Values

**Request:**
```http
GET /catalog/characteristics/1/values?category_id=1
```

**Response:**
```json
[
  {
    "id": 1,
    "value": "Black",
    "is_default": true,
    "position": 0
  },
  {
    "id": 2,
    "value": "White",
    "is_default": false,
    "position": 1
  },
  {
    "id": 3,
    "value": "Blue",
    "is_default": false,
    "position": 2
  }
]
```

## Pagination

The API uses cursor-based pagination. Here's an example of paginating through results:

**First Page:**
```http
GET /catalog/products?limit=2
```

**Response:**
```json
{
  "data": [
    {"id": "1", "name": "Product 1", "created_at": "2023-10-01T00:00:00Z"},
    {"id": "2", "name": "Product 2", "created_at": "2023-10-02T00:00:00Z"}
  ],
  "meta": {
    "total_items": 5,
    "total_pages": 3,
    "page": 1,
    "per_page": 2,
    "has_next": true,
    "has_prev": false,
    "next_cursor": "eyJjcmVhdGVkX2F0IjoiMjAyMy0xMC0wMlQwMDowMDowMFoiLCJpZCI6IjIifQ==",
    "prev_cursor": null
  }
}
```

**Next Page (using next_cursor):**
```http
GET /catalog/products?limit=2&cursor=eyJjcmVhdGVkX2F0IjoiMjAyMy0xMC0wMlQwMDowMDowMFoiLCJpZCI6IjIifQ==
```

## Filtering

Filter products by various criteria:

```http
# Filter by category and price range
GET /catalog/products?category_id=1&min_price=100&max_price=500

# Search by name or description
GET /catalog/products?q=wireless

# Filter by stock status
GET /catalog/products?in_stock=true

# Filter by status
GET /catalog/products?status=active

# Filter by multiple criteria
GET /catalog/products?category_id=1&status=active&in_stock=true&min_price=100
```

## Sorting

Sort results by any field in ascending or descending order:

```http
# Sort by price (ascending)
GET /catalog/products?sort_by=price&sort_direction=asc

# Sort by creation date (newest first)
GET /catalog/products?sort_by=created_at&sort_direction=desc

# Sort by name (A-Z)
GET /catalog/products?sort_by=name&sort_direction=asc
```

## Error Handling

### Login with curl
```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/auth/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=admin%40example.com&password=yourpassword'
```

### Login with httpie
```bash
http -f POST http://localhost:8000/api/v1/auth/login \
  username=admin@example.com \
  password=yourpassword
```

### Using the access token
```bash
# Set token from login response
export TOKEN="your_jwt_token_here"

# Make authenticated request
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/products
```

## Products

### Get all products
```bash
curl -H "Authorization: Bearer $TOKEN" \
  'http://localhost:8000/api/v1/products?limit=10&offset=0'
```

### Create a new product
```bash
curl -X 'POST' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name": "Premium Widget", "price": 99.99, "stock": 100}' \
  'http://localhost:8000/api/v1/products/'
```

## Categories

### Get all categories
```bash
curl -H "Authorization: Bearer $TOKEN" \
  'http://localhost:8000/api/v1/categories'
```

### Create a new category
```bash
curl -X 'POST' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name": "Electronics", "description": "Electronic devices"}' \
  'http://localhost:8000/api/v1/categories/'
```

## Error Handling

### 400 Bad Request

**Response:**
```json
{
  "type": "https://example.com/probs/bad-request",
  "title": "Bad Request",
  "status": 400,
  "detail": "Invalid request parameters",
  "instance": "/catalog/products",
  "errors": [
    {
      "field": "price",
      "message": "must be greater than 0"
    },
    {
      "field": "category_id",
      "message": "field required"
    }
  ]
}
```

### 401 Unauthorized

**Response:**
```json
{
  "type": "https://example.com/probs/unauthorized",
  "title": "Unauthorized",
  "status": 401,
  "detail": "Missing or invalid authentication credentials",
  "instance": "/catalog/products"
}
```

### 403 Forbidden

**Response:**
```json
{
  "type": "https://example.com/probs/forbidden",
  "title": "Forbidden",
  "status": 403,
  "detail": "You do not have permission to perform this action",
  "instance": "/catalog/products"
}
```

### 404 Not Found

**Response:**
```json
{
  "type": "https://example.com/probs/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "Product with ID 999 not found",
  "instance": "/catalog/products/999"
}
```

### 422 Unprocessable Entity

**Response:**
```json
{
  "type": "https://example.com/probs/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "The request contains invalid parameters",
  "instance": "/catalog/products",
  "errors": [
    {
      "loc": ["body", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    },
    {
      "loc": ["body", "price"],
      "msg": "ensure this value is greater than 0",
      "type": "value_error.number.not_gt",
      "ctx": {"limit_value": 0}
    }
  ]
}
```

### 429 Too Many Requests

**Response:**
```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/problem+json
Retry-After: 60
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1634567890

{
  "type": "https://example.com/probs/too-many-requests",
  "title": "Too Many Requests",
  "status": 429,
  "detail": "Rate limit exceeded. Please try again in 60 seconds.",
  "instance": "/catalog/products"
}
```

### 500 Internal Server Error

**Response:**
```json
{
  "type": "https://example.com/probs/internal-server-error",
  "title": "Internal Server Error",
  "status": 500,
  "detail": "An unexpected error occurred. Please try again later.",
  "instance": "/catalog/products"
}
```

### 502 Bad Gateway

**Response:**
```json
{
  "type": "https://example.com/probs/bad-gateway",
  "title": "Bad Gateway",
  "status": 502,
  "detail": "The server received an invalid response from the upstream service",
  "instance": "/catalog/products"
}
```

### 503 Service Unavailable

**Response:**
```json
{
  "type": "https://example.com/probs/service-unavailable",
  "title": "Service Unavailable",
  "status": 503,
  "detail": "The service is temporarily unavailable. Please try again later.",
  "instance": "/catalog/products",
  "retry_after": 300
}
```

### Handling validation errors
```http
HTTP/1.1 422 Unprocessable Entity
{
  "detail": [
    {
      "loc": ["body", "price"],
      "msg": "ensure this value is greater than 0",
      "type": "value_error.number.not_gt",
      "ctx": {"limit_value": 0}
    }
  ]
}
```

### Handling authentication errors
```http
HTTP/1.1 401 Unauthorized
{
  "detail": [
    {
      "type": "not_authenticated",
      "msg": "Not authenticated"
    }
  ]
}
```

## Pagination

### Using pagination parameters
```bash
# First page
curl 'http://localhost:8000/api/v1/products?limit=10&offset=0'

# Next page
curl 'http://localhost:8000/api/v1/products?limit=10&offset=10'
```

### Using cursor-based pagination
```bash
# Initial request
curl 'http://localhost:8000/api/v1/products?limit=10'

# Next page using cursor from previous response
curl 'http://localhost:8000/api/v1/products?limit=10&after=eyJpZCI6MTB9'
```

## Rate Limiting

### Checking rate limit headers
```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1641234567
X-RateLimit-Used: 1
```

### Handling rate limit exceeded
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
{
  "detail": "Rate limit exceeded. Please try again later.",
  "retry_after": 60
}
```
