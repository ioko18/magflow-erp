#!/bin/bash
# Test Script - Google Sheets Import Fix
# Data: 15 Octombrie 2025

echo "🧪 Testing Google Sheets Import Fix..."
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check Backend
echo "1️⃣  Checking Backend (Docker)..."
if docker ps | grep -q magflow_app; then
    echo -e "${GREEN}✅ Backend is running${NC}"
else
    echo -e "${RED}❌ Backend is NOT running${NC}"
    echo "   Run: docker-compose up -d"
    exit 1
fi
echo ""

# Test 2: Check Backend Health
echo "2️⃣  Checking Backend Health..."
HEALTH=$(curl -s http://localhost:8000/api/v1/health)
if echo "$HEALTH" | grep -q '"status":"ok"'; then
    echo -e "${GREEN}✅ Backend is healthy${NC}"
    echo "   Response: $HEALTH"
else
    echo -e "${RED}❌ Backend health check failed${NC}"
    echo "   Response: $HEALTH"
    exit 1
fi
echo ""

# Test 3: Check service_account.json
echo "3️⃣  Checking service_account.json..."
if docker exec magflow_app test -f /app/service_account.json; then
    SIZE=$(docker exec magflow_app stat -f%z /app/service_account.json 2>/dev/null || docker exec magflow_app stat -c%s /app/service_account.json)
    echo -e "${GREEN}✅ service_account.json exists${NC}"
    echo "   Size: $SIZE bytes"
else
    echo -e "${RED}❌ service_account.json NOT found${NC}"
    exit 1
fi
echo ""

# Test 4: Login and Get Token
echo "4️⃣  Testing Authentication..."
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@magflow.local","password":"secret"}' \
  | jq -r '.access_token')

if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
    echo -e "${GREEN}✅ Authentication successful${NC}"
    echo "   Token: ${TOKEN:0:20}..."
else
    echo -e "${RED}❌ Authentication failed${NC}"
    echo "   Check credentials: admin@magflow.local / secret"
    exit 1
fi
echo ""

# Test 5: Test Google Sheets Connection
echo "5️⃣  Testing Google Sheets Connection..."
CONNECTION=$(curl -s http://localhost:8000/api/v1/products/import/sheets/test-connection \
  -H "Authorization: Bearer $TOKEN")

if echo "$CONNECTION" | grep -q '"status":"connected"'; then
    echo -e "${GREEN}✅ Google Sheets connection successful${NC}"
    echo "   $(echo $CONNECTION | jq -r '.message')"
    
    # Show statistics
    TOTAL_PRODUCTS=$(echo $CONNECTION | jq -r '.statistics.total_products // 0')
    TOTAL_SUPPLIERS=$(echo $CONNECTION | jq -r '.statistics.total_suppliers // 0')
    echo "   📊 Products: $TOTAL_PRODUCTS"
    echo "   📊 Suppliers: $TOTAL_SUPPLIERS"
else
    echo -e "${RED}❌ Google Sheets connection failed${NC}"
    echo "   Response: $CONNECTION"
    exit 1
fi
echo ""

# Test 6: Check Frontend (optional)
echo "6️⃣  Checking Frontend..."
if curl -s -I http://localhost:5173 | grep -q "200 OK"; then
    echo -e "${GREEN}✅ Frontend is running${NC}"
    echo "   URL: http://localhost:5173"
else
    echo -e "${YELLOW}⚠️  Frontend is NOT running${NC}"
    echo "   Run: cd admin-frontend && npm run dev"
fi
echo ""

# Test 7: Small Import Test (optional - commented out by default)
echo "7️⃣  Import Test (Optional)..."
echo -e "${YELLOW}⚠️  Skipping full import test (takes 1-3 minutes)${NC}"
echo "   To test import manually:"
echo "   1. Open: http://localhost:5173/login"
echo "   2. Login: admin@magflow.local / secret"
echo "   3. Navigate to: Products → Import from Google Sheets"
echo "   4. Click: Import Products & Suppliers"
echo "   5. Wait for completion (1-3 minutes)"
echo ""

# Summary
echo "========================================"
echo "📋 Test Summary"
echo "========================================"
echo -e "${GREEN}✅ Backend: Running and healthy${NC}"
echo -e "${GREEN}✅ service_account.json: Present${NC}"
echo -e "${GREEN}✅ Authentication: Working${NC}"
echo -e "${GREEN}✅ Google Sheets: Connected${NC}"
echo ""
echo "🎉 All critical tests passed!"
echo ""
echo "📝 Next Steps:"
echo "   1. Restart frontend: cd admin-frontend && npm run dev"
echo "   2. Open browser: http://localhost:5173"
echo "   3. Login: admin@magflow.local / secret"
echo "   4. Test import: Products → Import from Google Sheets"
echo ""
echo "📚 Documentation:"
echo "   - GOOGLE_SHEETS_IMPORT_FIX_FINAL_2025_10_15.md"
echo "   - GOOGLE_SHEETS_IMPORT_IMPROVEMENTS_2025_10_15.md"
echo ""
