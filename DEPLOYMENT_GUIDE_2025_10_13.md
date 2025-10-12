# Ghid de Deployment - Manual Reorder Quantity Feature
**Data:** 13 Octombrie 2025, 01:45 AM  
**Status:** 🚀 **READY FOR DEPLOYMENT**

---

## 📋 Rezumat Rapid

Am implementat funcționalitatea de editare manuală a **Reorder Quantity** și am consolidat migrațiile pentru o mai bună organizare.

**Ce trebuie făcut:**
1. ✅ Adăugat codul (DONE)
2. ⏳ Adăugat coloana în DB (URMEAZĂ)
3. ⏳ Restart backend
4. ⏳ Verificare finală

---

## 🚀 Pași de Deployment

### **Pas 1: Verifică Credențialele DB** ✅

Verifică fișierul `.env` pentru credențialele bazei de date:

```bash
cat .env | grep DB_
```

**Expected output:**
```
DB_HOST=postgres (sau localhost/127.0.0.1)
DB_PORT=5432
DB_NAME=magflow
DB_USER=app
DB_PASS=app_password_change_me
```

---

### **Pas 2: Adaugă Coloana în Baza de Date** ⏳

#### **Opțiunea A: SQL Direct (RECOMANDAT - 2 minute)**

```bash
# Navighează la directorul proiectului
cd /Users/macos/anaconda3/envs/MagFlow

# Rulează scriptul SQL
psql -h localhost -U app -d magflow -f scripts/sql/safe_add_manual_reorder_quantity.sql

# SAU dacă folosești Docker:
docker exec -i postgres_container psql -U app -d magflow < scripts/sql/safe_add_manual_reorder_quantity.sql
```

**Ce face scriptul:**
- Verifică dacă coloana există
- Dacă NU există, o adaugă
- Dacă există, skip (safe to run multiple times)
- Adaugă comment explicativ
- Verifică rezultatul

**Expected output:**
```
NOTICE: ✅ Column manual_reorder_quantity added successfully
 column_name              | data_type | is_nullable | column_default
--------------------------+-----------+-------------+----------------
 manual_reorder_quantity  | integer   | YES         | NULL
```

---

#### **Opțiunea B: Alembic Migration (când DB este accesibil)**

```bash
# Verifică heads curente
alembic heads

# Ar trebui să vezi multiple heads (11)

# Rulează migrația
alembic upgrade head

# Verifică că merge-ul s-a aplicat
alembic current

# Ar trebui să vezi: 20251013_merge_heads (head)
```

**Ce face migrația:**
1. Unifică toate cele 11 heads
2. Adaugă `manual_reorder_quantity` column
3. Adaugă unique constraint pe `emag_sync_progress`
4. Adaugă `invoice_name_ro` și `invoice_name_en` columns
5. Adaugă `ean` column și index
6. Adaugă `display_order` column pe suppliers

---

### **Pas 3: Verifică că Coloana A Fost Adăugată** ✅

```sql
-- Conectează-te la PostgreSQL
psql -h localhost -U app -d magflow

-- Verifică coloana
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_schema = 'app' 
  AND table_name = 'inventory_items' 
  AND column_name = 'manual_reorder_quantity';

-- Expected output:
--  column_name              | data_type | is_nullable
-- --------------------------+-----------+-------------
--  manual_reorder_quantity  | integer   | YES
```

**Dacă vezi rezultatul de mai sus:** ✅ **SUCCESS!**

---

### **Pas 4: Restart Backend** 🔄

```bash
# Opțiunea 1: Dacă rulezi ca serviciu
sudo systemctl restart magflow-backend

# Opțiunea 2: Dacă rulezi manual
# Apasă Ctrl+C în terminalul unde rulează backend-ul
# Apoi repornește:
cd /Users/macos/anaconda3/envs/MagFlow
python -m uvicorn app.main:app --reload --port 8010

# Opțiunea 3: Dacă rulezi cu Docker
docker-compose restart backend
```

**Verifică că backend-ul pornește fără erori:**
```bash
# Verifică logs
tail -f logs/app.log

# SAU pentru Docker:
docker-compose logs -f backend
```

**Expected:** Fără erori SQL despre `manual_reorder_quantity`

---

### **Pas 5: Verifică în Browser** 🌐

1. **Deschide aplicația:**
   ```
   http://localhost:5173
   ```

2. **Login** cu credențialele tale

3. **Navighează la:**
   - **Low Stock Suppliers** (`/products/low-stock-suppliers`)
   - SAU **Inventory Management** (`/products/inventory`)

