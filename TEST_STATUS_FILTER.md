# Ghid de Testare - Status Filter

**Data:** 2025-10-02  
**Versiune:** 1.0.0  

---

## 🧪 Testare Manuală în Browser

### Pregătire

1. **Pornește serviciile:**
```bash
cd /Users/macos/anaconda3/envs/MagFlow
make up
```

2. **Pornește frontend-ul:**
```bash
cd admin-frontend
npm run dev
```

3. **Accesează aplicația:**
```
http://localhost:3000/products
```

4. **Login cu credențiale:**
- Email: `admin@example.com`
- Password: `secret`

---

## ✅ Scenarii de Testare

### Test 1: Toate produsele (Default)

**Pași:**
1. Accesează pagina Products
2. Verifică că dropdown-ul afișează "📋 Toate produsele"
3. Verifică numărul de produse afișate

**Rezultat așteptat:**
- ✅ Se afișează **5 produse** în total
- ✅ URL: `/api/v1/products?skip=0&limit=20` (fără `status_filter`)
- ✅ Produse: MCP601, BN283, EMG180, EMG463, EMG443

**Verificare în DevTools:**
```
Network → XHR → products
Request URL: http://localhost:8000/api/v1/products?skip=0&limit=20
```

---

### Test 2: Doar produse active

**Pași:**
1. Click pe dropdown "Filtrează după status"
2. Selectează "✅ Doar active"
3. Așteaptă încărcarea produselor

**Rezultat așteptat:**
- ✅ Se afișează **3 produse** active
- ✅ URL: `/api/v1/products?skip=0&limit=20&status_filter=active`
- ✅ Produse: EMG180, EMG463, EMG443
- ✅ Toate produsele au tag verde "Activ"
- ✅ Niciun produs nu are tag roșu "Discontinuat"

**Verificare:**
```javascript
// În Console
document.querySelectorAll('.ant-tag-green').length === 3
document.querySelectorAll('.ant-tag-red').length === 0
```

---

### Test 3: Doar produse inactive

**Pași:**
1. Click pe dropdown "Filtrează după status"
2. Selectează "❌ Doar inactive"
3. Așteaptă încărcarea produselor

**Rezultat așteptat:**
- ✅ Se afișează **1 produs** inactiv
- ✅ URL: `/api/v1/products?skip=0&limit=20&status_filter=inactive`
- ✅ Produs: BN283
- ✅ Produsul are tag gri "Inactiv"

**Verificare în tabel:**
| SKU | Status | Observații |
|-----|--------|------------|
| BN283 | Inactiv + Discontinuat | Tag gri + Tag roșu |

---

### Test 4: Doar produse discontinuate

**Pași:**
1. Click pe dropdown "Filtrează după status"
2. Selectează "🚫 Doar discontinuate"
3. Așteaptă încărcarea produselor

**Rezultat așteptat:**
- ✅ Se afișează **2 produse** discontinuate
- ✅ URL: `/api/v1/products?skip=0&limit=20&status_filter=discontinued`
- ✅ Produse: MCP601, BN283
- ✅ Ambele produse au tag roșu "Discontinuat"

**Verificare:**
```javascript
// În Console
document.querySelectorAll('.ant-tag-red').length === 2
```

---

### Test 5: Filtrare + Căutare

**Pași:**
1. Selectează "✅ Doar active"
2. Introdu în search: "amplificator"
3. Verifică rezultatele

**Rezultat așteptat:**
- ✅ Se afișează **1 produs**
- ✅ URL: `/api/v1/products?skip=0&limit=20&status_filter=active&search=amplificator`
- ✅ Produs: EMG180 (Amplificator audio)

---

### Test 6: Resetare filtre

**Pași:**
1. Aplică un filtru (ex: "Doar inactive")
2. Click pe butonul "Resetează Filtre"
3. Verifică rezultatele

**Rezultat așteptat:**
- ✅ Dropdown revine la "📋 Toate produsele"
- ✅ Search box devine gol
- ✅ Se afișează toate cele 5 produse

---

### Test 7: Paginare cu filtre

**Pași:**
1. Selectează "✅ Doar active"
2. Schimbă page size la 2 produse per pagină
3. Navighează între pagini

**Rezultat așteptat:**
- ✅ Pagina 1: 2 produse
- ✅ Pagina 2: 1 produs
- ✅ Total: "1-2 din 3 produse" (pagina 1)
- ✅ Filtrul rămâne aplicat la schimbarea paginii

---

## 🔍 Verificare în Database

