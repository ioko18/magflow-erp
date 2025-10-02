# eMAG Product Sync - Testing Guide

## ✅ Status: All Systems Operational

**Date:** 2025-10-01  
**Containers:** All healthy ✓

```
✓ magflow_app      - FastAPI Backend (Port 8000)
✓ magflow_worker   - Celery Worker
✓ magflow_beat     - Celery Beat Scheduler
✓ magflow_db       - PostgreSQL 16 (Port 5433)
✓ magflow_redis    - Redis 7 (Port 6379)
```

---

## 🧪 Manual Testing Steps

### 1. **Test Connection to eMAG API**

**Frontend:**
1. Navigate to: http://localhost:8000 (or your admin frontend URL)
2. Go to **eMAG Product Sync V2** page
3. Click **Test Connection** for MAIN account
4. Click **Test Connection** for FBE account
5. ✅ Both should show "Connected" with green checkmark

**API:**
```bash
# Test MAIN account
curl -X POST "http://localhost:8000/api/v1/emag/products/test-connection?account_type=main" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test FBE account
curl -X POST "http://localhost:8000/api/v1/emag/products/test-connection?account_type=fbe" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response:**
```json
{
  "status": "success",
  "message": "Connection to main account successful",
  "data": {
    "account_type": "main",
    "base_url": "https://marketplace-api.emag.ro/api-3",
    "total_products": 2545
  }
}
```

---

### 2. **Start Product Synchronization**

**Frontend:**
1. Configure sync options:
   - **Account Type:** Both (MAIN + FBE)
   - **Mode:** Incremental
   - **Max Pages:** 5 (for testing)
   - **Conflict Strategy:** eMAG Priority
   - **Run in Background:** Yes
2. Click **Start Incremental Sync - BOTH**
3. ✅ Progress bar should appear showing sync progress
4. ✅ Should complete without errors in ~2-5 minutes

**API:**
```bash
curl -X POST "http://localhost:8000/api/v1/emag/products/sync" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_type": "both",
    "mode": "incremental",
    "max_pages": 5,
    "items_per_page": 100,
    "include_inactive": false,
    "conflict_strategy": "emag_priority",
    "run_async": true
  }'
```

---

### 3. **Monitor Sync Progress**

**Frontend:**
- Auto-refresh is enabled (every 3 seconds during sync)
- Watch the progress bar and statistics update
- Check "Sync History" tab for completed syncs

**API:**
```bash
# Get current sync status
curl "http://localhost:8000/api/v1/emag/products/status" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response (while running):**
```json
{
  "is_running": true,
  "current_sync": {
    "id": "abc-123",
    "account_type": "both",
    "operation": "incremental_sync",
    "started_at": "2025-10-01T15:30:00",
    "total_items": 500,
    "processed_items": 250
  },
  "recent_syncs": [...]
}
```

---

### 4. **Test Cleanup Stuck Syncs**

**Scenario:** If a sync runs for more than 15 minutes (stuck)

**Frontend:**
1. If sync is running > 15 min, **"Cleanup Stuck"** button appears
2. Click the button
3. Confirm the action
4. ✅ Stuck syncs are marked as "failed"

**API:**
```bash
curl -X POST "http://localhost:8000/api/v1/emag/products/cleanup-stuck-syncs?timeout_minutes=15" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response:**
```json
{
  "status": "success",
  "message": "Cleaned up 2 stuck synchronizations",
  "data": {
    "cleaned_count": 2,
    "timeout_minutes": 15,
    "sync_ids": ["61a0ca43-...", "2f590328-..."]
  }
}
```

---

### 5. **Verify Synced Products**

**Frontend:**
1. Go to **"Synced Products"** tab
2. Use filters:
   - Search by SKU or name
   - Filter by account (MAIN/FBE)
3. Click **Export CSV** to download products
4. Click eye icon to view product details

**API:**
```bash
# Get synced products
curl "http://localhost:8000/api/v1/emag/products/products?limit=20&skip=0" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Search products
curl "http://localhost:8000/api/v1/emag/products/products?search=laptop&account_type=main" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 6. **Check Statistics**