4. **Verifică:**
   - ✅ Pagina se încarcă fără erori
   - ✅ Vezi lista de produse
   - ✅ Vezi coloana "Reorder Qty" cu buton edit (✏️)

5. **Testează Editarea:**
   - Click pe butonul edit (✏️) lângă "Reorder Qty"
   - Modifică valoarea (ex: 150)
   - Click pe Save (💾)
   - **Expected:** Mesaj "Reorder quantity updated successfully!"
   - **Expected:** Valoarea se actualizează
   - **Expected:** Apare tag-ul "Manual" albastru

6. **Testează Reset:**
   - Click pe butonul reset (🔄)
   - **Expected:** Mesaj "Reorder quantity reset to automatic calculation!"
   - **Expected:** Tag-ul "Manual" dispare
   - **Expected:** Valoarea revine la calculul automat

---

### **Pas 6: Testează API Direct** 🔧

```bash
# Test 1: Get low stock products
curl -X GET "http://localhost:8010/api/v1/inventory/low-stock-with-suppliers?skip=0&limit=10&account_type=fbe" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Expected: 200 OK, listă de produse cu manual_reorder_quantity

# Test 2: Update manual reorder quantity
curl -X PATCH "http://localhost:8010/api/v1/inventory/items/123" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"manual_reorder_quantity": 150}'

# Expected: 200 OK, mesaj de succes

# Test 3: Reset to automatic
curl -X PATCH "http://localhost:8010/api/v1/inventory/items/123" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"manual_reorder_quantity": null}'

# Expected: 200 OK, revert la calcul automat
```

---

## ✅ Checklist de Verificare

### **Backend:**
- [ ] Coloana `manual_reorder_quantity` există în DB
- [ ] Backend pornește fără erori
- [ ] Endpoint `/inventory/low-stock-with-suppliers` funcționează
- [ ] Endpoint `/inventory/items/{id}` PATCH funcționează
- [ ] Logs nu arată erori SQL

### **Frontend:**
- [ ] Pagina Low Stock Suppliers se încarcă
- [ ] Pagina Inventory Management se încarcă
- [ ] Butonul edit (✏️) apare lângă Reorder Qty
- [ ] Editarea funcționează (Save)
- [ ] Reset funcționează (🔄)
- [ ] Tag-ul "Manual" apare când e setat manual
- [ ] Mesajele de succes/eroare apar corect

### **Funcționalitate:**
- [ ] Pot seta o valoare manuală
- [ ] Valoarea manuală are prioritate față de calculul automat
- [ ] Pot reseta la calculul automat
- [ ] Modificările se salvează în DB
- [ ] Modificările persistă după refresh

---

## 🐛 Troubleshooting

### **Problema 1: "Column does not exist"**

**Simptom:**
```
sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError: 
column inventory_items.manual_reorder_quantity does not exist
```

**Soluție:**
```bash
# Rulează scriptul SQL
psql -h localhost -U app -d magflow -f scripts/sql/safe_add_manual_reorder_quantity.sql

# Apoi restart backend
```

---

### **Problema 2: "Cannot connect to database"**

**Simptom:**
```
socket.gaierror: [Errno 8] nodename nor servname provided
```

**Soluție:**
```bash
# Verifică că PostgreSQL rulează
pg_isready -h localhost -p 5432

# Verifică credențialele în .env
cat .env | grep DB_

# Verifică că poți conecta manual
psql -h localhost -U app -d magflow -c "SELECT 1"
```

---

### **Problema 3: "Multiple heads"**

**Simptom:**
```
alembic upgrade head
ERROR: Multiple heads exist
```

**Soluție:**
```bash
# Verifică heads
alembic heads

# Ar trebui să vezi 11 heads

# Rulează migrația de merge
alembic upgrade 20251013_merge_heads

# Verifică că acum e doar un head
alembic heads
```

---

### **Problema 4: Frontend nu se actualizează**

**Simptom:**
- Editarea nu funcționează
- Butonul edit nu apare

**Soluție:**
```bash
# 1. Hard refresh în browser
# Chrome/Firefox: Ctrl+Shift+R (sau Cmd+Shift+R pe Mac)

# 2. Clear cache
# Chrome: DevTools → Application → Clear storage

# 3. Restart frontend dev server
cd admin-frontend
npm run dev
```

---

## 📊 Verificare Finală

După deployment, verifică următoarele:

### **1. Database Schema**
```sql
-- Verifică toate coloanele noi
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_schema = 'app' 
  AND table_name IN ('inventory_items', 'products', 'suppliers', 'emag_products_v2')
  AND column_name IN (
    'manual_reorder_quantity',
    'invoice_name_ro',
    'invoice_name_en',
    'display_order',
    'ean'
  )
ORDER BY table_name, column_name;
```

**Expected:** 5 rânduri (toate coloanele noi)

---

### **2. Indexes**
```sql
-- Verifică indexurile noi
SELECT 
    schemaname,
    tablename,
    indexname
FROM pg_indexes
WHERE schemaname = 'app'
  AND indexname IN (
    'idx_emag_products_ean',
    'ix_app_suppliers_display_order'
  );
```

**Expected:** 2 rânduri (ambele indexuri)

---

### **3. Constraints**
```sql
-- Verifică constraint-ul nou
SELECT 
    conname,
    contype,
    conrelid::regclass AS table_name
FROM pg_constraint
WHERE conname = 'uq_emag_sync_progress_sync_log_id';
```

**Expected:** 1 rând (constraint-ul unique)

---

### **4. Migration History**
```bash
# Verifică că migrația s-a aplicat
alembic current

# Expected: 20251013_merge_heads (head)

# Verifică heads
alembic heads

# Expected: doar un head
```

---

## 🎉 Success Criteria

Deployment-ul este considerat **SUCCESS** dacă:

1. ✅ Toate coloanele noi există în DB
2. ✅ Backend pornește fără erori
3. ✅ Frontend se încarcă fără erori
4. ✅ Editarea reorder quantity funcționează
5. ✅ Reset la automat funcționează
6. ✅ Tag-ul "Manual" apare corect
7. ✅ Modificările persistă după refresh
8. ✅ API-urile returnează 200 OK
9. ✅ Logs nu arată erori
10. ✅ Alembic heads = 1 (unified)

---

## 📞 Support

### **Documentație Disponibilă:**
1. `DEPLOYMENT_GUIDE_2025_10_13.md` - Acest fișier
2. `MANUAL_REORDER_QUANTITY_FEATURE.md` - Feature documentation
3. `MIGRATION_CONSOLIDATION_2025_10_13.md` - Migration consolidation
4. `MIGRATION_FIX_AND_ANALYSIS_2025_10_13.md` - Migration analysis
5. `FINAL_VERIFICATION_REPORT_2025_10_13.md` - Complete verification

### **Scripts Disponibile:**
1. `scripts/sql/safe_add_manual_reorder_quantity.sql` - SQL direct
2. `scripts/add_manual_reorder_column.py` - Python script
3. `alembic/versions/20251013_merge_heads_add_manual_reorder.py` - Alembic migration

---

## 🔄 Rollback Plan (Dacă Ceva Merge Greșit)

### **Rollback Database:**
```bash
# Opțiunea 1: Downgrade Alembic
alembic downgrade -1

# Opțiunea 2: SQL Manual
psql -h localhost -U app -d magflow << EOF
ALTER TABLE app.inventory_items DROP COLUMN IF EXISTS manual_reorder_quantity;
EOF
```

### **Rollback Code:**
```bash
# Revert la commit-ul anterior
git log --oneline | head -5
git revert 3c77e641  # Sau commit-ul problematic
git push
```

### **Rollback Frontend:**
```bash
cd admin-frontend
git checkout HEAD~1 src/pages/products/LowStockSuppliers.tsx
git checkout HEAD~1 src/pages/products/Inventory.tsx
npm run build
```

---

## 📅 Timeline Estimat

| Pas | Timp Estimat | Status |
|-----|--------------|--------|
| 1. Verifică credențiale | 1 min | ⏳ |
| 2. Rulează SQL | 2 min | ⏳ |
| 3. Verifică coloana | 1 min | ⏳ |
| 4. Restart backend | 2 min | ⏳ |
| 5. Verifică în browser | 5 min | ⏳ |
| 6. Testează API | 3 min | ⏳ |
| **TOTAL** | **~15 min** | ⏳ |

---

## ✅ Status Final

**Pregătit pentru deployment:** ✅ **DA**

**Riscuri:** ⚠️ **MINIME**
- Toate modificările sunt backward compatible
- Safety checks în toate operațiile
- Rollback plan disponibil
- Documentație completă

**Recomandare:** 🚀 **DEPLOY NOW**

---

**Data:** 13 Octombrie 2025, 01:45 AM  
**Autor:** Cascade AI  
**Versiune:** 1.0.0
