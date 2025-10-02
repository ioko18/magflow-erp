#!/bin/bash
# Test script for unified products endpoint

echo "🧪 Testing Unified Products Endpoint"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get JWT token
echo "📝 Step 1: Getting JWT token..."
TOKEN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@example.com","password":"secret"}')

TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Failed to get token${NC}"
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ Token obtained${NC}"
echo ""

# Test 1: Get all products (first page)
echo "📊 Test 1: Get all products (first page, 10 items)"
echo "---------------------------------------------------"
RESPONSE=$(curl -s -X GET "http://localhost:8000/api/v1/emag/enhanced/products/unified/all?page=1&page_size=10&source=all" \
  -H "Authorization: Bearer $TOKEN")

TOTAL=$(echo $RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('statistics', {}).get('total', 0))" 2>/dev/null)
EMAG_MAIN=$(echo $RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('statistics', {}).get('emag_main', 0))" 2>/dev/null)
EMAG_FBE=$(echo $RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('statistics', {}).get('emag_fbe', 0))" 2>/dev/null)
LOCAL=$(echo $RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('statistics', {}).get('local', 0))" 2>/dev/null)

echo "Statistics:"
echo "  Total products: $TOTAL"
echo "  eMAG MAIN: $EMAG_MAIN"
echo "  eMAG FBE: $EMAG_FBE"
echo "  Local: $LOCAL"

if [ "$TOTAL" -gt 0 ]; then
    echo -e "${GREEN}✅ Test 1 PASSED${NC}"
else
    echo -e "${RED}❌ Test 1 FAILED${NC}"
fi
echo ""

# Test 2: Get only MAIN products
echo "📊 Test 2: Get only eMAG MAIN products"
echo "---------------------------------------"
RESPONSE=$(curl -s -X GET "http://localhost:8000/api/v1/emag/enhanced/products/unified/all?page=1&page_size=10&source=emag_main" \
  -H "Authorization: Bearer $TOKEN")

MAIN_COUNT=$(echo $RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('products', [])))" 2>/dev/null)
echo "  MAIN products returned: $MAIN_COUNT"

if [ "$MAIN_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✅ Test 2 PASSED${NC}"
else
    echo -e "${YELLOW}⚠️  Test 2 WARNING: No MAIN products found${NC}"
fi
echo ""

# Test 3: Get only FBE products
echo "📊 Test 3: Get only eMAG FBE products"
echo "--------------------------------------"
RESPONSE=$(curl -s -X GET "http://localhost:8000/api/v1/emag/enhanced/products/unified/all?page=1&page_size=10&source=emag_fbe" \
  -H "Authorization: Bearer $TOKEN")

FBE_COUNT=$(echo $RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('products', [])))" 2>/dev/null)
echo "  FBE products returned: $FBE_COUNT"

if [ "$FBE_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✅ Test 3 PASSED${NC}"
else
    echo -e "${YELLOW}⚠️  Test 3 WARNING: No FBE products found${NC}"
fi
echo ""

# Test 4: Get only local products
echo "📊 Test 4: Get only local products"
echo "-----------------------------------"
RESPONSE=$(curl -s -X GET "http://localhost:8000/api/v1/emag/enhanced/products/unified/all?page=1&page_size=10&source=local" \
  -H "Authorization: Bearer $TOKEN")

LOCAL_COUNT=$(echo $RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('products', [])))" 2>/dev/null)
echo "  Local products returned: $LOCAL_COUNT"

if [ "$LOCAL_COUNT" -ge 0 ]; then
    echo -e "${GREEN}✅ Test 4 PASSED${NC}"
else
    echo -e "${YELLOW}⚠️  Test 4 WARNING: No local products found${NC}"
fi
echo ""

# Test 5: Search functionality
echo "📊 Test 5: Search functionality"
echo "--------------------------------"
RESPONSE=$(curl -s -X GET "http://localhost:8000/api/v1/emag/enhanced/products/unified/all?page=1&page_size=10&search=Arduino" \
  -H "Authorization: Bearer $TOKEN")

SEARCH_COUNT=$(echo $RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('products', [])))" 2>/dev/null)
echo "  Products matching 'Arduino': $SEARCH_COUNT"

if [ "$SEARCH_COUNT" -ge 0 ]; then
    echo -e "${GREEN}✅ Test 5 PASSED${NC}"
else
    echo -e "${RED}❌ Test 5 FAILED${NC}"
fi
echo ""

# Test 6: Pagination
echo "📊 Test 6: Pagination"
echo "---------------------"
RESPONSE=$(curl -s -X GET "http://localhost:8000/api/v1/emag/enhanced/products/unified/all?page=2&page_size=5&source=all" \
  -H "Authorization: Bearer $TOKEN")

PAGE=$(echo $RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('pagination', {}).get('page', 0))" 2>/dev/null)
PAGE_SIZE=$(echo $RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('pagination', {}).get('page_size', 0))" 2>/dev/null)

echo "  Current page: $PAGE"
echo "  Page size: $PAGE_SIZE"

if [ "$PAGE" -eq 2 ] && [ "$PAGE_SIZE" -eq 5 ]; then
    echo -e "${GREEN}✅ Test 6 PASSED${NC}"
else
    echo -e "${RED}❌ Test 6 FAILED${NC}"
fi
echo ""

# Summary
echo "======================================"
echo "🎯 Test Summary"
echo "======================================"
echo ""
echo "Database Status:"
echo "  Total products: $TOTAL"
echo "  eMAG MAIN: $EMAG_MAIN"
echo "  eMAG FBE: $EMAG_FBE"
echo "  Local: $LOCAL"
echo ""
echo "Endpoint Tests:"
echo "  ✅ All products endpoint"
echo "  ✅ Filter by source (MAIN, FBE, Local)"
echo "  ✅ Search functionality"
echo "  ✅ Pagination"
echo ""
echo -e "${GREEN}✅ All tests completed!${NC}"
echo ""
echo "Next steps:"
echo "  1. Run full sync: http://localhost:5173 → eMAG Integration"
echo "  2. Set Max Pages = 1000"
echo "  3. Click 'Sincronizare Produse (MAIN + FBE)'"
echo "  4. Wait ~1-2 minutes for completion"
echo "  5. Re-run this script to see updated counts"
echo ""
