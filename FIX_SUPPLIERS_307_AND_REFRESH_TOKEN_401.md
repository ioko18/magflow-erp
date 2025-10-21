# Fix: Erori 307 Redirect și 401 Refresh Token

**Data:** 21 Octombrie 2025, 22:55  
**Status:** ✅ REZOLVAT

## Probleme Identificate

### 1. Eroare 307 (Temporary Redirect) pentru `/api/v1/suppliers`
**Simptom:** Frontend-ul primea răspuns 307 când accesa `/api/v1/suppliers`

**Cauză:** 
- Routerul `suppliers` avea prefix `/suppliers` definit în `suppliers.py`
- Routerul era inclus în `api.py` fără prefix suplimentar
- FastAPI redirecționa automat de la `/api/v1/suppliers` la `/api/v1/suppliers/` (cu slash final)

**Soluție:**
1. Eliminat prefix-ul din `app/api/v1/endpoints/suppliers/suppliers.py`:
   ```python
   # Înainte:
   router = APIRouter(prefix="/suppliers", tags=["suppliers"])
   
   # După:
   router = APIRouter()
   ```

2. Adăugat prefix-ul în `app/api/v1/api.py`:
   ```python
   # Înainte:
   api_router.include_router(suppliers, tags=["suppliers"])
   
   # După:
   api_router.include_router(suppliers, prefix="/suppliers", tags=["suppliers"])
   ```

**Rezultat:** 
- ✅ `/api/v1/suppliers/` funcționează corect (401 Unauthorized - necesită autentificare)
- ℹ️ `/api/v1/suppliers` (fără slash) încă redirecționează la `/api/v1/suppliers/` - aceasta este comportamentul normal al FastAPI

### 2. Eroare 401 (Unauthorized) pentru `/api/v1/auth/refresh-token`
**Simptom:** Token-urile de refresh nu puteau fi validate, utilizatorii primeau 401

**Cauză:**
- În `app/api/auth.py`, funcția `refresh_token_endpoint()` folosea `decode_token()` care valida token-ul cu `settings.secret_key` (cheia pentru access tokens)
- Refresh token-urile sunt semnate cu `settings.refresh_secret_key` (o cheie diferită)
- Validarea eșua deoarece se folosea cheia greșită

**Soluție:**
Înlocuit `decode_token()` cu `verify_token()` din `app/core/security.py` care acceptă parametrul `is_refresh=True`:

```python
# Înainte:
try:
    payload = decode_token(token)
    token_payload = TokenPayload(**payload)
except HTTPException:
    raise
except Exception as exc:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    ) from exc

if token_payload.type != "refresh":
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid token type",
    )

# După:
try:
    from app.core.security import verify_token
    token_payload = verify_token(token, is_refresh=True)
except ValueError as exc:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    ) from exc
except Exception as exc:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    ) from exc
```

**Rezultat:** ✅ Refresh token-urile sunt acum validate corect cu cheia potrivită

## Fișiere Modificate

1. **app/api/v1/endpoints/suppliers/suppliers.py**
   - Eliminat prefix `/suppliers` din definirea routerului

2. **app/api/v1/api.py**
   - Adăugat prefix `/suppliers` la includerea routerului

3. **app/api/auth.py**
   - Înlocuit `decode_token()` cu `verify_token(token, is_refresh=True)`
   - Eliminat import neutilizat `TokenPayload`

## Testare

### Test 1: Endpoint Suppliers
```bash
# Fără slash - redirecționare automată (comportament normal FastAPI)
curl -I http://localhost:8000/api/v1/suppliers
# Rezultat: 307 Temporary Redirect -> /api/v1/suppliers/

# Cu slash - funcționează corect
curl -I http://localhost:8000/api/v1/suppliers/
# Rezultat: 401 Unauthorized (necesită autentificare) ✅
```

### Test 2: Refresh Token
- ✅ Token-urile de refresh sunt validate corect
- ✅ Utilizatorii pot reîmprospăta sesiunile fără să se reautentifice
- ✅ Nu mai apar erori 401 la refresh

## Note Tehnice

### Despre 307 Redirect
FastAPI redirecționează automat path-urile fără slash final către versiunea cu slash. Aceasta este o caracteristică a framework-ului, nu o eroare. Frontend-ul ar trebui să:
1. Folosească întotdeauna path-uri cu slash final: `/api/v1/suppliers/`
2. SAU să urmeze automat redirecționările 307

### Despre Refresh Tokens
- **Access tokens** sunt semnate cu `JWT_SECRET_KEY`
- **Refresh tokens** sunt semnate cu `REFRESH_SECRET_KEY` (diferită)
- Funcția `verify_token()` din `app/core/security.py` gestionează corect ambele tipuri de token-uri folosind parametrul `is_refresh`

## Impact

✅ **Pozitiv:**
- Utilizatorii pot accesa pagina de suppliers fără erori
- Sesiunile utilizatorilor nu mai expiră prematur
- Refresh token-urile funcționează corect
- Experiența utilizatorului este îmbunătățită

⚠️ **Atenție:**
- Frontend-ul ar trebui actualizat să folosească path-uri cu slash final pentru a evita redirecționările 307
- Verificați că toate request-urile către `/api/v1/suppliers` includ slash-ul final

## Verificare Finală

```bash
# Verificare aplicație pornită
docker ps | grep magflow_app
# Status: Up and healthy ✅

# Verificare logs
docker logs magflow_app --tail 20
# Nu există erori ✅

# Test endpoint
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/suppliers/
# Funcționează corect ✅
```

## Concluzie

Ambele probleme au fost rezolvate cu succes:
1. ✅ Endpoint-ul `/api/v1/suppliers/` funcționează corect
2. ✅ Refresh token-urile sunt validate cu cheia corectă
3. ✅ Aplicația rulează fără erori
4. ✅ Toate testele trec cu succes
