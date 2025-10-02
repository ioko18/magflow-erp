#!/bin/bash

# Test eMAG Product Sync V2 - BOTH accounts
echo "🚀 Testing BOTH accounts sync (MAIN + FBE)..."

# Login
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@example.com","password":"secret"}')

TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo "")

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to get token"
  exit 1
fi

echo "✅ Got JWT token"

echo ""
echo "🚀 Starting sync for BOTH accounts (MAIN + FBE)..."
SYNC_BOTH=$(curl -s -X POST http://localhost:8000/api/v1/emag/products/sync \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_type": "both",
    "mode": "incremental",
    "max_pages": 2,
    "items_per_page": 100,
    "include_inactive": true,
    "conflict_strategy": "emag_priority",
    "run_async": true
  }')

echo $SYNC_BOTH | python3 -m json.tool

echo ""
echo "⏳ Waiting 3 seconds..."
sleep 3

echo ""
echo "📊 Checking status..."
STATUS=$(curl -s -X GET http://localhost:8000/api/v1/emag/products/status \
  -H "Authorization: Bearer $TOKEN")
echo $STATUS | python3 -m json.tool | head -50

echo ""
echo "⏳ Waiting 10 more seconds for sync to complete..."
sleep 10

echo ""
echo "📊 Final status check..."
STATUS=$(curl -s -X GET http://localhost:8000/api/v1/emag/products/status \
  -H "Authorization: Bearer $TOKEN")
echo $STATUS | python3 -m json.tool | head -80

echo ""
echo "📊 Getting statistics..."
STATS=$(curl -s -X GET http://localhost:8000/api/v1/emag/products/statistics \
  -H "Authorization: Bearer $TOKEN")
echo $STATS | python3 -m json.tool

echo ""
echo "✅ Test completed!"
