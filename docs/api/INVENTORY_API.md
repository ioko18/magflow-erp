# Inventory API Documentation

## Overview

The Inventory API provides endpoints for monitoring and managing eMAG product inventory, including low stock alerts, statistics, search functionality, and Excel export capabilities.

**Base Path**: `/api/v1/emag-inventory`

**Authentication**: All endpoints require JWT authentication via Bearer token.

---

## Endpoints

### 1. Get Inventory Statistics

Get comprehensive inventory statistics including stock levels, account distribution, and health metrics.

**Endpoint**: `GET /statistics`

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| account_type | string | No | Filter by account type: `main` or `fbe` |

**Response** (200 OK):
```json
{
  "status": "success",
  "data": {
    "total_products": 1250,
    "low_stock_count": 45,
    "out_of_stock_count": 12,
    "in_stock_count": 1193,
    "average_stock_level": 45.67,
    "total_stock_value": 125000.50,
    "by_account": {
      "main": 800,
      "fbe": 450
    },
    "low_stock_threshold": 10
  },
  "cached": false
}
```

**Caching**: Results are cached for 5 minutes.

**Example**:
```bash
curl -X GET "https://api.magflow.com/api/v1/emag-inventory/statistics?account_type=main" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 2. Get Low Stock Products

Retrieve products with low stock levels that need reordering.

**Endpoint**: `GET /low-stock`

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| skip | integer | No | 0 | Number of records to skip (pagination) |
| limit | integer | No | 20 | Maximum number of records (1-100) |
| account_type | string | No | - | Filter by account: `main` or `fbe` |
| group_by_sku | boolean | No | true | Group products by SKU across accounts |
| threshold | integer | No | 10 | Stock level threshold for low stock alert |

**Response** (200 OK):
```json
{
  "status": "success",
  "data": {
    "products": [
      {
        "id": "123",
        "part_number_key": "ABC-001",
        "sku": "ABC-001",
        "name": "Product Name",
        "brand": "Brand Name",
        "category_name": "Category",
        "account_type": "MAIN",
        "stock_quantity": 5,
        "main_stock": 5,
        "fbe_stock": 0,
        "price": 100.00,
        "currency": "RON",
        "stock_status": "critical",
        "reorder_quantity": 95,
        "sale_price": 120.00,
        "recommended_price": 130.00
      }
    ],
    "pagination": {
      "total": 45,
      "skip": 0,
      "limit": 20,
      "has_more": true
    },
    "threshold": 10,
    "grouped_by_sku": true
  }
}
```

**Stock Status Values**:
- `out_of_stock`: Stock quantity = 0
- `critical`: Stock quantity 1-10
- `low_stock`: Stock quantity 11-20
- `in_stock`: Stock quantity > 20

**Example**:
```bash
curl -X GET "https://api.magflow.com/api/v1/emag-inventory/low-stock?account_type=main&limit=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 3. Get Stock Alerts

Get stock alerts based on severity levels.

**Endpoint**: `GET /stock-alerts`

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| severity | string | No | Filter by severity: `critical`, `warning`, `info` |
| account_type | string | No | Filter by account type: `main` or `fbe` |
| limit | integer | No | Maximum number of alerts (1-200), default: 50 |

**Response** (200 OK):
```json
{
  "status": "success",
  "data": {
    "alerts": [
      {
        "severity": "critical",
        "message": "Out of stock: Product Name",
        "product": {
          "id": 123,
          "emag_id": "456",
          "name": "Product Name",
          "sku": "ABC-001",
          "account_type": "main",
          "stock": 0,
          "sale_price": 100.00
        },
        "timestamp": "2025-10-10T17:50:00Z"
      }
    ],
    "count": 12,
    "severity_filter": "critical",
    "thresholds": {
      "critical": 0,
      "warning": 10,
      "info": 50
    }
  }
}
```

**Example**:
```bash
curl -X GET "https://api.magflow.com/api/v1/emag-inventory/stock-alerts?severity=critical" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 4. Search Products

Search for eMAG products by SKU, part number, or name with stock breakdown.

**Endpoint**: `GET /search`

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| query | string | Yes | Search term (minimum 2 characters) |
| limit | integer | No | Maximum results (1-100), default: 20 |

**Response** (200 OK):
```json
{
  "status": "success",
  "data": {
    "products": [
      {
        "id": "123",
        "sku": "ABC-001",
        "part_number_key": "ABC-001",
        "name": "Product Name",
        "main_stock": 10,
        "fbe_stock": 5,
        "total_stock": 15,
        "price": 100.00,
        "currency": "RON",
        "brand": "Brand Name",
        "category_name": "Category",
        "ean": "1234567890123",
        "stock_status": "low_stock",
        "reorder_quantity": 5,
        "accounts": [
          {
            "account_type": "MAIN",
            "product_id": "123",
            "emag_id": "456",
            "stock": 10,
            "price": 100.00,
            "status": "active"
          },
          {
            "account_type": "FBE",
            "product_id": "124",
            "emag_id": "457",
            "stock": 5,
            "price": 100.00,
            "status": "active"
          }
        ]
      }
    ],
    "total": 1,
    "query": "ABC"
  },
  "cached": false
}
```

**Caching**: Results are cached for 10 minutes.

**Example**:
```bash
curl -X GET "https://api.magflow.com/api/v1/emag-inventory/search?query=ABC&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 5. Export Low Stock to Excel

