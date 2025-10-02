# Instrucțiuni de Setup - Sincronizare Produse eMAG

## 🎯 Pași de Implementare

### Pas 1: Verificare Configurare Existentă ✅

Credențialele sunt deja configurate în `.env`:

```bash
# MAIN Account
EMAG_MAIN_USERNAME=galactronice@yahoo.com
EMAG_MAIN_PASSWORD=NB1WXDm

# FBE Account
EMAG_FBE_USERNAME=galactronice.fbe@yahoo.com
EMAG_FBE_PASSWORD=GB6on54
```

### Pas 2: Activare Sincronizare Automată

Adăugați în `.env` (dacă nu există deja):

```bash
# Activare sincronizare automată
EMAG_ENABLE_SCHEDULED_SYNC=true

# Interval sincronizare (în minute)
EMAG_SYNC_INTERVAL_MINUTES=60

# Retenție loguri (în zile)
EMAG_MAIN_LOG_RETENTION=30
```

### Pas 3: Test Conexiune API

```bash
# Autentificare (obțineți token)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "secret"
  }'

# Salvați token-ul primit
export TOKEN="your_access_token_here"

# Test conexiune MAIN
curl -X POST "http://localhost:8000/api/v1/emag/products/test-connection?account_type=main" \
  -H "Authorization: Bearer $TOKEN"

# Test conexiune FBE
curl -X POST "http://localhost:8000/api/v1/emag/products/test-connection?account_type=fbe" \
  -H "Authorization: Bearer $TOKEN"
```

### Pas 4: Sincronizare Inițială

```bash
# Sincronizare completă (ambele conturi) - în background
curl -X POST http://localhost:8000/api/v1/emag/products/sync \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_type": "both",
    "mode": "full",
    "run_async": true,
    "conflict_strategy": "emag_priority"
  }'
```

### Pas 5: Monitorizare Progres

```bash
# Verificare status sincronizare
curl -X GET http://localhost:8000/api/v1/emag/products/status \
  -H "Authorization: Bearer $TOKEN" | jq

# Monitorizare continuă (refresh la 10 secunde)
watch -n 10 'curl -s http://localhost:8000/api/v1/emag/products/status \
  -H "Authorization: Bearer $TOKEN" | jq'
```

### Pas 6: Verificare Rezultate

```bash
# Statistici sincronizare
curl -X GET http://localhost:8000/api/v1/emag/products/statistics \
  -H "Authorization: Bearer $TOKEN" | jq

# Primele 10 produse sincronizate
curl -X GET "http://localhost:8000/api/v1/emag/products/products?limit=10" \
  -H "Authorization: Bearer $TOKEN" | jq

# Verificare în database
docker exec -it magflow_db psql -U app -d magflow -c "
SELECT 
    account_type,
    COUNT(*) as total_products,
    COUNT(*) FILTER (WHERE is_active = true) as active_products,
    MAX(last_synced_at) as last_sync
FROM emag_products_v2
GROUP BY account_type;
"
```

### Pas 7: Pornire Celery pentru Sincronizare Automată

```bash
# În terminal separat - pornire Celery worker
celery -A app.core.celery worker --loglevel=info

# În alt terminal - pornire Celery beat (scheduler)
celery -A app.core.celery beat --loglevel=info

# SAU ambele împreună
celery -A app.core.celery worker --beat --loglevel=info
```

## 📋 Verificare Finală

### Checklist
- [ ] Credențiale configurate în `.env`
- [ ] Test conexiune API reușit (MAIN)
- [ ] Test conexiune API reușit (FBE)
- [ ] Sincronizare inițială completă
- [ ] Produse vizibile în database
- [ ] Celery worker pornit
- [ ] Celery beat pornit
- [ ] Sincronizare automată activată

### Comenzi Utile

```bash
# Istoric sincronizări
curl -X GET "http://localhost:8000/api/v1/emag/products/history?limit=10" \
  -H "Authorization: Bearer $TOKEN" | jq

# Căutare produse
curl -X GET "http://localhost:8000/api/v1/emag/products/products?search=laptop" \
  -H "Authorization: Bearer $TOKEN" | jq

# Filtrare pe cont
curl -X GET "http://localhost:8000/api/v1/emag/products/products?account_type=main&limit=20" \
  -H "Authorization: Bearer $TOKEN" | jq

# Sincronizare incrementală manuală
curl -X POST http://localhost:8000/api/v1/emag/products/sync \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_type": "both",
    "mode": "incremental",
    "max_pages": 5
  }'
```

## 🔍 Troubleshooting

### Eroare: "Missing credentials"
```bash
# Verificați variabilele de mediu
echo $EMAG_MAIN_USERNAME
echo $EMAG_FBE_USERNAME

# Restart aplicație după modificare .env
docker-compose restart app
```

### Eroare: "Authentication failed"
- Verificați credențialele în eMAG seller portal
- Verificați IP whitelist în eMAG
- Testați manual login pe marketplace-api.emag.ro

### Sincronizare lentă
```bash
# Reduceți numărul de pagini
curl -X POST http://localhost:8000/api/v1/emag/products/sync \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"mode": "incremental", "max_pages": 3}'
```

### Rate limit exceeded
- Creșteți intervalul de sincronizare în `.env`
- Reduceți `max_pages` în cereri manuale
- Verificați că nu rulează multiple sincronizări simultan

## 📊 Monitorizare Database

```sql
-- Conectare la database
docker exec -it magflow_db psql -U app -d magflow

-- Statistici produse
SELECT 
    account_type,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE is_active = true) as active,
    COUNT(*) FILTER (WHERE sync_status = 'synced') as synced,
    MAX(last_synced_at) as last_sync
FROM emag_products_v2
GROUP BY account_type;

-- Ultimele sincronizări
SELECT 
    sync_type,
    account_type,
    operation,
    status,
    started_at,
    duration_seconds,
    total_items,
    created_items,
    updated_items,
    failed_items
FROM emag_sync_logs
WHERE sync_type = 'products'
ORDER BY started_at DESC
LIMIT 10;

-- Sincronizări eșuate
SELECT 
    account_type,
    operation,
    started_at,
    errors
FROM emag_sync_logs
WHERE status = 'failed' AND sync_type = 'products'
ORDER BY started_at DESC;
```

## 🎉 Finalizare

După parcurgerea acestor pași, sistemul de sincronizare eMAG este complet funcțional:

✅ **Sincronizare automată** - rulează la fiecare oră  
✅ **Sincronizare manuală** - disponibilă prin API  
✅ **Monitoring complet** - status, statistici, istoric  
✅ **Dual-account** - MAIN și FBE sincronizate  
✅ **Production ready** - error handling, logging, retry logic  

Pentru detalii complete, consultați:
- `docs/EMAG_PRODUCT_SYNC_GUIDE.md` - Ghid complet
- `EMAG_PRODUCT_SYNC_QUICKSTART.md` - Quick reference
- `http://localhost:8000/docs` - API documentation

---

**Succes cu sincronizarea! 🚀**
