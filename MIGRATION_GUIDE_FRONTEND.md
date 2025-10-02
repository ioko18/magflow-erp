# Ghid de Migrare - Frontend eMAG Sync

## 📋 Overview

Acest ghid vă ajută să migrați de la pagina veche de sincronizare (`EmagProductSync`) la noua pagină (`EmagProductSyncV2`) care integrează complet noul sistem de sincronizare.

## 🔄 Diferențe Principale

### Endpoint-uri API

| Funcționalitate | Vechi | Nou |
|----------------|-------|-----|
| Statistici | `/emag/enhanced/status` | `/emag/products/statistics` |
| Status Sync | `/emag/enhanced/products/sync-progress` | `/emag/products/status` |
| Lista Produse | `/emag/enhanced/products/all` | `/emag/products/products` |
| Start Sync | `/emag/enhanced/sync/all-products` | `/emag/products/sync` |
| Test Conexiune | N/A | `/emag/products/test-connection` ⭐ |

### Funcționalități Noi

#### 1. Test Conexiune API ⭐
```typescript
// Nou în V2
const testConnection = async (accountType: 'main' | 'fbe') => {
  const response = await api.post('/emag/products/test-connection', null, {
    params: { account_type: accountType }
  })
  // Verifică conexiunea înainte de sincronizare
}
```

#### 2. Moduri de Sincronizare ⭐
```typescript
// Vechi: doar full sync
startFullSync(accountType)

// Nou: 3 moduri
syncOptions = {
  mode: 'full' | 'incremental' | 'selective',
  // ...
}
```

#### 3. Strategii Rezolvare Conflicte ⭐
```typescript
// Nou în V2
syncOptions = {
  conflict_strategy: 'emag_priority' | 'local_priority' | 'newest_wins' | 'manual',
  // ...
}
```

#### 4. Opțiuni Avansate ⭐
```typescript
// Nou în V2
syncOptions = {
  account_type: 'main' | 'fbe' | 'both',
  mode: 'full' | 'incremental' | 'selective',
  max_pages: number | null,
  items_per_page: number,
  include_inactive: boolean,
  conflict_strategy: string,
  run_async: boolean  // Nou!
}
```

## 🚀 Pași de Migrare

### Pas 1: Backup Date
```bash
# Export produse existente
curl -X GET "http://localhost:8000/api/v1/emag/products/products?limit=1000" \
  -H "Authorization: Bearer $TOKEN" > products_backup.json
```

### Pas 2: Test Noile Endpoint-uri

#### Test Statistici
```bash
curl -X GET http://localhost:8000/api/v1/emag/products/statistics \
  -H "Authorization: Bearer $TOKEN"
```

#### Test Conexiune
```bash
# MAIN
curl -X POST "http://localhost:8000/api/v1/emag/products/test-connection?account_type=main" \
  -H "Authorization: Bearer $TOKEN"

# FBE
curl -X POST "http://localhost:8000/api/v1/emag/products/test-connection?account_type=fbe" \
  -H "Authorization: Bearer $TOKEN"
```

#### Test Sincronizare (Dry Run)
```bash
curl -X POST http://localhost:8000/api/v1/emag/products/sync \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_type": "main",
    "mode": "incremental",
    "max_pages": 1,
    "items_per_page": 10,
    "include_inactive": false,
    "conflict_strategy": "emag_priority",
    "run_async": false
  }'
```

### Pas 3: Actualizare Frontend

#### Opțiune A: Folosire Directă V2
```typescript
// În App.tsx - schimbă ruta implicită
{
  path: 'emag',
  element: <EmagProductSyncV2 />,  // Schimbat de la EmagProductSync
}
```

#### Opțiune B: Păstrare Ambele Versiuni
```typescript
// Păstrează ambele pentru tranziție
{
  path: 'emag',
  element: <EmagProductSync />,  // Vechi
},
{
  path: 'emag/sync-v2',
  element: <EmagProductSyncV2 />,  // Nou
}
```

### Pas 4: Actualizare Componente Custom

Dacă aveți componente custom care folosesc pagina veche:

```typescript
// Vechi
import EmagProductSync from './pages/EmagProductSync'

// Nou
import EmagProductSyncV2 from './pages/EmagProductSyncV2'
```

### Pas 5: Testare Completă

1. **Test Conexiune**
   - Accesați `/emag/sync-v2`
   - Click "Test Connection" pentru ambele conturi
   - Verificați că ambele sunt OK

2. **Test Sincronizare Incrementală**
   ```typescript
   // Configurare
   {
     account_type: 'main',
     mode: 'incremental',
     max_pages: 2,
     run_async: false
   }
   ```
   - Start sync
   - Monitorizați progresul
   - Verificați rezultatele

3. **Test Sincronizare Completă**
   ```typescript
   // Configurare
   {
     account_type: 'both',
     mode: 'full',
     max_pages: null,
     run_async: true
   }
   ```
   - Start sync
   - Monitorizați în background
   - Verificați statisticile

4. **Test Filtrare și Căutare**
   - Căutare după SKU
   - Filtrare după account
   - Export CSV

5. **Test Istoric**
   - Verificați tab "Sync History"
   - Verificați detalii sincronizări

## 📊 Comparație Funcționalități

