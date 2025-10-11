# eMAG Product Sync - Troubleshooting Guide

**Date:** 2025-10-11  
**Status:** ✅ Enhanced & Fixed  
**Feature:** Improved error handling and diagnostics for eMAG product synchronization

---

## 🎯 Overview

This guide helps you diagnose and fix issues with the eMAG Product Synchronization page.

---

## ✅ Recent Improvements

### What Was Fixed

1. **Enhanced Error Messages** ✅
   - More descriptive error messages
   - Specific guidance for common issues
   - Credential validation hints

2. **Connection Testing** ✅
   - Added "Test Connection" buttons for MAIN and FBE
   - Verify credentials before sync
   - Check API availability

3. **Better Error Display** ✅
   - Last error displayed prominently
   - Closable error alerts
   - Helpful troubleshooting tips

4. **Improved Logging** ✅
   - Detailed backend logging
   - Error type identification
   - Account-specific error tracking

---

## 🔍 Common Issues & Solutions

### Issue 1: "Authentication failed" or "Missing credentials"

**Symptoms:**
- Sync fails immediately
- Error mentions "credentials" or "authentication"
- Test connection fails

**Cause:**
Missing or incorrect eMAG API credentials in environment variables.

**Solution:**

1. **Check Environment Variables**
   ```bash
   # For MAIN account
   echo $EMAG_MAIN_USERNAME
   echo $EMAG_MAIN_PASSWORD
   
   # For FBE account
   echo $EMAG_FBE_USERNAME
   echo $EMAG_FBE_PASSWORD
   ```

2. **Set Missing Variables**
   ```bash
   # In .env file or environment
   EMAG_MAIN_USERNAME=your_main_username
   EMAG_MAIN_PASSWORD=your_main_password
   EMAG_MAIN_BASE_URL=https://marketplace-api.emag.ro/api-3
   
   EMAG_FBE_USERNAME=your_fbe_username
   EMAG_FBE_PASSWORD=your_fbe_password
   EMAG_FBE_BASE_URL=https://marketplace-api.emag.ro/api-3
   ```

3. **Restart Backend**
   ```bash
   docker-compose restart backend
   ```

4. **Test Connection**
   - Go to "Sincronizare Produse eMAG" page
   - Click "Test Conexiune MAIN" or "Test Conexiune FBE"
   - Verify success message

---

### Issue 2: "Timeout" or "Connection error"

**Symptoms:**
- Sync runs for 5+ minutes then fails
- Error mentions "timeout" or "connection"
- Network-related errors

**Cause:**
- Slow network connection
- eMAG API is slow or unavailable
- Too many products to sync at once

**Solution:**

1. **Reduce Sync Scope**
   - The sync uses `max_pages: null` (all pages)
   - Consider implementing pagination limits

2. **Check Network**
   ```bash
   # Test eMAG API connectivity
   curl -I https://marketplace-api.emag.ro/api-3
   ```

3. **Check Backend Logs**
   ```bash
   docker-compose logs -f backend | grep -i "emag\|sync"
   ```

4. **Increase Timeout (if needed)**
   - Current timeout: 5 minutes (300 seconds)
   - Can be increased in frontend code

---

### Issue 3: Sync Starts But Never Completes

**Symptoms:**
- "Sincronizare în Curs" shows indefinitely
- No progress updates
- Status stuck at "running"

**Cause:**
- Backend crashed during sync
- Database connection lost
- Stuck sync record in database

**Solution:**

1. **Check Backend Status**
   ```bash
   docker-compose ps backend
   docker-compose logs backend --tail=100
   ```

2. **Clean Up Stuck Syncs**
   ```bash
   # Via API (if available)
   curl -X POST http://localhost:8000/api/v1/emag/products/cleanup-stuck-syncs \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

3. **Manual Database Cleanup**
   ```sql
   -- Connect to database
   UPDATE emag_sync_logs 
   SET status = 'failed', 
       error_message = 'Manually cancelled - stuck sync'
   WHERE status = 'running' 
     AND started_at < NOW() - INTERVAL '30 minutes';
   ```

4. **Restart Backend**
   ```bash
   docker-compose restart backend
   ```

---

### Issue 4: No Products Showing After Sync

**Symptoms:**
- Sync completes successfully
- Statistics show 0 products
- Products table is empty

**Cause:**
- Products were synced but not committed
- Database transaction issue
- Filtering hiding all products

**Solution:**

1. **Check Database Directly**
   ```sql
   SELECT COUNT(*) FROM emag_products_v2;
   SELECT account_type, COUNT(*) 
   FROM emag_products_v2 
   GROUP BY account_type;
   ```

2. **Clear Filters**
   - Remove search text
   - Set account filter to "All"
   - Refresh page

3. **Check Sync Logs**
   ```sql
   SELECT * FROM emag_sync_logs 
   ORDER BY started_at DESC 
   LIMIT 5;
   ```

4. **Re-run Sync**
   - Try syncing again
   - Check for error messages
   - Monitor backend logs

---

### Issue 5: "Service Error" or Generic Errors

**Symptoms:**
- Vague error messages
- "Service Error" or "Internal Server Error"
- No specific details

**Cause:**
- Backend code error
- Missing dependencies
- Configuration issue

**Solution:**

1. **Check Backend Logs**
   ```bash
   docker-compose logs backend --tail=200 | grep -i error
   ```

2. **Verify Dependencies**
   ```bash
   docker-compose exec backend pip list | grep -i emag
   ```

3. **Check Database Connection**
   ```bash
   docker-compose exec backend python -c "from app.core.database import engine; print('DB OK')"
   ```

4. **Review Configuration**
   - Check `.env` file
   - Verify all required variables set
   - Check database connection string

---

## 🧪 Testing Checklist

Before reporting an issue, test the following:

### Pre-Sync Checks

- [ ] Backend is running (`docker-compose ps`)
- [ ] Database is accessible
- [ ] Environment variables are set
- [ ] Test connection succeeds for target account
- [ ] No stuck syncs in database

### During Sync

- [ ] Progress notifications appear
- [ ] No error messages in console
- [ ] Backend logs show activity
- [ ] Database connections stable

### Post-Sync

- [ ] Success notification appears
- [ ] Statistics update
- [ ] Products appear in table
- [ ] No errors in logs

---

## 📊 Diagnostic Commands

### Check Backend Health

```bash
# Backend status
docker-compose ps backend

