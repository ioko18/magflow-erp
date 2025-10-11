# 🧪 API Testing Examples - Low Stock Suppliers

## 📋 Overview

Acest document conține exemple concrete de request/response pentru testarea endpoint-urilor Low Stock Suppliers.

---

## 🔐 Authentication

Toate request-urile necesită autentificare. Obține token-ul astfel:

### Login Request
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin@magflow.com",
    "password": "your_password"
  }'
```

### Response
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Folosește token-ul în header:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 📊 Endpoint 1: Get Low Stock Products with Suppliers

### Basic Request - All Low Stock Products

```bash
curl -X GET "http://localhost:8000/api/v1/inventory/low-stock-with-suppliers" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Response Example
```json
{
  "status": "success",
  "data": {
    "products": [
      {
        "inventory_item_id": 123,
        "product_id": 456,
        "sku": "ARD-UNO-001",
        "name": "Arduino UNO R3 Development Board",
        "chinese_name": "Arduino UNO R3开发板",
        "image_url": "https://example.com/images/arduino.jpg",
        "warehouse_id": 1,
        "warehouse_name": "Main Warehouse",
        "warehouse_code": "WH-MAIN",
        "quantity": 0,
        "reserved_quantity": 0,
        "available_quantity": 0,
        "minimum_stock": 10,
        "reorder_point": 15,
        "maximum_stock": 50,
        "unit_cost": 22.80,
        "stock_status": "out_of_stock",
        "reorder_quantity": 30,
        "location": "Shelf A-12",
        "base_price": 45.00,
        "currency": "RON",
        "is_discontinued": false,
        "suppliers": [
          {
            "supplier_id": "sheet_45",
            "supplier_name": "Shenzhen Electronics Co.",
            "supplier_type": "google_sheets",
            "price": 22.80,
            "currency": "CNY",
            "price_ron": 68.40,
            "supplier_url": "https://detail.1688.com/offer/123456789.html",
            "supplier_contact": "contact@shenzhen-elec.com",
            "chinese_name": "Arduino UNO R3 开发板 ATmega328P",
            "specification": "ATmega328P, USB Cable included",
            "is_preferred": true,
            "is_verified": true,
            "last_updated": "2025-10-10T10:30:00"
          },
          {
            "supplier_id": "sheet_67",
            "supplier_name": "Guangzhou Tech Supplier",
            "supplier_type": "google_sheets",
            "price": 24.50,
            "currency": "CNY",
            "price_ron": 73.50,
            "supplier_url": "https://detail.1688.com/offer/987654321.html",
            "supplier_contact": "sales@gz-tech.com",
            "chinese_name": "Arduino UNO R3 单片机开发板",
            "specification": null,
            "is_preferred": false,
            "is_verified": true,
            "last_updated": "2025-10-09T15:20:00"
          },
          {
            "supplier_id": "1688_89",
            "supplier_name": "Beijing Components Ltd",
            "supplier_type": "1688",
            "price": 21.00,
            "currency": "CNY",
            "price_ron": null,
            "supplier_url": "https://detail.1688.com/offer/555666777.html",
            "supplier_contact": null,
            "chinese_name": "Arduino UNO R3 控制板",
            "specification": "Compatible with Arduino IDE",
            "is_preferred": false,
            "is_verified": false,
            "last_updated": "2025-10-08T09:15:00"
          }
        ],
        "supplier_count": 3
      }
    ],
    "pagination": {
      "total": 25,
      "skip": 0,
      "limit": 20,
      "has_more": true
    },
    "summary": {
      "total_low_stock": 25,
      "out_of_stock": 8,
      "critical": 10,
      "low_stock": 7,
      "products_with_suppliers": 20,
      "products_without_suppliers": 5
    }
  }
}
```

---

### Filtered Request - Only Out of Stock

```bash
curl -X GET "http://localhost:8000/api/v1/inventory/low-stock-with-suppliers?status=out_of_stock" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Filtered Request - Critical Stock in Specific Warehouse

```bash
curl -X GET "http://localhost:8000/api/v1/inventory/low-stock-with-suppliers?status=critical&warehouse_id=1" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Paginated Request

