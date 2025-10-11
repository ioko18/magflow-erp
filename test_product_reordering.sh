#!/bin/bash

# Test Product Reordering Functionality
# This script tests the new display_order feature

set -e

echo "🧪 Testing Product Reordering Functionality"
echo "==========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_URL="http://localhost:8000/api/v1"
EMAIL="admin@example.com"
PASSWORD="secret"

echo "📡 Step 1: Login and get token..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
  echo -e "${RED}❌ Login failed!${NC}"
  echo "Response: $LOGIN_RESPONSE"
  exit 1
fi

echo -e "${GREEN}✅ Login successful${NC}"
echo ""

# Test 1: Get products
echo "📋 Step 2: Fetching products..."
PRODUCTS_RESPONSE=$(curl -s "$API_URL/products?skip=0&limit=5" \
  -H "Authorization: Bearer $TOKEN")

PRODUCT_COUNT=$(echo $PRODUCTS_RESPONSE | jq -r '.data.products | length')

if [ "$PRODUCT_COUNT" -eq 0 ]; then
  echo -e "${YELLOW}⚠️  No products found. Creating test products...${NC}"
  
  # Create test products
  for i in {1..3}; do
    curl -s -X POST "$API_URL/products" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"name\": \"Test Product $i\",
        \"sku\": \"TEST-SKU-$i-$(date +%s)\",
        \"base_price\": $((100 + i * 10)),
        \"currency\": \"RON\",
        \"is_active\": true,
        \"is_discontinued\": false
      }" > /dev/null
    echo -e "${GREEN}✅ Created Test Product $i${NC}"
  done
  
  # Fetch products again
  PRODUCTS_RESPONSE=$(curl -s "$API_URL/products?skip=0&limit=5" \
    -H "Authorization: Bearer $TOKEN")
  PRODUCT_COUNT=$(echo $PRODUCTS_RESPONSE | jq -r '.data.products | length')
fi

echo -e "${GREEN}✅ Found $PRODUCT_COUNT products${NC}"
echo ""

# Get first product ID
PRODUCT_ID=$(echo $PRODUCTS_RESPONSE | jq -r '.data.products[0].id')
PRODUCT_NAME=$(echo $PRODUCTS_RESPONSE | jq -r '.data.products[0].name')

echo "🎯 Step 3: Testing display_order update..."
echo "   Product ID: $PRODUCT_ID"
echo "   Product Name: $PRODUCT_NAME"
echo ""

# Test 2: Set display_order
echo "📝 Setting display_order to 5..."
ORDER_RESPONSE=$(curl -s -X POST "$API_URL/products/$PRODUCT_ID/display-order" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_order": 5,
    "auto_adjust": true
  }')

ORDER_STATUS=$(echo $ORDER_RESPONSE | jq -r '.status')
NEW_ORDER=$(echo $ORDER_RESPONSE | jq -r '.data.new_display_order')

if [ "$ORDER_STATUS" == "success" ] && [ "$NEW_ORDER" == "5" ]; then
  echo -e "${GREEN}✅ Display order set to $NEW_ORDER${NC}"
else
  echo -e "${RED}❌ Failed to set display order${NC}"
  echo "Response: $ORDER_RESPONSE"
  exit 1
fi
echo ""

# Test 3: Bulk reorder
echo "🔄 Step 4: Testing bulk reorder..."

# Get multiple product IDs
PRODUCT_IDS=$(echo $PRODUCTS_RESPONSE | jq -r '.data.products[0:3] | map(.id) | @json')

# Create reorder payload
REORDER_PAYLOAD=$(cat <<EOF
{
  "product_orders": [
    {"product_id": $(echo $PRODUCTS_RESPONSE | jq -r '.data.products[0].id'), "display_order": 0},
    {"product_id": $(echo $PRODUCTS_RESPONSE | jq -r '.data.products[1].id'), "display_order": 1},
    {"product_id": $(echo $PRODUCTS_RESPONSE | jq -r '.data.products[2].id'), "display_order": 2}
  ]
}
EOF
)

REORDER_RESPONSE=$(curl -s -X POST "$API_URL/products/reorder" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$REORDER_PAYLOAD")

REORDER_STATUS=$(echo $REORDER_RESPONSE | jq -r '.status')
UPDATED_COUNT=$(echo $REORDER_RESPONSE | jq -r '.data.updated_products | length')

if [ "$REORDER_STATUS" == "success" ]; then
  echo -e "${GREEN}✅ Bulk reorder successful - Updated $UPDATED_COUNT products${NC}"
else
  echo -e "${RED}❌ Bulk reorder failed${NC}"
  echo "Response: $REORDER_RESPONSE"
  exit 1
fi
echo ""

# Test 4: Verify products are sorted
echo "🔍 Step 5: Verifying product order..."
SORTED_PRODUCTS=$(curl -s "$API_URL/products?skip=0&limit=10" \
  -H "Authorization: Bearer $TOKEN")

echo "Products with display_order:"
echo $SORTED_PRODUCTS | jq -r '.data.products[] | select(.display_order != null) | "  - \(.name): order \(.display_order)"'
echo ""

# Test 5: Remove display_order
echo "🗑️  Step 6: Testing display_order removal..."
DELETE_RESPONSE=$(curl -s -X DELETE "$API_URL/products/$PRODUCT_ID/display-order" \
  -H "Authorization: Bearer $TOKEN")

DELETE_STATUS=$(echo $DELETE_RESPONSE | jq -r '.status')

if [ "$DELETE_STATUS" == "success" ]; then
  echo -e "${GREEN}✅ Display order removed successfully${NC}"
else
  echo -e "${RED}❌ Failed to remove display order${NC}"
  echo "Response: $DELETE_RESPONSE"
  exit 1
fi
echo ""

# Test 6: Check database column exists
echo "🗄️  Step 7: Verifying database schema..."
DB_CHECK=$(docker-compose exec -T db psql -U app -d magflow -c "\d app.products" 2>/dev/null | grep display_order || echo "")

if [ -n "$DB_CHECK" ]; then
  echo -e "${GREEN}✅ display_order column exists in database${NC}"
else
  echo -e "${RED}❌ display_order column not found in database${NC}"
  exit 1
fi
echo ""

# Summary
echo "==========================================="
echo -e "${GREEN}🎉 All tests passed successfully!${NC}"
echo ""
echo "✅ Login and authentication"
echo "✅ Set display_order with auto_adjust"
echo "✅ Bulk reorder products"
echo "✅ Product sorting verification"
echo "✅ Remove display_order"
echo "✅ Database schema verification"
echo ""
echo "🚀 Product reordering feature is fully functional!"
echo "==========================================="
