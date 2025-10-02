#!/bin/bash

# Test eMAG Product Sync V2
# This script tests the synchronization endpoints

set -e

echo "🔐 Step 1: Login to get JWT token..."
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@example.com","password":"secret"}')

TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo "")

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to get token. Response:"
  echo $LOGIN_RESPONSE
  exit 1
fi

echo "✅ Got JWT token"

echo ""
echo "📊 Step 2: Get current statistics..."
STATS=$(curl -s -X GET http://localhost:8000/api/v1/emag/products/statistics \
  -H "Authorization: Bearer $TOKEN")
echo $STATS | python3 -m json.tool

echo ""
echo "🔍 Step 3: Check sync status..."
STATUS=$(curl -s -X GET http://localhost:8000/api/v1/emag/products/status \
  -H "Authorization: Bearer $TOKEN")
echo $STATUS | python3 -m json.tool

echo ""
echo "🧪 Step 4: Test connection to MAIN account..."
TEST_MAIN=$(curl -s -X POST "http://localhost:8000/api/v1/emag/products/test-connection?account_type=main" \
  -H "Authorization: Bearer $TOKEN")
echo $TEST_MAIN | python3 -m json.tool

echo ""
echo "🧪 Step 5: Test connection to FBE account..."
TEST_FBE=$(curl -s -X POST "http://localhost:8000/api/v1/emag/products/test-connection?account_type=fbe" \
  -H "Authorization: Bearer $TOKEN")
echo $TEST_FBE | python3 -m json.tool

echo ""
echo "🚀 Step 6: Start sync for MAIN account (async)..."
SYNC_MAIN=$(curl -s -X POST http://localhost:8000/api/v1/emag/products/sync \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_type": "main",
    "mode": "incremental",
    "max_pages": 2,
    "items_per_page": 100,
    "include_inactive": true,
    "conflict_strategy": "emag_priority",
    "run_async": true
  }')
echo $SYNC_MAIN | python3 -m json.tool

echo ""
echo "⏳ Waiting 5 seconds for sync to start..."
sleep 5

echo ""
echo "📊 Step 7: Check sync status again..."
STATUS=$(curl -s -X GET http://localhost:8000/api/v1/emag/products/status \
  -H "Authorization: Bearer $TOKEN")
echo $STATUS | python3 -m json.tool

echo ""
echo "✅ Test completed! Check the output above for any errors."