```bash
curl -X GET "http://localhost:8000/api/v1/inventory/low-stock-with-suppliers?skip=20&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## 📤 Endpoint 2: Export Low Stock by Supplier

### Request Body Format

```json
[
  {
    "product_id": 456,
    "sku": "ARD-UNO-001",
    "supplier_id": "sheet_45",
    "reorder_quantity": 30
  },
  {
    "product_id": 789,
    "sku": "ESP32-DEV-001",
    "supplier_id": "sheet_45",
    "reorder_quantity": 20
  },
  {
    "product_id": 101,
    "sku": "NODEMCU-001",
    "supplier_id": "sheet_67",
    "reorder_quantity": 25
  }
]
```

### cURL Request

```bash
curl -X POST "http://localhost:8000/api/v1/inventory/export/low-stock-by-supplier" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "product_id": 456,
      "sku": "ARD-UNO-001",
      "supplier_id": "sheet_45",
      "reorder_quantity": 30
    },
    {
      "product_id": 789,
      "sku": "ESP32-DEV-001",
      "supplier_id": "sheet_45",
      "reorder_quantity": 20
    }
  ]' \
  --output low_stock_export.xlsx
```

### Response
- **Content-Type:** `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- **Content-Disposition:** `attachment; filename=low_stock_by_supplier_20251010_195000.xlsx`
- **Body:** Binary Excel file

---

## 🧪 Testing with Postman

### Collection Setup

1. **Create Collection:** "Low Stock Suppliers API"
2. **Add Environment Variables:**
   ```json
   {
     "base_url": "http://localhost:8000/api/v1",
     "token": "YOUR_TOKEN_HERE"
   }
   ```

### Request 1: Get Low Stock Products

**Method:** GET  
**URL:** `{{base_url}}/inventory/low-stock-with-suppliers`  
**Headers:**
```
Authorization: Bearer {{token}}
```
**Query Params:**
- `status`: `out_of_stock` (optional)
- `warehouse_id`: `1` (optional)
- `skip`: `0` (optional)
- `limit`: `20` (optional)

### Request 2: Export Excel

**Method:** POST  
**URL:** `{{base_url}}/inventory/export/low-stock-by-supplier`  
**Headers:**
```
Authorization: Bearer {{token}}
Content-Type: application/json
```
**Body (raw JSON):**
```json
[
  {
    "product_id": 456,
    "sku": "ARD-UNO-001",
    "supplier_id": "sheet_45",
    "reorder_quantity": 30
  }
]
```
**Settings:**
- Send and Download
- Save response to file

---

## 🐍 Testing with Python

### Install Requirements
```bash
pip install requests
```

### Test Script

```python
import requests
import json

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "admin@magflow.com"
PASSWORD = "your_password"

# 1. Login and get token
def get_token():
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": USERNAME, "password": PASSWORD}
    )
    return response.json()["access_token"]

# 2. Get low stock products
def get_low_stock_products(token, status=None):
    headers = {"Authorization": f"Bearer {token}"}
    params = {}
    if status:
        params["status"] = status
    
    response = requests.get(
        f"{BASE_URL}/inventory/low-stock-with-suppliers",
        headers=headers,
        params=params
    )
    return response.json()

# 3. Export to Excel
def export_to_excel(token, selections):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{BASE_URL}/inventory/export/low-stock-by-supplier",
        headers=headers,
        json=selections
    )
    
    # Save Excel file
    with open("low_stock_export.xlsx", "wb") as f:
        f.write(response.content)
    
    return response.status_code

# Main test
if __name__ == "__main__":
    # Get token
    print("🔐 Logging in...")
    token = get_token()
    print(f"✅ Token obtained: {token[:20]}...")
    
    # Get low stock products
    print("\n📊 Fetching low stock products...")
    data = get_low_stock_products(token, status="out_of_stock")
    products = data["data"]["products"]
    print(f"✅ Found {len(products)} products")
    
    # Display first product with suppliers
    if products:
        product = products[0]
        print(f"\n📦 Product: {product['name']}")
        print(f"   SKU: {product['sku']}")
        print(f"   Stock: {product['available_quantity']}/{product['minimum_stock']}")
        print(f"   Suppliers: {product['supplier_count']}")
        
        for supplier in product['suppliers']:
            print(f"   - {supplier['supplier_name']}: {supplier['price']} {supplier['currency']}")
    
    # Export example
    if products and products[0]['suppliers']:
        print("\n📤 Exporting to Excel...")
        selections = [
            {
                "product_id": products[0]["product_id"],
                "sku": products[0]["sku"],
                "supplier_id": products[0]["suppliers"][0]["supplier_id"],
                "reorder_quantity": products[0]["reorder_quantity"]
            }
        ]
        
        status = export_to_excel(token, selections)
        if status == 200:
            print("✅ Excel file saved: low_stock_export.xlsx")
        else:
            print(f"❌ Export failed with status: {status}")
```

### Run the script
```bash
python test_low_stock_api.py
```

---

## 🔍 Testing Scenarios

### Scenario 1: Product with Multiple Suppliers

**Goal:** Verify that all suppliers are returned for a product

**Test:**
1. Create product with 3 suppliers
2. Call GET endpoint
3. Verify `supplier_count` = 3
4. Verify all 3 suppliers in `suppliers` array

