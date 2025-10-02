#!/bin/bash

# Script pentru sincronizare completă a tuturor produselor

echo "🚀 Sincronizare COMPLETĂ - TOATE produsele (MAIN + FBE)"
echo "=================================================="
echo ""

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@example.com","password":"secret"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to get token"
  exit 1
fi

echo "✅ Autentificat cu succes"
echo ""

# Start sync
echo "🚀 Pornesc sincronizarea..."
SYNC_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/emag/products/sync \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_type":"both",
    "mode":"full",
    "max_pages":null,
    "items_per_page":100,
    "include_inactive":true,
    "conflict_strategy":"emag_priority",
    "run_async":false
  }')

echo "$SYNC_RESPONSE" | python3 -m json.tool

echo ""
echo "📊 Verificare finală..."
sleep 2

# Get statistics
STATS=$(curl -s -X GET http://localhost:8000/api/v1/emag/products/statistics \
  -H "Authorization: Bearer $TOKEN")

echo "$STATS" | python3 -m json.tool

echo ""
echo "✅ Sincronizare completă finalizată!"
