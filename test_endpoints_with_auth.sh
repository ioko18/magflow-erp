#!/bin/bash

# Test script to verify the API endpoints are working

echo "=== Testing API Endpoints ==="
echo ""

# Test health endpoint
echo "1. Testing health endpoint..."
curl -s http://localhost:8000/health | jq '.' || echo "Health check failed"
echo ""

# Login and get token
echo "2. Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST 'http://localhost:8000/api/v1/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin@example.com","password":"admin123","remember_me":false}')

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token // empty')

if [ -z "$TOKEN" ]; then
  echo "❌ Login failed"
  echo "Response: $LOGIN_RESPONSE"
  exit 1
fi

echo "✓ Login successful"
echo ""

# Test suppliers endpoint
echo "3. Testing suppliers endpoint..."
SUPPLIERS_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  'http://localhost:8000/api/v1/suppliers?limit=5&active_only=false')

HTTP_CODE=$(echo "$SUPPLIERS_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$SUPPLIERS_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" = "200" ]; then
  echo "✓ Suppliers endpoint working (HTTP $HTTP_CODE)"
  echo "$BODY" | jq '.data.suppliers | length' | xargs echo "  Found suppliers:"
else
  echo "❌ Suppliers endpoint failed (HTTP $HTTP_CODE)"
  echo "$BODY" | jq '.'
fi
echo ""

# Test products endpoint
echo "4. Testing products endpoint..."
PRODUCTS_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  'http://localhost:8000/api/v1/products?skip=0&limit=5')

HTTP_CODE=$(echo "$PRODUCTS_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$PRODUCTS_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" = "200" ]; then
  echo "✓ Products endpoint working (HTTP $HTTP_CODE)"
  echo "$BODY" | jq '.data.products | length' | xargs echo "  Found products:"
else
  echo "❌ Products endpoint failed (HTTP $HTTP_CODE)"
  echo "$BODY" | jq '.'
fi
echo ""

echo "=== Test Complete ==="