| Funcționalitate | Vechi | Nou V2 |
|----------------|-------|--------|
| Dual-account sync | ✅ | ✅ |
| Progress tracking | ✅ | ✅ Îmbunătățit |
| Products table | ✅ | ✅ Îmbunătățit |
| Sync history | ✅ | ✅ Îmbunătățit |
| Test connection | ❌ | ✅ **NOU** |
| Sync modes | ❌ | ✅ **NOU** (3 moduri) |
| Conflict resolution | ❌ | ✅ **NOU** (4 strategii) |
| Advanced options | Limitate | ✅ **Complete** |
| Async execution | ❌ | ✅ **NOU** |
| Real-time stats | Parțial | ✅ **Complete** |
| Export CSV | ✅ | ✅ |
| Product details | ✅ | ✅ Îmbunătățit |
| Responsive design | ✅ | ✅ Îmbunătățit |
| Auto-refresh | ✅ | ✅ Îmbunătățit |

## 🔧 Configurare Recomandată

### Development
```typescript
{
  account_type: 'main',
  mode: 'incremental',
  max_pages: 2,
  items_per_page: 50,
  include_inactive: false,
  conflict_strategy: 'emag_priority',
  run_async: false  // Pentru debugging
}
```

### Production
```typescript
{
  account_type: 'both',
  mode: 'incremental',
  max_pages: null,
  items_per_page: 100,
  include_inactive: false,
  conflict_strategy: 'emag_priority',
  run_async: true  // Background execution
}
```

## 🐛 Troubleshooting Migrare

### Problema: Endpoint-uri nu răspund
**Cauză**: Backend nu este actualizat  
**Soluție**:
```bash
# Verificați că backend-ul are noile endpoint-uri
curl http://localhost:8000/docs | grep "/emag/products"

# Restart backend
docker-compose restart app
```

### Problema: Produse nu se afișează
**Cauză**: Structură diferită răspuns API  
**Soluție**:
```typescript
// Verificați structura răspunsului
console.log(response.data)

// V2 folosește: response.data.data.products
// Vechi folosea: response.data.products
```

### Problema: Sincronizare nu pornește
**Cauză**: Parametri diferiți  
**Soluție**:
```typescript
// Vechi
{
  max_pages_per_account: 10,
  delay_between_requests: 0.5
}

// Nou
{
  max_pages: 10,
  items_per_page: 100,
  run_async: true
}
```

## 📝 Checklist Migrare

- [ ] Backup date existente
- [ ] Test endpoint-uri noi în Postman/curl
- [ ] Test conexiune API pentru ambele conturi
- [ ] Actualizare import-uri în cod
- [ ] Actualizare rute în App.tsx
- [ ] Test sincronizare incrementală (mic)
- [ ] Test sincronizare completă (mare)
- [ ] Test filtrare și căutare
- [ ] Test export CSV
- [ ] Test istoric sincronizări
- [ ] Test responsive design (mobile/tablet)
- [ ] Verificare console pentru erori
- [ ] Verificare network tab pentru API calls
- [ ] Test auto-refresh
- [ ] Test notificări
- [ ] Documentare modificări pentru echipă

## 🎯 Timeline Recomandat

### Săptămâna 1: Pregătire
- Zi 1-2: Backup și testare endpoint-uri
- Zi 3-4: Actualizare cod și teste locale
- Zi 5: Code review și documentare

### Săptămâna 2: Testare
- Zi 1-2: Testare extensivă pe development
- Zi 3-4: Testare pe staging
- Zi 5: Pregătire deployment

### Săptămâna 3: Deployment
- Zi 1: Deployment pe production
- Zi 2-3: Monitoring intensiv
- Zi 4-5: Ajustări și optimizări

## 🔄 Rollback Plan

Dacă apar probleme:

### Pas 1: Revert Rute
```typescript
// În App.tsx
{
  path: 'emag',
  element: <EmagProductSync />,  // Înapoi la vechi
}
```

### Pas 2: Clear Cache
```bash
# Browser
Ctrl+Shift+Delete -> Clear cache

# Backend
docker-compose restart app
```

### Pas 3: Verificare Logs
```bash
# Frontend
Browser Console

# Backend
docker-compose logs -f app
```

## 📚 Resurse Adiționale

- **Backend API Docs**: `http://localhost:8000/docs`
- **Frontend Guide**: `admin-frontend/EMAG_SYNC_FRONTEND_GUIDE.md`
- **Backend Guide**: `docs/EMAG_PRODUCT_SYNC_GUIDE.md`
- **Quick Start**: `EMAG_PRODUCT_SYNC_QUICKSTART.md`

## 🎉 După Migrare

După migrare reușită:

1. **Ștergeți pagina veche** (opțional):
   ```bash
   # După 2-4 săptămâni de monitoring
   rm admin-frontend/src/pages/EmagProductSync.tsx
   ```

2. **Redenumire V2 → Principal**:
   ```bash
   mv EmagProductSyncV2.tsx EmagProductSync.tsx
   ```

3. **Actualizare documentație**:
   - Marcați ghidul vechi ca deprecated
   - Actualizați README-ul principal

4. **Training echipă**:
   - Prezentare funcționalități noi
   - Demo live
   - Q&A session

---

**Versiune**: 1.0.0  
**Data**: 2025-10-01  
**Status**: Ready for Migration ✅
