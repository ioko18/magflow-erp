#!/bin/bash

echo "=== Testing eMAG Inventory Endpoints ==="
echo ""

# Login and get token
echo "1. Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST 'http://localhost:8000/api/v1/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin@example.com","password":"admin123","remember_me":false}')

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token // empty')

if [ -z "$TOKEN" ]; then
  echo "❌ Login failed"
  exit 1
fi

echo "✓ Login successful"
echo ""

# Test statistics endpoint
echo "2. Testing /api/v1/emag-inventory/statistics..."
STATS_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  'http://localhost:8000/api/v1/emag-inventory/statistics')

HTTP_CODE=$(echo "$STATS_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$STATS_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" = "200" ]; then
  echo "✓ Statistics endpoint working (HTTP $HTTP_CODE)"
  echo "$BODY" | jq '.data | {total_products, low_stock_count, out_of_stock_count}'
else
  echo "❌ Statistics endpoint failed (HTTP $HTTP_CODE)"
  echo "$BODY" | jq '.'
fi
echo ""

# Test low-stock endpoint
echo "3. Testing /api/v1/emag-inventory/low-stock..."
LOW_STOCK_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  'http://localhost:8000/api/v1/emag-inventory/low-stock?skip=0&limit=5&group_by_sku=true')

HTTP_CODE=$(echo "$LOW_STOCK_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$LOW_STOCK_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" = "200" ]; then
  echo "✓ Low stock endpoint working (HTTP $HTTP_CODE)"
  echo "$BODY" | jq '.data.pagination'
else
  echo "❌ Low stock endpoint failed (HTTP $HTTP_CODE)"
  echo "$BODY" | jq '.'
fi
echo ""

# Test stock-alerts endpoint
echo "4. Testing /api/v1/emag-inventory/stock-alerts..."
ALERTS_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  'http://localhost:8000/api/v1/emag-inventory/stock-alerts?limit=5')

HTTP_CODE=$(echo "$ALERTS_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$ALERTS_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" = "200" ]; then
  echo "✓ Stock alerts endpoint working (HTTP $HTTP_CODE)"
  echo "$BODY" | jq '.data.count'
else
  echo "❌ Stock alerts endpoint failed (HTTP $HTTP_CODE)"
  echo "$BODY" | jq '.'
fi
echo ""

echo "=== Test Complete ==="
