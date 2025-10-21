# 🚀 Instrucțiuni de Deployment - Fix Import Google Sheets

## 📋 Pre-requisite

- Backend rulează pe port 8000
- Frontend rulează pe port 5173
- PostgreSQL database activ
- Redis activ (opțional)
- service_account.json configurat

## 🔄 Pași de Deployment

### 1. Backend (Nu necesită restart)

Modificările în `product_import.py` sunt deja active dacă backend-ul rulează cu `--reload`.

**Verificare**:
```bash
# Check dacă backend rulează
curl http://localhost:8000/health

# Ar trebui să returneze: {"status":"ok","timestamp":"..."}
```

**Dacă backend-ul NU rulează**:
```bash
# Pornește backend
./start_backend.sh

# SAU manual
conda activate MagFlow
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend (Necesită rebuild)

**Opțiunea A: Development Mode (Recomandat pentru testare)**
```bash
cd admin-frontend

# Oprește serverul existent (Ctrl+C)

# Reinstalează dependențele (dacă e necesar)
npm install

# Pornește dev server
npm run dev

# Frontend va fi disponibil pe http://localhost:5173
```

**Opțiunea B: Production Build**
```bash
cd admin-frontend

# Build pentru producție
npm run build

# Servește build-ul
npm run preview
# SAU
npx serve -s dist -l 5173
```

### 3. Verificare Deployment

**Test 1: Backend Health**
```bash
curl http://localhost:8000/health
# Expected: {"status":"ok",...}
```

**Test 2: Frontend Loading**
```bash
curl -I http://localhost:5173
# Expected: HTTP/1.1 200 OK
```

**Test 3: API Connection**
```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"secret"}' \
  | jq -r '.access_token')

# Test Google Sheets connection
curl -s http://localhost:8000/api/v1/products/import/sheets/test-connection \
  -H "Authorization: Bearer $TOKEN" | jq .

# Expected: {"status":"connected",...}
```

**Test 4: Import Functionality**
```bash
# Start import (va dura 1-3 minute pentru dataset mare)
curl -s -X POST http://localhost:8000/api/v1/products/import/google-sheets \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"auto_map": true, "import_suppliers": true}' | jq .

# Expected: {"import_id":X,"status":"completed",...}
```

## 🧪 Testare Manuală în Browser

### Pas 1: Login
1. Deschide: http://localhost:5173/login
2. Email: `admin@example.com`
3. Password: `secret`
4. Click "Login"

### Pas 2: Navighează la Import
1. Click pe "Products" în menu
2. Click pe "Import from Google Sheets"
3. Verifică că status-ul este "Google Sheets Connected" (verde)

### Pas 3: Test Import
1. Click pe "Import Products & Suppliers"
2. În modal, verifică opțiunile:
   - ✅ Update existing products
   - ✅ Create new products
   - ✅ Import suppliers from "Product_Suppliers" sheet
3. Click "Start Import"
4. **Observă**:
   - Progress bar apare și se animă
   - Mesaje de status: "Connecting...", "Fetching products...", etc.
   - Loading notification în colțul ecranului
5. **Așteaptă** finalizarea (1-3 minute pentru 5000+ produse)
6. **Verifică** modal de succes:
   - Statistici: Total Rows, Successful, Failed, Created, Updated
   - Duration în secunde
   - Alert pentru produse failed (dacă există)

### Pas 4: Verificare Rezultate
1. În tab "Products", verifică că produsele sunt actualizate
2. În tab "Import History", verifică că importul apare în listă
3. Click pe "Vezi furnizori" pentru un produs - verifică că furnizorii sunt importați

## 🐛 Troubleshooting

### Problema: Frontend nu se actualizează

**Soluție**:
```bash
# Clear cache și rebuild
cd admin-frontend
rm -rf node_modules/.vite
npm run dev
```

### Problema: Backend nu răspunde

**Soluție**:
```bash
# Check logs
tail -50 logs/backend.log

# Restart backend
pkill -f uvicorn
./start_backend.sh
```

### Problema: Import timeout după 5 minute

**Soluție temporară** (crește timeout-ul):
```typescript
// În admin-frontend/src/services/api.ts
timeout: 600000, // 10 minutes
```

**Soluție permanentă**: Implementează background jobs (vezi documentația)

### Problema: Eroare "Not authenticated"

**Soluție**:
```bash
# Verifică că token-ul este valid
# Logout și login din nou în browser
```

### Problema: "Connection Error" la Google Sheets

**Verificări**:
```bash
# 1. Verifică service_account.json
ls -la service_account.json

# 2. Test manual
conda activate MagFlow
python3 -c "
from app.services.google_sheets_service import GoogleSheetsService
service = GoogleSheetsService()
service.authenticate()
service.open_spreadsheet()
print('✅ Connection OK')
"
```

## 📊 Monitoring

### Logs de urmărit

**Backend logs**:
```bash
# Real-time monitoring
tail -f logs/backend.log | grep -i "import\|google\|sheets"

# Caută pentru:
# - "Starting Google Sheets import requested by..."
# - "Import completed successfully in X.XXs"
# - "Total: X, Success: Y, Failed: Z"
```

**Frontend console**:
- Deschide DevTools (F12)
- Tab "Console"
- Caută pentru erori sau warning-uri

### Metrici de succes

✅ **Import reușit**:
- Duration: 20-240 secunde (depinde de număr produse)
- Success rate: >95%
- Failed imports: <5%
- No timeout errors

❌ **Import problematic**:
- Timeout după 5 minute
- Success rate: <90%
- Failed imports: >10%
- Erori repetate în logs

## 🔄 Rollback (Dacă e necesar)

### Frontend Rollback
```bash
cd admin-frontend
git checkout HEAD~1 src/services/api.ts
git checkout HEAD~1 src/pages/products/ProductImport.tsx
npm run dev
```

### Backend Rollback
```bash
git checkout HEAD~1 app/api/v1/endpoints/products/product_import.py
# Restart backend
pkill -f uvicorn
./start_backend.sh
```

## 📞 Support

Dacă întâmpini probleme:

1. **Check logs**: `logs/backend.log`
2. **Check console**: Browser DevTools
3. **Check documentation**: `GOOGLE_SHEETS_IMPORT_IMPROVEMENTS_2025_10_15.md`
4. **Contact**: support@magflow.com

## ✅ Checklist Final

Înainte de a considera deployment-ul complet:

- [ ] Backend rulează și răspunde la `/health`
- [ ] Frontend se încarcă la http://localhost:5173
- [ ] Login funcționează
- [ ] Google Sheets connection status este "Connected"
- [ ] Import test reușește (chiar și cu 1-2 produse)
- [ ] Progress bar apare și se animă
- [ ] Modal de succes afișează statistici corecte
- [ ] Produsele sunt actualizate în tabel
- [ ] Import history conține noul import
- [ ] Logs nu conțin erori critice

---

**Data**: 15 Octombrie 2025  
**Versiune**: 1.0.0  
**Status**: ✅ READY FOR DEPLOYMENT
