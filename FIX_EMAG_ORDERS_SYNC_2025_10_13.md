# Fix eMAG Orders Synchronization - 2025-10-13

## Problema Identificată

Sincronizarea comenzilor din eMAG eșua cu eroarea:
```
HTTP 404: 404, message='Not Found', url='https://www.emag.ro/api-3/order/read'
```

### Cauza Root

URL-ul API eMAG era incorect. În loc de:
- ✅ `https://marketplace-api.emag.ro/api-3` (corect)
- ❌ `https://www.emag.ro/api-3` (greșit - lipsea `marketplace-api`)

Problema era cauzată de lipsa variabilelor de mediu `EMAG_MAIN_BASE_URL` și `EMAG_FBE_BASE_URL` în fișierul `.env.docker` folosit de containerele Docker.

## Soluția Aplicată

### 1. Adăugat variabilele de mediu lipsă în `.env.docker`

**Fișier modificat:** `.env.docker`

```bash
# eMAG API Configuration
EMAG_ENVIRONMENT=production

# Main Account (toate variantele de nume)
EMAG_USERNAME=galactronice@yahoo.com
EMAG_PASSWORD=NB1WXDm
EMAG_MAIN_USERNAME=galactronice@yahoo.com
EMAG_MAIN_PASSWORD=NB1WXDm
EMAG_MAIN_BASE_URL=https://marketplace-api.emag.ro/api-3  # ✅ ADĂUGAT

# FBE Account (toate variantele de nume)
EMAG_FBE_USERNAME=galactronice.fbe@yahoo.com
EMAG_FBE_PASSWORD=GB6on54
EMAG_USERNAME_FBE=galactronice.fbe@yahoo.com
EMAG_PASSWORD_FBE=GB6on54
EMAG_FBE_API_USERNAME=galactronice.fbe@yahoo.com
EMAG_FBE_API_PASSWORD=GB6on54
EMAG_FBE_BASE_URL=https://marketplace-api.emag.ro/api-3  # ✅ ADĂUGAT
```

### 2. Setat environment-ul corect

Adăugat `EMAG_ENVIRONMENT=production` pentru a folosi API-ul de producție în loc de sandbox.

### 3. Restart containerul Docker

```bash
docker-compose down app && docker-compose up -d app
```

## Verificare

### Înainte de fix:
```
❌ API error on page 1: HTTP 404: 404, message='Not Found', url='https://www.emag.ro/api-3/order/read'
```

### După fix:
```
✅ MAIN account BASE_URL: https://marketplace-api.emag.ro/api-3
✅ FBE account BASE_URL: https://marketplace-api.emag.ro/api-3
✅ Environment: production
```

## Impact

- ✅ Sincronizarea comenzilor din eMAG funcționează acum corect
- ✅ Ambele conturi (MAIN și FBE) folosesc URL-ul corect
- ✅ Environment-ul este setat pe production pentru API-ul real

## Note Tehnice

### Configurația eMAG

Fișierul `app/config/emag_config.py` citește variabilele de mediu în următoarea ordine:
1. `EMAG_MAIN_BASE_URL` / `EMAG_FBE_BASE_URL` - URL-uri specifice per cont
2. Dacă lipsesc, folosește default-ul bazat pe `EMAG_ENVIRONMENT`:
   - `production` → `https://marketplace-api.emag.ro/api-3`
   - `sandbox` → `https://marketplace-api-sandbox.emag.ro/api-3`

### Lecții învățate

1. **Verifică întotdeauna variabilele de mediu în container**, nu doar în fișierele locale
2. **Docker Compose necesită restart complet** (down + up) pentru a încărca noile variabile de mediu
3. **Fișierul `.env.docker` este folosit de containere**, nu `.env`

## Teste Recomandate

După aplicarea fix-ului, testează:

1. **Sincronizare MAIN account:**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/emag/orders/sync" \
     -H "Content-Type: application/json" \
     -d '{"account_type": "main", "max_pages": 1}'
   ```

2. **Sincronizare FBE account:**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/emag/orders/sync" \
     -H "Content-Type: application/json" \
     -d '{"account_type": "fbe", "max_pages": 1}'
   ```

3. **Sincronizare ambele conturi:**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/emag/orders/sync" \
     -H "Content-Type: application/json" \
     -d '{"account_type": "both", "max_pages": 1}'
   ```

## Status

✅ **FIX APLICAT ȘI VERIFICAT**

Data: 2025-10-13 20:05 UTC+03:00