# Recent logs
docker-compose logs backend --tail=100

# Follow logs in real-time
docker-compose logs -f backend
```

### Check Database

```bash
# Connect to database
docker-compose exec postgres psql -U magflow -d magflow_db

# Check products
SELECT account_type, COUNT(*), MAX(updated_at) 
FROM emag_products_v2 
GROUP BY account_type;

# Check sync logs
SELECT id, account_type, status, started_at, completed_at, error_message
FROM emag_sync_logs 
ORDER BY started_at DESC 
LIMIT 10;
```

### Test API Endpoints

```bash
# Get auth token first
TOKEN="your_jwt_token_here"

# Test connection
curl -X POST "http://localhost:8000/api/v1/emag/products/test-connection?account_type=main" \
  -H "Authorization: Bearer $TOKEN"

# Get sync status
curl "http://localhost:8000/api/v1/emag/products/status" \
  -H "Authorization: Bearer $TOKEN"

# Get statistics
curl "http://localhost:8000/api/v1/emag/products/statistics" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🔧 Advanced Troubleshooting

### Enable Debug Logging

1. **Backend Logging**
   ```python
   # In app/core/logging.py or .env
   LOG_LEVEL=DEBUG
   ```

2. **Restart Backend**
   ```bash
   docker-compose restart backend
   ```

3. **Monitor Logs**
   ```bash
   docker-compose logs -f backend | grep -i "emag\|sync"
   ```

### Database Query Performance

```sql
-- Check for slow queries
SELECT query, calls, mean_exec_time, max_exec_time
FROM pg_stat_statements
WHERE query LIKE '%emag_products%'
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check table sizes
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename LIKE '%emag%'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Network Diagnostics

```bash
# Test eMAG API from backend container
docker-compose exec backend curl -I https://marketplace-api.emag.ro/api-3

# Check DNS resolution
docker-compose exec backend nslookup marketplace-api.emag.ro

# Test with timeout
docker-compose exec backend timeout 10 curl https://marketplace-api.emag.ro/api-3
```

---

## 📝 Error Message Reference

### Backend Error Messages

| Error Message | Meaning | Solution |
|--------------|---------|----------|
| "Missing credentials for X account" | Environment variables not set | Set EMAG_X_USERNAME and EMAG_X_PASSWORD |
| "Authentication failed" | Invalid credentials | Verify credentials with eMAG |
| "Connection timeout" | Network or API slow | Check network, reduce scope |
| "Rate limit exceeded" | Too many API requests | Wait and retry, implement backoff |
| "Invalid sync configuration" | Bad request parameters | Check sync parameters |
| "Database error" | DB connection issue | Check database health |

### Frontend Error Messages

| Error Message | Meaning | Solution |
|--------------|---------|----------|
| "Timeout: Sincronizarea durează..." | 5-minute timeout reached | Reduce scope or check backend |
| "Nu s-a putut porni sincronizarea" | Generic sync start failure | Check backend logs |
| "Test conexiune eșuat" | Connection test failed | Check credentials and network |

---

## 🎓 Best Practices

### Before Syncing

1. **Test Connection First**
   - Always click "Test Conexiune" before syncing
   - Verify credentials are working
   - Check product count makes sense

2. **Check System Resources**
   - Ensure adequate disk space
   - Check database connections available
   - Monitor memory usage

3. **Review Recent Syncs**
   - Check "Istoric Sincronizări" tab
   - Look for patterns in failures
   - Verify last sync completed

### During Sync

1. **Monitor Progress**
   - Watch progress notifications
   - Check backend logs if suspicious
   - Don't close browser tab

2. **Be Patient**
   - Large syncs take time (2-5 minutes typical)
   - Don't start multiple syncs simultaneously
   - Wait for completion notification

### After Sync

1. **Verify Results**
   - Check statistics updated
   - Browse products table
   - Verify product counts

2. **Review Logs**
   - Check for any warnings
   - Note any failed products
   - Document issues for future reference

---

## 🆘 Getting Help

### Information to Provide

When reporting an issue, include:

1. **Error Message**
   - Exact error text
   - Screenshot if possible

2. **Steps to Reproduce**
   - What you clicked
   - Which account (MAIN/FBE)
   - When it happened

3. **Environment**
   - Backend logs (last 100 lines)
   - Browser console errors
   - Network tab (if relevant)

4. **System State**
   - Recent syncs (from Istoric tab)
   - Current statistics
   - Database product count

### Contact

- **Technical Issues:** Check backend logs first
- **Configuration Help:** Review environment variables
- **Bug Reports:** Include full diagnostic info

---

## ✅ Success Indicators

You know sync is working when:

- ✅ Test connection succeeds
- ✅ Sync completes in 2-5 minutes
- ✅ Success notification appears
- ✅ Statistics update correctly
- ✅ Products appear in table
- ✅ No errors in logs
- ✅ Sync history shows "completed" status

---

**Last Updated:** 2025-10-11  
**Version:** 2.0  
**Status:** ✅ Enhanced with diagnostics
