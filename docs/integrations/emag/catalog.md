# eMAG Catalog Integration

This document provides an overview of the eMAG Catalog API integration for the MagFlow ERP system.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [API Endpoints](#api-endpoints)
  - [Products](#products)
  - [Brands](#brands)
  - [Characteristics](#characteristics)
- [Error Handling](#error-handling)
- [Pagination](#pagination)
- [Filtering](#filtering)
- [Sorting](#sorting)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Overview

The Catalog API provides access to product, brand, and characteristic data in the eMAG Marketplace. It supports full CRUD operations for products and read-only access to brands and characteristics.

## Authentication

All API requests require authentication using a valid JWT token in the `Authorization` header:

```
Authorization: Bearer <your_jwt_token>
```

## Rate Limiting

The API enforces rate limiting to ensure fair usage:

- **Standard Rate Limit**: 1000 requests per minute per IP address
- **Burst Limit**: 100 requests per second

Responses include rate limit headers:

- `X-RateLimit-Limit`: Maximum number of requests allowed in the time window
- `X-RateLimit-Remaining`: Remaining requests in the current window
- `X-RateLimit-Reset`: Time when the rate limit resets (UTC epoch seconds)

## API Endpoints

### Products

#### List Products

```http
GET /catalog/products
```

**Query Parameters:**

| Parameter        | Type    | Required | Description                                      |
| ---------------- | ------- | -------- | ------------------------------------------------ |
| `q`              | string  | No       | Search query for product names and descriptions  |
| `category_id`    | integer | No       | Filter by category ID                            |
| `brand_id`       | integer | No       | Filter by brand ID                               |
| `status`         | string  | No       | Filter by status (active, draft, archived)       |
| `min_price`      | number  | No       | Minimum price filter                             |
| `max_price`      | number  | No       | Maximum price filter                             |
| `in_stock`       | boolean | No       | Filter by in-stock status                        |
| `limit`          | integer | No       | Number of items per page (default: 20, max: 100) |
| `cursor`         | string  | No       | Cursor for pagination                            |
| `sort_by`        | string  | No       | Field to sort by (name, price, created_at)       |
| `sort_direction` | string  | No       | Sort direction (asc, desc)                       |

**Response:**

```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Test Product",
      "description": "A test product",
      "sku": "TEST-001",
      "price": 99.99,
      "status": "active",
      "is_active": true,
      "stock_quantity": 10,
      "category_id": 1,
      "created_at": "2023-10-15T12:00:00Z",
      "updated_at": "2023-10-15T12:00:00Z"
    }
  ],
  "meta": {
    "total_items": 1,
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

#### Get Product by ID

```http
GET /catalog/products/{product_id}
```

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Test Product",
  "description": "A test product",
  "sku": "TEST-001",
  "price": 99.99,
  "status": "active",
  "is_active": true,
  "stock_quantity": 10,
  "category_id": 1,
  "created_at": "2023-10-15T12:00:00Z",
  "updated_at": "2023-10-15T12:00:00Z"
}
```

#### Create Product

```http
POST /catalog/products
```

**Request Body:**

```json
{
  "name": "New Product",
  "description": "A new product",
  "sku": "NEW-001",
  "price": 199.99,
  "status": "draft",
  "is_active": true,
  "stock_quantity": 0,
  "category_id": 1
}
```

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "New Product",
  "description": "A new product",
  "sku": "NEW-001",
  "price": 199.99,
  "status": "draft",
  "is_active": true,
  "stock_quantity": 0,
  "category_id": 1,
  "created_at": "2023-10-15T12:00:00Z",
  "updated_at": "2023-10-15T12:00:00Z"
}
```

#### Update Product

```http
PUT /catalog/products/{product_id}
```

**Request Body:**

```json
{
  "name": "Updated Product",
  "price": 249.99,
  "stock_quantity": 5
}
```

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Updated Product",
  "description": "A new product",
  "sku": "NEW-001",
  "price": 249.99,
  "status": "draft",
  "is_active": true,
  "stock_quantity": 5,
  "category_id": 1,
  "created_at": "2023-10-15T12:00:00Z",
  "updated_at": "2023-10-15T13:00:00Z"
}
```

#### Delete Product

```http
DELETE /catalog/products/{product_id}
```

**Response:**

```
204 No Content
```

### Brands

#### List Brands

```http
GET /catalog/brands
```

**Query Parameters:**

| Parameter | Type    | Required | Description                                      |
| --------- | ------- | -------- | ------------------------------------------------ |
| `limit`   | integer | No       | Number of items per page (default: 20, max: 100) |
| `cursor`  | string  | No       | Cursor for pagination                            |

**Response:**

```json
{
  "data": [
    {
      "id": 1,
      "name": "Test Brand",
      "slug": "test-brand",
      "is_active": true,
      "created_at": "2023-10-15T12:00:00Z",
      "updated_at": "2023-10-15T12:00:00Z"
    }
  ],
  "meta": {
    "total_items": 1,
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

#### Get Brand by ID

```http
GET /catalog/brands/{brand_id}
```

**Response:**

```json
{
  "id": 1,
  "name": "Test Brand",
  "slug": "test-brand",
  "is_active": true,
  "created_at": "2023-10-15T12:00:00Z",
  "updated_at": "2023-10-15T12:00:00Z"
}
```

### Characteristics

#### List Characteristics

```http
GET /catalog/characteristics
```

**Query Parameters:**

| Parameter     | Type    | Required | Description                                      |
| ------------- | ------- | -------- | ------------------------------------------------ |
| `category_id` | integer | Yes      | Filter by category ID                            |
| `limit`       | integer | No       | Number of items per page (default: 20, max: 100) |
| `cursor`      | string  | No       | Cursor for pagination                            |

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
          "value": "Red",
          "is_default": true,
          "position": 0
        }
      ],
      "created_at": "2023-10-15T12:00:00Z",
      "updated_at": "2023-10-15T12:00:00Z"
    }
  ],
  "meta": {
    "total_items": 1,
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

#### Get Characteristic Values

```http
GET /catalog/characteristics/{characteristic_id}/values
```

**Query Parameters:**

| Parameter     | Type    | Required | Description |
| ------------- | ------- | -------- | ----------- |
| `category_id` | integer | Yes      | Category ID |

**Response:**

```json
[
  {
    "id": 1,
    "value": "Red",
    "is_default": true,
    "position": 0
  },
  {
    "id": 2,
    "value": "Blue",
    "is_default": false,
    "position": 1
  }
]
```

## Error Handling

Errors follow the [RFC 9457 Problem Details](https://datatracker.ietf.org/doc/html/rfc9457) format:

```json
{
  "type": "https://example.com/probs/validation-error",
  "title": "Invalid Input",
  "status": 400,
  "detail": "The request contains invalid parameters",
  "instance": "/catalog/products",
  "errors": [
    {
      "field": "price",
      "message": "must be greater than 0"
    }
  ]
}
```

### Common Error Status Codes

| Status Code | Description                             |
| ----------- | --------------------------------------- |
| 400         | Bad Request - Invalid request data      |
| 401         | Unauthorized - Missing or invalid JWT   |
| 403         | Forbidden - Insufficient permissions    |
| 404         | Not Found - Resource not found          |
| 422         | Unprocessable Entity - Validation error |
| 429         | Too Many Requests - Rate limit exceeded |
| 500         | Internal Server Error                   |
| 502         | Bad Gateway - Upstream service error    |
| 503         | Service Unavailable - Try again later   |

## Pagination

The API uses cursor-based pagination for list endpoints. The response includes a `meta` object with pagination details.

### Request Parameters

| Parameter | Type    | Required | Description                                                 |
| --------- | ------- | -------- | ----------------------------------------------------------- |
| `limit`   | integer | No       | Number of items per page (default: 20, max: 100)            |
| `cursor`  | string  | No       | Cursor for pagination (from `next_cursor` or `prev_cursor`) |

### Response Fields

| Field         | Type    | Description                                       |
| ------------- | ------- | ------------------------------------------------- |
| `total_items` | integer | Total number of items across all pages            |
| `total_pages` | integer | Total number of pages                             |
| `page`        | integer | Current page number                               |
| `per_page`    | integer | Number of items per page                          |
| `has_next`    | boolean | Whether there are more items after this page      |
| `has_prev`    | boolean | Whether there are items before this page          |
| `next_cursor` | string  | Cursor for the next page (null if no more items)  |
| `prev_cursor` | string  | Cursor for the previous page (null if first page) |

## Filtering

List endpoints support filtering using query parameters. The available filters depend on the endpoint.

### Common Filters

| Parameter    | Type    | Description                                     |
| ------------ | ------- | ----------------------------------------------- |
| `q`          | string  | Search query (searches in name and description) |
| `status`     | string  | Filter by status (active, draft, archived)      |
| `is_active`  | boolean | Filter by active status                         |
| `created_at` | string  | Filter by creation date (ISO 8601 format)       |
| `updated_at` | string  | Filter by last update date (ISO 8601 format)    |

### Product-Specific Filters

| Parameter     | Type    | Description               |
| ------------- | ------- | ------------------------- |
| `category_id` | integer | Filter by category ID     |
| `brand_id`    | integer | Filter by brand ID        |
| `min_price`   | number  | Filter by minimum price   |
| `max_price`   | number  | Filter by maximum price   |
| `in_stock`    | boolean | Filter by in-stock status |

## Sorting

List endpoints support sorting using the `sort_by` and `sort_direction` parameters.

### Sortable Fields

| Field        | Description                |
| ------------ | -------------------------- |
| `name`       | Sort by product/brand name |
| `price`      | Sort by product price      |
| `created_at` | Sort by creation date      |
| `updated_at` | Sort by last update date   |

### Sort Direction

- `asc`: Ascending order (A-Z, 0-9, oldest first)
- `desc`: Descending order (Z-A, 9-0, newest first)

## Examples

### List Active Products in a Category

```http
GET /catalog/products?category_id=1&status=active&limit=10&sort_by=price&sort_direction=asc
```

### Search for Products

```http
GET /catalog/products?q=wireless+headphones&in_stock=true&min_price=50&max_price=200
```

### Paginate Through Results

1. First request:

   ```http
   GET /catalog/products?limit=20
   ```

   Response includes `next_cursor` for the next page.

1. Next page:

   ```http
   GET /catalog/products?limit=20&cursor=eyJjcmVhdGVkX2F0IjoiMjAyMy0xMC0xNVQxMjowMDowMFoiLCJpZCI6IjU1MGU4NDAwLWUyOWItNDFkNC1hNzE2LTQ0NjY1NTQ0MDAwMCJ9
   ```

## Troubleshooting

### Common Issues

1. **Authentication Failed**

   - Verify the JWT token is valid and not expired
   - Check that the `Authorization` header is correctly formatted

1. **Rate Limit Exceeded**

   - Check the `X-RateLimit-Remaining` header
   - Implement exponential backoff in your client

1. **Validation Errors**

   - Check the error response for details on which fields failed validation
   - Ensure all required fields are provided with the correct data types

1. **Not Found Errors**

   - Verify the resource ID exists
   - Check that you have permission to access the resource

### Getting Help

For additional assistance, please contact the API support team at `api-support@example.com`.
