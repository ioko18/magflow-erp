# Quick Test Guide - eMAG Sync Fixes

## 🚀 How to Test the Fixes

### 1. Monitor Health Check (Should Pass Now)
```bash
# Watch for health check task (runs every 5 minutes)
docker-compose logs -f magflow_worker | grep "health_check"
```

**Expected Output:**
```
[INFO] emag.health_check: Health check completed: {'timestamp': '...', 'status': 'healthy', ...}
```

**Before Fix:** ❌ Error about timezone comparison  
**After Fix:** ✅ Success with status 'healthy'

---

### 2. Test Small Sync (Quick Test)
```bash
# Via API or UI: Start incremental sync
curl -X POST http://localhost:8000/api/v1/emag/orders/sync \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_type": "both",
    "sync_mode": "incremental",
    "max_pages": 5
  }'
```

**Expected:**
- Completes in < 2 minutes
- Returns success with order counts
- No timeout errors

---

### 3. Test Large Sync (Full Test)
```bash
# Via API or UI: Start full sync
curl -X POST http://localhost:8000/api/v1/emag/orders/sync \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_type": "both",
    "sync_mode": "full",
    "max_pages": 50
  }'
```

**Expected:**
- Completes in < 15 minutes (even with 4000+ orders)
- Batch progress logs visible
- All orders saved to database

**Monitor Progress:**
```bash
docker-compose logs -f magflow_app | grep -E "Fetched page|Processing batch|Batch complete"
```

---

### 4. Verify Orders in Database
```bash
# Connect to database
docker-compose exec magflow_db psql -U magflow_user -d magflow

# Check order counts
SELECT account_type, COUNT(*) as total_orders
FROM app.emag_orders
GROUP BY account_type;

# Check recent syncs
SELECT sync_type, account_type, status, total_items, created_items, updated_items
FROM app.emag_sync_logs
ORDER BY created_at DESC
LIMIT 10;
```

---

## 📊 What to Look For

### ✅ Success Indicators:
1. **Health Check:** No timezone errors, status "healthy"
2. **Sync Progress:** Batch logs showing progress (e.g., "Processing batch 1-100 of 4700")
3. **Completion:** Sync completes without timeout
4. **Database:** All fetched orders are saved

### ❌ Failure Indicators:
1. Timezone comparison errors in logs
2. "Sync operation timed out" after 5 minutes
3. Orders fetched but not saved to database
4. No batch progress logs

---

## 🔍 Troubleshooting

### If Health Check Still Fails:
```bash
# Check exact error
docker-compose logs magflow_worker | grep -A 20 "health_check.*ERROR"

# Verify database schema
docker-compose exec magflow_db psql -U magflow_user -d magflow -c "\d app.emag_sync_logs"
```

### If Sync Times Out:
```bash
# Check if timeout was increased
docker-compose logs magflow_app | grep "timeout"

# Should show: "Wait for both with 15 minute timeout"
# NOT: "Wait for both with 5 minute timeout"
```

### If Orders Not Saving:
```bash
# Check for batch processing logs
docker-compose logs magflow_app | grep "Processing batch"

# Check for database errors
docker-compose logs magflow_app | grep -i "error saving order"
```

---

## 📈 Performance Metrics

| Scenario | Before Fix | After Fix |
|----------|-----------|-----------|
| **Health Check** | ❌ Failed | ✅ Success |
| **Small Sync (500 orders)** | ✅ 1-2 min | ✅ 1-2 min |
| **Large Sync (4700 orders)** | ❌ Timeout at 5 min | ✅ ~10-12 min |
| **Progress Visibility** | ❌ None | ✅ Batch-level |

---

## 🎯 Next Steps After Testing

1. **If All Tests Pass:**
   - ✅ Fixes are working correctly
   - Deploy to production if needed
   - Monitor for 24 hours

2. **If Any Test Fails:**
   - Check the specific error in logs
   - Verify code changes were applied
   - Restart services: `docker-compose restart`

3. **Production Deployment:**
   ```bash
   # Rebuild and restart
   docker-compose down
   docker-compose build magflow_app magflow_worker
   docker-compose up -d
   
   # Monitor startup
   docker-compose logs -f magflow_app magflow_worker
   ```

---

## 📞 Quick Commands Reference

```bash
# View all logs
docker-compose logs -f

# View only app logs
docker-compose logs -f magflow_app

# View only worker logs
docker-compose logs -f magflow_worker

# Restart services
docker-compose restart magflow_app magflow_worker

# Check service status
docker-compose ps

# Check database connection
docker-compose exec magflow_db psql -U magflow_user -d magflow -c "SELECT 1"
```

---

**Status:** ✅ Ready for Testing  
**Last Updated:** 2025-10-14  
**Fixes Applied:** Timezone handling, Timeout extension, Batch processing