```sql
-- Conectează-te la database
docker exec -it magflow_db psql -U app -d magflow

-- Verifică distribuția produselor
SELECT 
    sku,
    name,
    is_active,
    is_discontinued,
    CASE 
        WHEN is_discontinued = true THEN 'discontinued'
        WHEN is_active = true THEN 'active'
        ELSE 'inactive'
    END as status_category
FROM app.products
ORDER BY id;

-- Rezultat așteptat:
--   sku   |           name            | is_active | is_discontinued | status_category
-- --------+---------------------------+-----------+-----------------+-----------------
--  MCP601 | Modul convertor MCP4725   | t         | t               | discontinued
--  BN283  | Driver motor L298N        | f         | t               | inactive
--  EMG180 | Amplificator audio        | t         | f               | active
--  EMG463 | Adaptor USB la RS232      | t         | f               | active
--  EMG443 | Shield SIM900 GPRS/GSM    | t         | f               | active
```

---

## 📊 Verificare Backend Logs

```bash
# Verifică că backend primește parametrul corect
docker logs magflow_app --tail 100 | grep "status_filter"

# Rezultat așteptat:
# GET /api/v1/products?skip=0&limit=20&status_filter=active HTTP/1.1" 200 OK
# GET /api/v1/products?skip=0&limit=20&status_filter=inactive HTTP/1.1" 200 OK
# GET /api/v1/products?skip=0&limit=20&status_filter=discontinued HTTP/1.1" 200 OK
```

---

## 🐛 Debugging

### Problema: Filtrul nu se aplică

**Verificare:**
1. Deschide DevTools → Network tab
2. Aplică un filtru
3. Verifică request-ul către `/api/v1/products`

**Ce să cauți:**
```
Query String Parameters:
  skip: 0
  limit: 20
  status_filter: active  ← Trebuie să fie prezent!
```

**Dacă lipsește `status_filter`:**
- Frontend nu trimite parametrul
- Verifică că ai salvat modificările în `Products.tsx`
- Hard refresh browser: Ctrl+Shift+R

---

### Problema: Număr incorect de produse

**Verificare:**
```bash
# Test direct API
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"secret"}' \
  > token.json

TOKEN=$(cat token.json | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

# Test filtru active
curl -X GET "http://localhost:8000/api/v1/products?status_filter=active" \
  -H "Authorization: Bearer $TOKEN" | jq '.data.pagination.total'

# Rezultat așteptat: 3
```

---

### Problema: Backend nu se reîncarcă

**Verificare:**
```bash
# Verifică că WatchFiles detectează modificările
docker logs magflow_app | grep -i "reloading"

# Dacă nu vezi "Reloading", restart manual:
docker restart magflow_app
```

---

## ✅ Checklist de Testare

### Funcționalitate de bază
- [ ] Filtrul "Toate produsele" afișează 5 produse
- [ ] Filtrul "Doar active" afișează 3 produse
- [ ] Filtrul "Doar inactive" afișează 1 produs
- [ ] Filtrul "Doar discontinuate" afișează 2 produse

### Integrare
- [ ] Filtrarea funcționează cu search
- [ ] Filtrarea funcționează cu paginare
- [ ] Butonul "Resetează Filtre" funcționează
- [ ] Filtrul persistă la schimbarea paginii

### UI/UX
- [ ] Dropdown-ul afișează toate opțiunile
- [ ] Loading indicator apare la schimbarea filtrului
- [ ] Tag-urile de status sunt corecte
- [ ] Numărul total de produse este corect

### Backend
- [ ] Request-urile conțin parametrul `status_filter`
- [ ] Response-urile conțin numărul corect de produse
- [ ] Log-urile nu conțin erori
- [ ] Query-urile SQL sunt corecte

### Performance
- [ ] Filtrarea este rapidă (< 500ms)
- [ ] Nu există memory leaks
- [ ] Paginarea funcționează smooth

---

## 📈 Rezultate Așteptate

| Filtru | Produse | SKU-uri |
|--------|---------|---------|
| Toate | 5 | MCP601, BN283, EMG180, EMG463, EMG443 |
| Active | 3 | EMG180, EMG463, EMG443 |
| Inactive | 1 | BN283 |
| Discontinuate | 2 | MCP601, BN283 |

---

## 🎯 Success Criteria

✅ **Testarea este considerată success dacă:**
1. Toate cele 4 filtre funcționează corect
2. Numărul de produse afișate corespunde cu database-ul
3. Nu există erori în console sau backend logs
4. UI este responsive și intuitiv
5. Filtrele se combină corect cu search și paginare

---

**Ghid creat de:** Cascade AI Assistant  
**Data:** 2025-10-02  
**Versiune:** 1.0.0
