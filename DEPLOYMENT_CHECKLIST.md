# 🚀 Deployment Checklist: Sincronizare Nume Chinezești

## Pre-Deployment

### Backend Preparation
- [ ] Verifică că Python version este 3.10+
  ```bash
  python --version
  ```

- [ ] Verifică imports
  ```bash
  python -c "from app.core.utils.chinese_text_utils import contains_chinese; print('✅ OK')"
  ```

- [ ] Rulează teste unitare
  ```bash
  pytest tests/core/test_chinese_text_utils.py -v
  ```

- [ ] Verifică database connection
  ```bash
  python -c "from app.db.session import get_async_db; print('✅ DB OK')"
  ```

### Frontend Preparation
- [ ] Rebuild TypeScript
  ```bash
  cd admin-frontend && npm run build
  ```

- [ ] Verifică că nu sunt erori de compilare
  ```bash
  npm run lint
  ```

- [ ] Verifică imports în DevTools
  - Deschide DevTools (F12)
  - Verifică Console pentru erori

---

## Deployment Steps

### 1. Backend Deployment

#### Step 1.1: Copy Files
```bash
# Utility module
cp app/core/utils/chinese_text_utils.py /production/app/core/utils/

# Service layer
cp app/services/suppliers/chinese_name_sync_service.py /production/app/services/suppliers/

# Updated endpoint
cp app/api/v1/endpoints/suppliers/suppliers.py /production/app/api/v1/endpoints/suppliers/

# Migration script
cp scripts/sync_all_chinese_names.py /production/scripts/
chmod +x /production/scripts/sync_all_chinese_names.py

# Tests
cp tests/core/test_chinese_text_utils.py /production/tests/core/
```

#### Step 1.2: Verify Backend
```bash
# SSH to production server
ssh user@production-server

# Navigate to app directory
cd /production

# Verify imports
python -c "from app.core.utils.chinese_text_utils import contains_chinese; print('✅ Backend OK')"

# Run tests
pytest tests/core/test_chinese_text_utils.py -v

# Check endpoint
curl -X POST http://localhost:8000/suppliers/1/products/sync-chinese-names \
  -H "Authorization: Bearer TEST_TOKEN" \
  -H "Content-Type: application/json"
```

#### Step 1.3: Restart Backend
```bash
# If using systemd
sudo systemctl restart magflow-api

# If using Docker
docker restart magflow-api

# If using manual process
pkill -f "uvicorn app.main:app"
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 &
```

### 2. Frontend Deployment

#### Step 2.1: Build Frontend
```bash
cd admin-frontend

# Install dependencies (if needed)
npm install

# Build
npm run build

# Verify build output
ls -la dist/
```

#### Step 2.2: Deploy Frontend
```bash
# Copy build to server
scp -r dist/* user@production-server:/var/www/magflow-admin/

# Or if using Docker
docker build -t magflow-admin:latest .
docker push magflow-admin:latest
docker pull magflow-admin:latest
docker restart magflow-admin
```

#### Step 2.3: Verify Frontend
```bash
# Open browser
https://production-server/admin

# Check Console (F12) for errors
# Look for "Sincronizează CN" button in "Produse Furnizori" page
```

### 3. Database Preparation (Optional)

#### Step 3.1: Backup Database
```bash
# Create backup
pg_dump -U postgres magflow > magflow_backup_$(date +%Y%m%d_%H%M%S).sql

# Or using Docker
docker exec magflow-db pg_dump -U postgres magflow > magflow_backup_$(date +%Y%m%d_%H%M%S).sql
```

#### Step 3.2: Verify Data
```bash
# Check if there are products with Chinese names
psql -U postgres -d magflow -c "
SELECT COUNT(*) as total,
       COUNT(CASE WHEN supplier_product_chinese_name IS NOT NULL THEN 1 END) as with_chinese_name,
       COUNT(CASE WHEN supplier_product_chinese_name IS NULL THEN 1 END) as without_chinese_name
FROM app.supplier_products;
"
```

---

## Post-Deployment

### Verification Steps

#### Step 1: Test Manual Sync (UI)
```
1. Open "Produse Furnizori"
2. Select supplier (e.g., TZT)
3. Click "Sincronizează CN" button
4. Confirm in dialog
5. Wait for success message
6. Verify: "Sincronizare completă! X produse actualizate, Y sărite."
```

#### Step 2: Test Product Details Modal
```
1. Open "Produse Furnizori"
2. Find product with Chinese name
3. Click "Vezi detalii"
4. Verify: Chinese name displays correctly in "Nume Chinezesc:" field
5. Verify: Not showing "Adaugă nume chinezesc"
```

#### Step 3: Test Retroactive Sync (Script)
```bash
# Run script for all suppliers
python scripts/sync_all_chinese_names.py

# Verify output shows synchronized count
# Example: "✅ Synced: 156, ⏭️ Skipped: 89"
```

