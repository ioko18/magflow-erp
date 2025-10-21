# 🧪 Instrucțiuni de Testare - MagFlow ERP

**Data:** 14 Octombrie 2025  
**Scop:** Verificare completă a fix-urilor implementate

---

## 🎯 Obiective Testare

1. ✅ Verificare funcționalitate Google Sheets Import
2. ✅ Testare retry logic pentru erori de rețea
3. ✅ Validare mesaje de eroare user-friendly
4. ✅ Verificare eMAG order acknowledgment
5. ✅ Testare resilience și error recovery

---

## 🚀 Pregătire Mediu de Testare

### 1. Restart Aplicație
```bash
cd /Users/macos/anaconda3/envs/MagFlow

# Oprire servicii
make stop

# Curățare (opțional)
docker-compose down -v

# Pornire servicii
make start

# Verificare status
docker-compose ps
```

### 2. Verificare Logs
```bash
# Terminal 1: Application logs
docker-compose logs -f magflow_app

# Terminal 2: Worker logs  
docker-compose logs -f magflow_worker

# Terminal 3: Database logs (opțional)
docker-compose logs -f magflow_db
```

### 3. Verificare Servicii
```bash
# Health check
curl http://localhost:8000/api/v1/health/live

# Expected output:
# {"status":"healthy","timestamp":"..."}
```

---

## 📋 Scenarii de Testare

### Test 1: Import Google Sheets - Succes Normal

**Obiectiv:** Verificare import normal fără erori

**Pași:**
1. Accesați UI: `http://localhost:3000`
2. Login cu credențiale admin
3. Navigați la: **Products → Import from Google Sheets**
4. Click pe **"Import Products & Suppliers"**
5. Așteptați finalizare (30-60 secunde)

**Rezultat Așteptat:**
```
✅ Status: Success
✅ Total products: 5160
✅ Successful imports: 5160
✅ Failed imports: 0
✅ Suppliers imported: 5391
```

**Verificare Logs:**
```bash
# Căutați în logs:
grep "Import completed" docker-compose logs magflow_app

# Ar trebui să vedeți:
# Import completed: 5160 successful, 0 failed
```

---

### Test 2: Retry Logic - Simulare Eroare de Rețea

**Obiectiv:** Verificare retry logic funcționează corect

**Metodă 1: Disconnect temporar internet**
```bash
# Pe macOS:
# 1. Deschideți System Preferences → Network
# 2. Disconnect Wi-Fi
# 3. Inițiați import în UI
# 4. Reconnect Wi-Fi după 5 secunde
```

**Rezultat Așteptat:**
```
Logs ar trebui să arate:
1. "Attempting to authenticate (attempt 1/3)"
2. "Network error during authentication (attempt 1/3)"
3. "Retrying in 2.0 seconds..."
4. "Attempting to authenticate (attempt 2/3)"
5. "Successfully authenticated with Google Sheets API"
```

**Metodă 2: Firewall temporar**
```bash
# Blocați temporar Google Sheets API
# (necesită configurare firewall)
```

---

### Test 3: Mesaje de Eroare User-Friendly

**Obiectiv:** Verificare mesaje clare pentru utilizatori

**Scenario A: Fișier service_account.json lipsă**
```bash
# Redenumire temporară
mv service_account.json service_account.json.bak

# Încercați import în UI
# Rezultat așteptat:
# "Service account configuration file not found. 
#  Please contact administrator."

# Restaurare
mv service_account.json.bak service_account.json
```

**Scenario B: Eroare de rețea**
```bash
# Disconnect internet complet
# Încercați import în UI
# Rezultat așteptat:
# "Network Error: Unable to connect to Google Sheets. 
#  Please check your internet connection and try again."
```

**Scenario C: Permisiuni spreadsheet**
```bash
# Modificați temporar numele spreadsheet în config
# Rezultat așteptat:
# "Spreadsheet Error: Unable to access the Google Sheets document. 
#  Please verify permissions."
```

---

### Test 4: eMAG Order Acknowledgment

**Obiectiv:** Verificare gestionare corectă erori eMAG API

**Pași:**
1. Așteptați task-ul automat (rulează la fiecare 5 minute)
2. SAU rulați manual:
```bash
docker-compose exec magflow_worker celery -A app.worker call \
  emag.auto_acknowledge_orders
```

**Verificare Logs:**
```bash
# Căutați în worker logs:
docker-compose logs magflow_worker | grep "auto_acknowledge"

# Ar trebui să vedeți:
# - "Starting auto-acknowledgment of new orders"
# - "Acknowledged X orders" (pentru fiecare account)
# - Eventual: "Failed to acknowledge order XXX" (dacă există erori de la eMAG)
```

**Rezultat Așteptat:**
```
✅ Task-ul se execută fără crash
✅ Comenzile valide sunt acknowledged
✅ Erorile HTTP 500 de la eMAG sunt logate dar nu opresc task-ul
✅ Raport complet cu statistici la final
```

---

### Test 5: Resilience - Recovery după Erori

**Obiectiv:** Verificare sistem se recuperează automat