Export low stock products to a formatted Excel file.

**Endpoint**: `GET /export/low-stock-excel`

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| account_type | string | No | Filter by account: `MAIN` or `FBE` |
| status | string | No | Filter by status: `critical`, `low_stock`, `out_of_stock` |

**Response** (200 OK):
- **Content-Type**: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- **Content-Disposition**: `attachment; filename=low_stock_products_YYYYMMDD_HHMMSS.xlsx`

**Excel File Structure**:
- **Headers**: Part Number, Product Name, Account Type, Current Stock, Status, Reorder Qty, Unit Price, Total Cost, Currency, Brand, Category, EAN, Last Updated
- **Conditional Formatting**: Red for out of stock, Yellow for low stock
- **Summary Section**: Total products, Total reorder cost, Generation timestamp
- **Features**: Frozen header row, Optimized column widths, Borders

**Error Response** (404 Not Found):
```json
{
  "detail": "No low stock products found"
}
```

**Example**:
```bash
curl -X GET "https://api.magflow.com/api/v1/emag-inventory/export/low-stock-excel?account_type=MAIN" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o low_stock_products.xlsx
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid parameter value"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 404 Not Found
```json
{
  "detail": "No low stock products found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to fetch inventory statistics: Database connection error"
}
```

---

## Rate Limiting

All endpoints are subject to rate limiting:
- **Limit**: 100 requests per minute per user
- **Headers**: 
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-RateLimit-Reset`: Time when limit resets (Unix timestamp)

---

## Caching

Certain endpoints use Redis caching to improve performance:

| Endpoint | Cache Duration | Cache Key Pattern |
|----------|----------------|-------------------|
| `/statistics` | 5 minutes | `inventory:stats:{account_type}` |
| `/search` | 10 minutes | `inventory:search:{query}:{limit}` |
| `/low-stock` | 3 minutes | `inventory:low_stock:{filters}` |

**Cache Headers**:
- Response includes `"cached": true/false` field indicating if data was served from cache

**Cache Invalidation**:
- Automatic on inventory updates
- Manual via cache management endpoints (admin only)

---

## Best Practices

### 1. Pagination
Always use pagination for large datasets:
```bash
# Get first page
GET /low-stock?skip=0&limit=50

# Get second page
GET /low-stock?skip=50&limit=50
```

### 2. Filtering
Combine filters for specific results:
```bash
GET /low-stock?account_type=main&status=critical&limit=20
```

### 3. Search Optimization
- Use specific search terms (minimum 2 characters)
- Limit results to needed amount
- Leverage caching by using consistent queries

### 4. Export Best Practices
- Export during off-peak hours for large datasets
- Use filters to reduce export size
- Cache export files client-side if needed frequently

---

## Code Examples

### Python (httpx)
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        "https://api.magflow.com/api/v1/emag-inventory/statistics",
        headers={"Authorization": f"Bearer {token}"}
    )
    data = response.json()
    print(f"Total products: {data['data']['total_products']}")
```

### JavaScript (fetch)
```javascript
const response = await fetch(
  'https://api.magflow.com/api/v1/emag-inventory/search?query=ABC',
  {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
);
const data = await response.json();
console.log(data.data.products);
```

### cURL
```bash
# Get statistics
curl -X GET "https://api.magflow.com/api/v1/emag-inventory/statistics" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Search products
curl -X GET "https://api.magflow.com/api/v1/emag-inventory/search?query=ABC" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Export to Excel
curl -X GET "https://api.magflow.com/api/v1/emag-inventory/export/low-stock-excel" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o inventory.xlsx
```

---

## Changelog

### Version 1.1.0 (2025-10-10)
- ✅ Added `/search` endpoint for product search
- ✅ Added caching support for statistics and search
- ✅ Added helper functions for stock status calculation
- ✅ Improved Excel export formatting
- ✅ Added stock breakdown by account in responses

### Version 1.0.0 (2025-09-01)
- Initial release
- Basic inventory endpoints
- Excel export functionality

---

## Support

For API support:
- **Documentation**: https://docs.magflow.com
- **Email**: api-support@magflow.com
- **GitHub Issues**: https://github.com/magflow/erp/issues
