#!/bin/bash
# Sincronizare REALĂ din eMag API

set -e

echo "🚀 Sincronizare REALĂ din eMag API"
echo "=" | tr '=' '=' | head -c 60; echo

# Get admin token
echo "🔐 Obținere token autentificare..."
TOKEN=$(docker exec magflow_db psql -U app -d magflow -t -c "
SELECT access_token 
FROM app.users 
WHERE email = 'admin@magflow.ro' 
LIMIT 1;
" | tr -d ' ')

if [ -z "$TOKEN" ]; then
    echo "❌ Nu s-a putut obține token-ul admin"
    exit 1
fi

echo "✅ Token obținut"
echo ""

# Sync products from eMag API
echo "📦 Sincronizare produse din eMag FBE API..."
echo "Acest proces poate dura câteva minute..."
echo ""

RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/emag/sync/products?account_type=fbe&full_sync=false&async_mode=false" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")

echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"

echo ""
echo "=" | tr '=' '=' | head -c 60; echo

# Check results
echo ""
echo "📊 Verificare rezultate sincronizare..."
docker exec magflow_db psql -U app -d magflow -c "
SELECT 
    'eMag Products' as table_name,
    COUNT(*) as total
FROM app.emag_products
UNION ALL
SELECT 
    'eMag FBE Offers',
    COUNT(*)
FROM app.emag_product_offers
WHERE account_type = 'fbe';
"

echo ""
echo "✅ Sincronizare eMag completă!"
echo "Acum rulează: docker exec -i magflow_db psql -U app -d magflow < scripts/sql/sync_emag_fbe_to_inventory.sql"
