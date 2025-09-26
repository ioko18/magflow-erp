# Cursor-based Pagination

This document describes the cursor-based pagination implementation for the MagFlow API.

## Overview

Cursor-based pagination is implemented for better performance with large datasets, especially when users are likely to paginate through many pages. This approach is more efficient than offset-based pagination for large datasets.

## Implementation Details

### Database Schema

- Added `created_at` column to `app.products` and `app.categories` tables
- Created composite indexes for efficient cursor-based pagination:
  - `idx_products_created_id_paginate` on `app.products(created_at DESC, id DESC)`
  - `idx_categories_created_id_paginate` on `app.categories(created_at DESC, id DESC)`

### API Endpoints

#### List Products

```
GET /products
```

**Query Parameters:**

- `limit`: Number of items per page (default: 20, max: 100)
- `after`: Cursor for next page
- `before`: Cursor for previous page
- `q`: Search query for product names

**Response Format:**

```json
{
  "items": [
    {
      "id": 1,
      "name": "Product 1",
      "price": 10.0,
      "created_at": "2023-01-01T00:00:00Z",
      "categories": ["Category 1", "Category 2"]
    }
  ],
  "next_cursor": "base64_encoded_cursor",
  "has_more": true
}
```

### Cursor Format

Cursors are base64-encoded JSON objects containing the sorting criteria:

```json
{
  "created_at": "2023-01-01T00:00:00Z",
  "id": 1
}
```

## Performance Considerations

- Uses composite index on `(created_at DESC, id DESC)` for efficient cursor-based pagination
- Includes proper error handling for invalid cursors
- Implements caching for better performance
- Uses parameterized queries to prevent SQL injection

## Testing

Run the test suite with:

```bash
pytest tests/test_cursor_pagination.py -v
```

Test cases cover:

- Basic pagination
- Forward and backward pagination
- Search with pagination
- Edge cases (first page, last page, empty results)
- Invalid cursor handling

## Example Usage

1. Get first page of products:

   ```bash
   curl "http://localhost:8000/products?limit=5"
   ```

1. Get next page using cursor:

   ```bash
   curl "http://localhost:8000/products?limit=5&after=eyJjcmVhdGVkX2F0IjoiMjAyMy0wMS0wMVQwMDowMDowMFoiLCJpZCI6NX0="
   ```

1. Search products with pagination:

   ```bash
   curl "http://localhost:8000/products?limit=5&q=Product"
   ```