**Frontend:**
- Dashboard shows:
  - Total Products
  - MAIN Account products
  - FBE Account products
  - Sync status (Running/Idle)

**API:**
```bash
curl "http://localhost:8000/api/v1/emag/products/statistics" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response:**
```json
{
  "products_by_account": {
    "main": 1523,
    "fbe": 1022
  },
  "total_products": 2545,
  "recent_syncs": [
    {
      "id": "...",
      "account_type": "both",
      "status": "completed",
      "created_items": 150,
      "updated_items": 350,
      "failed_items": 0,
      "duration_seconds": 245.5
    }
  ]
}
```

---

## 🔍 Verification Checklist

### Database Checks

```sql
-- Check synced products count
SELECT account_type, COUNT(*) 
FROM emag_products_v2 
GROUP BY account_type;

-- Check recent sync logs
SELECT id, account_type, operation, status, 
       created_items, updated_items, failed_items, duration_seconds
FROM emag_sync_logs 
WHERE sync_type = 'products'
ORDER BY started_at DESC 
LIMIT 10;

-- Check for stuck syncs
SELECT id, account_type, started_at, 
       EXTRACT(EPOCH FROM (NOW() - started_at))/60 as minutes_running
FROM emag_sync_logs 
WHERE status = 'running' 
  AND sync_type = 'products';
```

### Container Health

```bash
# Check all containers
docker ps

# Check app logs
docker logs magflow_app --tail 50

# Check worker logs
docker logs magflow_worker --tail 50

# Check beat logs
docker logs magflow_beat --tail 50

# Check for errors
docker logs magflow_worker 2>&1 | grep -i error
```

---

## 🐛 Troubleshooting

### Issue: Sync stuck at 0%

**Solution:**
1. Check API credentials in `.env` file
2. Test connection to eMAG API
3. Check worker logs: `docker logs magflow_worker`
4. Restart worker: `docker restart magflow_worker`

### Issue: "created_at column does not exist" error

**Status:** ✅ **FIXED** in this release
- Removed `created_at` from `emag_sync_progress` insert

### Issue: "RuntimeError: Task got Future attached to different loop"

**Status:** ✅ **FIXED** in this release
- Implemented `run_async()` helper with `nest-asyncio`

### Issue: Sync running forever

**Status:** ✅ **FIXED** in this release
- Added 10-minute timeout
- Added cleanup endpoint for stuck syncs

---

## 📊 Expected Performance

### Incremental Sync (Recommended)
- **Duration:** 2-5 minutes for 500 products
- **API Calls:** ~5-10 requests
- **Memory:** ~200-300 MB
- **CPU:** Low (< 20%)

### Full Sync
- **Duration:** 10-30 minutes for 2500 products
- **API Calls:** ~25-50 requests
- **Memory:** ~300-500 MB
- **CPU:** Medium (20-40%)

---

## 🎯 Success Criteria

✅ **All tests pass:**
- [ ] Connection tests successful for both accounts
- [ ] Sync completes without errors
- [ ] Progress tracking works correctly
- [ ] Products appear in database
- [ ] Statistics are accurate
- [ ] Cleanup endpoint works
- [ ] No database errors in logs
- [ ] No event loop errors in logs
- [ ] Timeout prevents infinite loops

✅ **Performance:**
- [ ] Sync completes within expected time
- [ ] No memory leaks
- [ ] CPU usage is reasonable

✅ **UI/UX:**
- [ ] Progress bar updates in real-time
- [ ] Notifications appear for all actions
- [ ] Filters and search work correctly
- [ ] Export CSV works

---

## 📞 Support

If you encounter any issues:

1. **Check logs:** `docker logs magflow_worker --tail 100`
2. **Check database:** Run SQL queries above
3. **Restart services:** `docker-compose restart`
4. **Full rebuild:** `docker-compose down && docker-compose up -d --build`

---

**Last Updated:** 2025-10-01  
**Version:** 2.0 (with fixes)  
**Status:** Production Ready ✅