**Scenario:**
```bash
# 1. Disconnect internet
# 2. Inițiați import (va eșua)
# 3. Reconnect internet
# 4. Inițiați din nou import (ar trebui să reușească)
```

**Rezultat Așteptat:**
```
✅ Prima încercare: Eșec cu mesaj clar
✅ A doua încercare: Succes complet
✅ Logs arată retry-uri în prima încercare
✅ Logs arată succes în a doua încercare
```

---

## 📊 Verificări Suplimentare

### 1. Verificare Database

```bash
# Connect la database
docker-compose exec magflow_db psql -U magflow_user -d magflow_db

# Verificare produse importate
SELECT COUNT(*) FROM products;
# Expected: 5160

# Verificare mappings
SELECT COUNT(*) FROM google_sheets_product_mapping;
# Expected: 5160

# Verificare suppliers
SELECT COUNT(*) FROM product_supplier_sheets;
# Expected: 5391

# Exit
\q
```

### 2. Verificare API Endpoints

```bash
# Test connection endpoint
curl -X GET "http://localhost:8000/api/v1/products/import/sheets/test-connection" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Expected response:
# {
#   "status": "connected",
#   "message": "Successfully connected to Google Sheets",
#   "statistics": {...}
# }
```

### 3. Verificare Import History

```bash
# Get import history
curl -X GET "http://localhost:8000/api/v1/products/import/history?limit=5" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Ar trebui să vedeți ultimele 5 import-uri cu statistici
```

---

## 🔍 Troubleshooting

### Problemă: Import eșuează imediat

**Verificări:**
```bash
# 1. Verificare service_account.json există
ls -la service_account.json

# 2. Verificare format JSON valid
cat service_account.json | python3 -m json.tool

# 3. Verificare permisiuni file
chmod 644 service_account.json

# 4. Verificare logs pentru detalii
docker-compose logs magflow_app | tail -100
```

### Problemă: Retry logic nu funcționează

**Verificări:**
```bash
# 1. Verificare cod actualizat
grep "max_retries" app/services/google_sheets_service.py

# 2. Verificare imports
grep "from requests.exceptions" app/services/google_sheets_service.py

# 3. Restart servicii
make restart
```

### Problemă: Mesaje de eroare nu sunt clare

**Verificări:**
```bash
# 1. Verificare endpoint actualizat
grep "Network Error:" app/api/v1/endpoints/products/product_import.py

# 2. Verificare logs pentru erori
docker-compose logs magflow_app | grep "ERROR"
```

---

## ✅ Checklist Final de Testare

### Pre-Production:
- [ ] Test 1: Import normal - PASSED
- [ ] Test 2: Retry logic - PASSED
- [ ] Test 3: Mesaje eroare - PASSED
- [ ] Test 4: eMAG acknowledgment - PASSED
- [ ] Test 5: Recovery - PASSED
- [ ] Verificare database - PASSED
- [ ] Verificare API endpoints - PASSED
- [ ] Verificare logs - PASSED

### Production Readiness:
- [ ] Toate testele au trecut
- [ ] Logs sunt clare și informative
- [ ] Mesaje de eroare sunt user-friendly
- [ ] Retry logic funcționează corect
- [ ] Sistem se recuperează automat după erori
- [ ] Performance este acceptabil
- [ ] Documentație este completă

---

## 📈 Metrici de Success

### Import Google Sheets:
- **Success Rate:** > 99%
- **Timp Mediu:** 30-60 secunde
- **Retry Rate:** < 5%
- **Error Recovery:** 100%

### eMAG Order Acknowledgment:
- **Success Rate:** > 95% (dependent de eMAG API)
- **Failed Orders:** Logate și raportate
- **Task Completion:** 100%
- **No Crashes:** ✅

### System Resilience:
- **Network Error Recovery:** Automatic
- **Max Retries:** 3 per operation
- **Exponential Backoff:** 2s → 3s → 4.5s
- **Graceful Degradation:** Yes

---

## 🎯 Raportare Rezultate

### Template Raport:
```markdown
## Test Results - [DATA]

### Environment:
- OS: macOS
- Docker: [VERSION]
- Python: 3.11+

### Tests Executed:
1. Import Google Sheets: [PASS/FAIL]
2. Retry Logic: [PASS/FAIL]
3. Error Messages: [PASS/FAIL]
4. eMAG Acknowledgment: [PASS/FAIL]
5. Recovery: [PASS/FAIL]

### Issues Found:
- [Descriere problemă 1]
- [Descriere problemă 2]

### Recommendations:
- [Recomandare 1]
- [Recomandare 2]

### Overall Status: [READY/NOT READY]
```

---

## 📞 Support

### În caz de probleme:

1. **Verificați logs:**
   ```bash
   docker-compose logs -f magflow_app
   ```

2. **Verificați documentația:**
   - `FIXES_APPLIED.md`
   - `FINAL_VERIFICATION_REPORT.md`

3. **Restart servicii:**
   ```bash
   make restart
   ```

4. **Contactați echipa de development**

---

**Document creat:** 14 Octombrie 2025  
**Ultima actualizare:** 14 Octombrie 2025  
**Status:** ✅ Ready for Testing

🎉 **Succes la testare!** 🎉
