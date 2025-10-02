#!/bin/bash

# Test script for eMAG API v4.4.9 improvements
# Tests all new endpoints and verifies functionality

set -e

echo "=========================================="
echo "eMAG API v4.4.9 Improvements Test Suite"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="http://localhost:8000"
API_VERSION="v1"

# Function to get JWT token
get_token() {
    curl -s -X POST "${BASE_URL}/api/${API_VERSION}/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"username":"admin@example.com","password":"secret"}' \
        | python3 -c 'import sys, json; print(json.load(sys.stdin)["access_token"])'
}

# Function to test endpoint
test_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local data=$4
    local expected_status=${5:-200}
    
    echo -n "Testing ${name}... "
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "${BASE_URL}/api/${API_VERSION}${endpoint}" \
            -H "Authorization: Bearer $TOKEN")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "${BASE_URL}/api/${API_VERSION}${endpoint}" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi
    
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$status_code" -eq "$expected_status" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $status_code)"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $status_code, expected $expected_status)"
        echo "Response: $body"
        return 1
    fi
}

# Get authentication token
echo "Step 1: Authenticating..."
TOKEN=$(get_token)
if [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ Authentication failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Authentication successful${NC}"
echo ""

# Test counters
TOTAL=0
PASSED=0
FAILED=0

echo "=========================================="
echo "Testing Fixed Endpoints"
echo "=========================================="
echo ""

# Test 1: Categories endpoint (fixed)
TOTAL=$((TOTAL + 1))
if test_endpoint "Categories List" "GET" "/categories"; then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
fi
echo ""

echo "=========================================="
echo "Testing New eMAG v4.4.9 Endpoints"
echo "=========================================="
echo ""

# Test 2: VAT Rates
TOTAL=$((TOTAL + 1))
if test_endpoint "VAT Rates (MAIN)" "GET" "/emag/advanced/vat-rates?account_type=main"; then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 3: Handling Times
TOTAL=$((TOTAL + 1))
if test_endpoint "Handling Times (MAIN)" "GET" "/emag/advanced/handling-times?account_type=main"; then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 4: EAN Matching
TOTAL=$((TOTAL + 1))
EAN_DATA='{"eans": ["5904862975146"], "account_type": "main"}'
if test_endpoint "EAN Matching" "POST" "/emag/advanced/products/find-by-eans" "$EAN_DATA"; then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 5: Categories (eMAG)
TOTAL=$((TOTAL + 1))
if test_endpoint "eMAG Categories" "GET" "/emag/advanced/categories?account_type=main&page=1&items_per_page=10"; then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 6: Light Offer API (will fail if product doesn't exist, but tests endpoint)
TOTAL=$((TOTAL + 1))
OFFER_DATA='{"product_id": 999999, "account_type": "main", "sale_price": 99.99, "stock_value": 10}'
echo -n "Testing Light Offer API (expected to fail for non-existent product)... "
response=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/api/${API_VERSION}/emag/advanced/offers/update-light" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$OFFER_DATA")
status_code=$(echo "$response" | tail -n1)
if [ "$status_code" -eq "200" ] || [ "$status_code" -eq "400" ]; then
    echo -e "${GREEN}✓ PASS${NC} (HTTP $status_code - endpoint accessible)"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC} (HTTP $status_code)"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 7: Measurements API (will fail if product doesn't exist, but tests endpoint)
TOTAL=$((TOTAL + 1))
MEASUREMENTS_DATA='{"product_id": 999999, "account_type": "main", "length": 100.0, "width": 50.0, "height": 30.0, "weight": 500.0}'
echo -n "Testing Measurements API (expected to fail for non-existent product)... "
response=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/api/${API_VERSION}/emag/advanced/products/measurements" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$MEASUREMENTS_DATA")
status_code=$(echo "$response" | tail -n1)
if [ "$status_code" -eq "200" ] || [ "$status_code" -eq "400" ]; then
    echo -e "${GREEN}✓ PASS${NC} (HTTP $status_code - endpoint accessible)"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC} (HTTP $status_code)"
    FAILED=$((FAILED + 1))
fi
echo ""

echo "=========================================="
echo "Testing Existing eMAG Endpoints"
echo "=========================================="
echo ""

# Test 8: Enhanced Products List
TOTAL=$((TOTAL + 1))
if test_endpoint "Enhanced Products List" "GET" "/emag/enhanced/products/all?skip=0&limit=10"; then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 9: Enhanced Status
TOTAL=$((TOTAL + 1))
if test_endpoint "Enhanced Status" "GET" "/emag/enhanced/status"; then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
fi
echo ""

echo "=========================================="
echo "Test Results Summary"
echo "=========================================="
echo ""
echo "Total Tests: $TOTAL"
echo -e "${GREEN}Passed: $PASSED${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Failed: $FAILED${NC}"
else
    echo -e "${GREEN}Failed: $FAILED${NC}"
fi
echo ""

# Calculate success rate
SUCCESS_RATE=$((PASSED * 100 / TOTAL))
echo "Success Rate: ${SUCCESS_RATE}%"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}=========================================="
    echo "✓ ALL TESTS PASSED!"
    echo -e "==========================================${NC}"
    exit 0
else
    echo -e "${YELLOW}=========================================="
    echo "⚠ SOME TESTS FAILED"
    echo -e "==========================================${NC}"
    exit 1
fi