#### Step 4: Check Logs
```bash
# Backend logs
tail -f /var/log/magflow/app.log | grep -i "sync\|chinese"

# Or if using Docker
docker logs -f magflow-api | grep -i "sync\|chinese"

# Look for:
# - "Synchronized X Chinese names for supplier Y"
# - No ERROR messages
```

#### Step 5: Database Verification
```bash
# Check if synchronization worked
psql -U postgres -d magflow -c "
SELECT id, supplier_product_name, supplier_product_chinese_name
FROM app.supplier_products
WHERE supplier_product_chinese_name IS NOT NULL
LIMIT 10;
"
```

---

## Rollback Plan

### If Something Goes Wrong

#### Step 1: Identify Issue
```bash
# Check logs
tail -f /var/log/magflow/app.log

# Check database
psql -U postgres -d magflow -c "SELECT COUNT(*) FROM app.supplier_products;"
```

#### Step 2: Rollback Backend
```bash
# Restore previous version
git checkout HEAD~1 app/api/v1/endpoints/suppliers/suppliers.py

# Restart backend
sudo systemctl restart magflow-api
```

#### Step 3: Rollback Frontend
```bash
# Restore previous build
scp -r /backup/dist/* user@production-server:/var/www/magflow-admin/

# Or restart container
docker restart magflow-admin
```

#### Step 4: Restore Database (if needed)
```bash
# Restore from backup
psql -U postgres -d magflow < magflow_backup_YYYYMMDD_HHMMSS.sql

# Or if using Docker
docker exec magflow-db psql -U postgres -d magflow < magflow_backup_YYYYMMDD_HHMMSS.sql
```

---

## Monitoring

### Post-Deployment Monitoring

#### Daily Checks (First Week)
- [ ] Check application logs for errors
- [ ] Verify sync button works
- [ ] Test modal display
- [ ] Monitor database performance

#### Weekly Checks
- [ ] Review sync statistics
- [ ] Check for any error patterns
- [ ] Verify data consistency
- [ ] Performance metrics

#### Monthly Checks
- [ ] Run full test suite
- [ ] Review logs for issues
- [ ] Backup database
- [ ] Update documentation

### Metrics to Monitor
```
- Sync success rate
- Average sync time
- Number of products synced
- Error count
- Database query performance
```

---

## Troubleshooting

### Issue: Button doesn't appear
**Solution:**
1. Clear browser cache (Ctrl+Shift+Delete)
2. Rebuild frontend: `npm run build`
3. Restart frontend service

### Issue: Sync fails with 404
**Solution:**
1. Verify backend is running
2. Check endpoint: `curl http://localhost:8000/suppliers/1/products/sync-chinese-names`
3. Verify authentication token

### Issue: No products synced
**Solution:**
1. Check if products have Chinese names: `SELECT COUNT(*) FROM app.supplier_products WHERE supplier_product_name ~ '[\\u4e00-\\u9fff]'`
2. Run script with debug: `python scripts/sync_all_chinese_names.py --supplier-id 1`
3. Check logs for errors

### Issue: Database connection error
**Solution:**
1. Verify database is running
2. Check connection string
3. Verify credentials
4. Check firewall rules

---

## Sign-Off

### Pre-Deployment Sign-Off
- [ ] Backend developer: Code reviewed and tested
- [ ] Frontend developer: UI tested and verified
- [ ] QA: All tests passed
- [ ] DevOps: Infrastructure ready

### Post-Deployment Sign-Off
- [ ] Deployment completed successfully
- [ ] All verification steps passed
- [ ] No critical errors in logs
- [ ] Users can access new features
- [ ] Rollback plan documented

---

## Documentation

### Files to Reference
1. `SOLUTION_SUMMARY.md` - Overview
2. `IMPLEMENTATION_GUIDE.md` - Detailed guide
3. `CHINESE_NAME_SYNC_SOLUTION.md` - Technical details
4. `DEPLOYMENT_CHECKLIST.md` - This file

### Support Contacts
- Backend: [Backend Team]
- Frontend: [Frontend Team]
- DevOps: [DevOps Team]
- Database: [DBA Team]

---

## Timeline

### Estimated Timeline
- **Pre-Deployment:** 30 minutes
- **Backend Deployment:** 15 minutes
- **Frontend Deployment:** 15 minutes
- **Verification:** 30 minutes
- **Total:** ~90 minutes

### Recommended Deployment Window
- **Time:** Off-peak hours (e.g., 2 AM - 4 AM)
- **Duration:** 2 hours
- **Rollback Time:** 30 minutes

---

**Deployment Date:** [TO BE FILLED]  
**Deployed By:** [TO BE FILLED]  
**Verified By:** [TO BE FILLED]  
**Status:** ⏳ PENDING DEPLOYMENT