**Expected:**
```json
{
  "supplier_count": 3,
  "suppliers": [
    {"supplier_id": "sheet_1", "price": 22.80},
    {"supplier_id": "sheet_2", "price": 24.50},
    {"supplier_id": "1688_3", "price": 21.00}
  ]
}
```

---

### Scenario 2: Product with No Suppliers

**Goal:** Verify handling of products without suppliers

**Test:**
1. Create product without suppliers
2. Call GET endpoint
3. Verify `supplier_count` = 0
4. Verify `suppliers` = []

**Expected:**
```json
{
  "supplier_count": 0,
  "suppliers": []
}
```

---

### Scenario 3: Export Multiple Suppliers

**Goal:** Verify Excel has separate sheets per supplier

**Test:**
1. Select 3 products from 2 different suppliers
2. Call POST export endpoint
3. Open Excel file
4. Verify 2 sheets exist
5. Verify products grouped correctly

**Expected Excel Structure:**
- Sheet 1: "Supplier A" with 2 products
- Sheet 2: "Supplier B" with 1 product

---

### Scenario 4: Filter by Status

**Goal:** Verify filtering works correctly

**Test:**
```bash
# Test out_of_stock filter
curl "http://localhost:8000/api/v1/inventory/low-stock-with-suppliers?status=out_of_stock"

# Verify all returned products have available_quantity = 0
```

---

### Scenario 5: Pagination

**Goal:** Verify pagination works correctly

**Test:**
```bash
# Page 1
curl "http://localhost:8000/api/v1/inventory/low-stock-with-suppliers?skip=0&limit=10"

# Page 2
curl "http://localhost:8000/api/v1/inventory/low-stock-with-suppliers?skip=10&limit=10"

# Verify different products returned
# Verify pagination.has_more is correct
```

---

## 🐛 Error Scenarios

### Error 1: Unauthorized (401)

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/inventory/low-stock-with-suppliers"
# No Authorization header
```

**Response:**
```json
{
  "detail": "Not authenticated"
}
```

---

### Error 2: Invalid Status Filter (422)

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/inventory/low-stock-with-suppliers?status=invalid_status"
```

**Response:**
```json
{
  "detail": "Invalid status filter"
}
```

---

### Error 3: Export with No Products (400)

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/inventory/export/low-stock-by-supplier" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '[]'
```

**Response:**
```json
{
  "detail": "No products selected for export"
}
```

---

### Error 4: Excel Library Not Installed (500)

**Response:**
```json
{
  "detail": "Excel export not available. Please install openpyxl"
}
```

**Fix:**
```bash
pip install openpyxl
```

---

## 📊 Performance Testing

### Load Test with Apache Bench

```bash
# Test GET endpoint
ab -n 100 -c 10 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/inventory/low-stock-with-suppliers

# Expected results:
# - Requests per second: > 50
# - Mean time per request: < 200ms
# - Failed requests: 0
```

### Load Test with Locust

```python
from locust import HttpUser, task, between

class LowStockUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Login
        response = self.client.post("/api/v1/auth/login", json={
            "username": "admin@magflow.com",
            "password": "password"
        })
        self.token = response.json()["access_token"]
    
    @task(3)
    def get_low_stock(self):
        self.client.get(
            "/api/v1/inventory/low-stock-with-suppliers",
            headers={"Authorization": f"Bearer {self.token}"}
        )
    
    @task(1)
    def export_excel(self):
        self.client.post(
            "/api/v1/inventory/export/low-stock-by-supplier",
            headers={"Authorization": f"Bearer {self.token}"},
            json=[{
                "product_id": 456,
                "sku": "TEST-001",
                "supplier_id": "sheet_1",
                "reorder_quantity": 10
            }]
        )
```

**Run:**
```bash
locust -f locustfile.py --host=http://localhost:8000
```

---

## ✅ Test Checklist

- [ ] Authentication works
- [ ] GET endpoint returns products
- [ ] Suppliers are included for each product
- [ ] Filtering by status works
- [ ] Filtering by warehouse works
- [ ] Pagination works correctly
- [ ] Export endpoint creates Excel file
- [ ] Excel has correct sheets per supplier
- [ ] Excel formatting is correct
- [ ] Error handling works (401, 400, 500)
- [ ] Performance is acceptable (< 200ms)
- [ ] No memory leaks with large exports

---

## 📞 Support

If tests fail:
1. Check backend logs: `docker logs magflow-backend`
2. Check database connection
3. Verify openpyxl is installed
4. Check authentication token is valid
5. Verify test data exists in database

---

**Last Updated:** 2025-10-10  
**Version:** 1.0.0
