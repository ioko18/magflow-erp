# Ghid Rapid Deployment: Fix Nume Chinezești

## 🚀 Deployment Rapid (5 minute)

### 1. Verificare Modificări

```bash
cd /Users/macos/anaconda3/envs/MagFlow

# Verifică fișierele modificate
git status

# Ar trebui să vezi:
# - app/api/v1/endpoints/suppliers/suppliers.py
# - admin-frontend/src/pages/suppliers/SupplierMatching.tsx
# - admin-frontend/src/pages/suppliers/SupplierProducts.tsx
```

### 2. Restart Backend

```bash
# Restart container backend
docker-compose restart app

# Verifică că a pornit corect
docker-compose logs -f app --tail 50
```

### 3. Rebuild Frontend (dacă e necesar)

```bash
cd admin-frontend

# Rebuild
npm run build

# Sau restart dev server
npm run dev
```

### 4. Testare Rapidă

#### Test 1: Product Matching
1. Deschide: http://localhost:3000/products/matching
2. Caută un produs cu nume chinezesc
3. Apasă "Vezi Detalii"
4. ✅ Verifică că se afișează numele chinezesc complet

#### Test 2: Produse Furnizori
1. Deschide: http://localhost:3000/suppliers/products
2. Selectează furnizor "TZT"
3. Caută "微波多普勒"
4. Apasă "Vezi detalii" pe un produs
5. ✅ Verifică că se afișează numele chinezesc, nu "Adaugă nume chinezesc"

## 📊 Verificare în Producție

### Checklist Post-Deployment

- [ ] Backend pornit fără erori
- [ ] Frontend încărcat corect
- [ ] Product Matching afișează nume chinezești
- [ ] Supplier Products afișează nume chinezești
- [ ] Search funcționează cu caractere chinezești
- [ ] Nu există erori în console

### Comenzi Verificare

```bash
# Verifică logs backend
docker-compose logs app --tail 100 | grep -i error

# Verifică că API returnează date corecte
curl http://localhost:8010/api/v1/suppliers/1/products?limit=1 | jq '.data.products[0] | {supplier_product_name, supplier_product_chinese_name}'

# Verifică search
curl "http://localhost:8010/api/v1/suppliers/1/products?search=微波" | jq '.data.products | length'
```

## 🔧 Troubleshooting

### Problema: Backend nu pornește

```bash
# Verifică logs
docker-compose logs app

# Restart complet
docker-compose down
docker-compose up -d
```

### Problema: Frontend nu afișează corect

```bash
# Clear cache browser
# Ctrl+Shift+R (Chrome/Firefox)

# Rebuild frontend
cd admin-frontend
rm -rf node_modules/.cache
npm run build
```

### Problema: Search nu funcționează

```bash
# Verifică că backend-ul a fost restartat
docker-compose restart app

# Verifică logs pentru erori SQL
docker-compose logs app | grep -i "sql"
```

## 📅 Migrare Date (Opțional - Recomandată)

### Când să rulezi migrarea?

- ✅ După ce fix-urile sunt testate și funcționează
- ✅ În afara orelor de vârf
- ✅ După un backup complet al bazei de date

### Pași Migrare

```bash
# 1. Backup bază de date
docker exec magflow_db pg_dump -U app magflow > backup_pre_migration_$(date +%Y%m%d_%H%M%S).sql

# 2. Dry-run (nu modifică datele)
python scripts/migrate_chinese_names_standardization.py

# 3. Verifică output-ul dry-run
# Ar trebui să vezi câte produse vor fi migrate

# 4. Execuție reală (DOAR după verificare)
python scripts/migrate_chinese_names_standardization.py --execute

# 5. Verificare post-migrare
docker exec magflow_db psql -U app -d magflow -c "
SELECT 
    COUNT(*) as total,
    COUNT(supplier_product_chinese_name) as with_chinese,
    ROUND(COUNT(supplier_product_chinese_name)::numeric / COUNT(*)::numeric * 100, 1) as percentage
FROM app.supplier_products;
"
```

### Rollback (dacă e necesar)

```bash
# Restaurare din backup
docker exec -i magflow_db psql -U app magflow < backup_pre_migration_YYYYMMDD_HHMMSS.sql
```

## 📈 Monitorizare Post-Deployment

### Metrici de Urmărit

```bash
# 1. Număr de produse cu chinese_name
docker exec magflow_db psql -U app -d magflow -c "
SELECT COUNT(*) FROM app.supplier_products WHERE supplier_product_chinese_name IS NOT NULL;
"

# 2. Verifică că search-ul funcționează
curl -s "http://localhost:8010/api/v1/suppliers/1/products?search=微波" | jq '.data.pagination.total'

# 3. Verifică logs pentru erori
docker-compose logs app --since 1h | grep -i error | wc -l
```

### Alertă Dacă

- ❌ Numărul de erori crește brusc
- ❌ Search-ul returnează 0 rezultate pentru query-uri cunoscute
- ❌ Utilizatorii raportează probleme cu afișarea numelor

## 🎯 Success Criteria

Deployment-ul este considerat reușit dacă:

1. ✅ Backend pornește fără erori
2. ✅ Frontend se încarcă corect
3. ✅ Numele chinezești se afișează în toate paginile
4. ✅ Search-ul funcționează cu caractere chinezești
5. ✅ Nu există regresii în funcționalități existente
6. ✅ Nu există erori în logs

## 📞 Contact

Dacă întâmpini probleme:

1. Verifică documentația:
   - `FIX_CHINESE_NAME_DISPLAY_2025_10_21.md`
   - `FIX_SUPPLIER_PRODUCTS_CHINESE_NAME_2025_10_21.md`
   - `REZUMAT_FIX_NUME_CHINEZESTI_COMPLET_2025_10_21.md`

2. Verifică logs:
   ```bash
   docker-compose logs app --tail 200
   ```

3. Rollback dacă e necesar:
   ```bash
   git checkout HEAD -- app/api/v1/endpoints/suppliers/suppliers.py
   git checkout HEAD -- admin-frontend/src/pages/suppliers/
   docker-compose restart app
   ```

## ⏱️ Timeline Estimat

| Activitate | Durată | Când |
|-----------|--------|------|
| Deployment fix-uri | 5 min | Imediat |
| Testare | 10 min | După deployment |
| Monitorizare | 1 oră | După deployment |
| Backup DB | 5 min | Înainte de migrare |
| Migrare date (dry-run) | 2 min | Când ești pregătit |
| Migrare date (execuție) | 5-10 min | După dry-run |
| Verificare post-migrare | 5 min | După migrare |

**Total timp estimat**: 30-45 minute (inclusiv migrare)

---

**Ultima actualizare**: 21 Octombrie 2025  
**Versiune**: 1.0  
**Status**: ✅ Gata pentru Deployment
