# Inventory Optimization Deployment Guide

## 📋 Overview

This guide covers the deployment of inventory optimization features including:
- Database indexing for improved query performance
- Redis caching for reduced database load
- New search endpoint
- Enhanced Excel export functionality

**Estimated Deployment Time**: 30-45 minutes  
**Downtime Required**: ~5 minutes (for database migrations)

---

## 🎯 Pre-Deployment Checklist

### 1. Environment Verification
- [ ] PostgreSQL 12+ running
- [ ] Redis 6+ running and accessible
- [ ] Python 3.11+ installed
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Database backup created
- [ ] Staging environment tested

### 2. Configuration Check
```bash
# Verify environment variables
echo $DATABASE_URL
echo $REDIS_URL

# Test database connection
psql $DATABASE_URL -c "SELECT version();"

# Test Redis connection
redis-cli -u $REDIS_URL ping
```

### 3. Backup Creation
```bash
# Create database backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Verify backup
ls -lh backup_*.sql
```

---

## 🚀 Deployment Steps

### Step 1: Code Deployment

#### 1.1 Pull Latest Code
```bash
cd /Users/macos/anaconda3/envs/MagFlow
git pull origin main
```

#### 1.2 Install Dependencies
```bash
# Activate virtual environment
source venv/bin/activate  # or: conda activate MagFlow

# Install/update dependencies
pip install -r requirements.txt

# Verify openpyxl is installed (for Excel export)
pip show openpyxl
```

#### 1.3 Verify Code Changes
```bash
# Check modified files
git diff HEAD~1 --name-only

# Key files to verify:
# - app/api/v1/endpoints/inventory/emag_inventory.py
# - app/services/inventory/inventory_cache_service.py
# - alembic/versions/add_inventory_indexes_2025_10_10.py
```

---

### Step 2: Database Migration

#### 2.1 Review Migration
```bash
# Check current migration status
alembic current

# Review pending migrations
alembic history

# Preview migration SQL (dry run)
alembic upgrade head --sql > migration_preview.sql
cat migration_preview.sql
```

#### 2.2 Apply Migration
```bash
# Apply database indexes
alembic upgrade head

# Verify indexes were created
psql $DATABASE_URL -c "
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'emag_products_v2' 
ORDER BY indexname;
"
```

**Expected Indexes**:
- `ix_emag_products_v2_stock_quantity`
- `ix_emag_products_v2_account_type`
- `ix_emag_products_v2_sku`
- `ix_emag_products_v2_part_number_key`
- `ix_emag_products_v2_updated_at`
- `ix_emag_products_v2_is_active`
- `ix_emag_products_v2_account_stock`
- `ix_emag_products_v2_sku_account`
- `ix_emag_products_v2_name_trgm`

#### 2.3 Analyze Tables
```bash
# Update table statistics for query planner
psql $DATABASE_URL -c "ANALYZE emag_products_v2;"
```

---

### Step 3: Application Restart

#### 3.1 Graceful Shutdown
```bash
# If using systemd
sudo systemctl stop magflow-api

# If using supervisor
sudo supervisorctl stop magflow-api

# If running manually
pkill -TERM -f "uvicorn app.main:app"
```

#### 3.2 Start Application
```bash
# If using systemd
sudo systemctl start magflow-api
sudo systemctl status magflow-api

# If using supervisor
sudo supervisorctl start magflow-api
sudo supervisorctl status magflow-api

# If running manually
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### 3.3 Verify Startup
```bash
# Check application logs
tail -f /var/log/magflow/app.log

# Verify health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "version": "1.1.0"}
```

---

### Step 4: Verification & Testing

#### 4.1 Smoke Tests
```bash
# Test statistics endpoint
curl -X GET "http://localhost:8000/api/v1/emag-inventory/statistics" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test new search endpoint
curl -X GET "http://localhost:8000/api/v1/emag-inventory/search?query=ABC" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test Excel export
curl -X GET "http://localhost:8000/api/v1/emag-inventory/export/low-stock-excel" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o test_export.xlsx

# Verify Excel file
file test_export.xlsx
# Expected: Microsoft Excel 2007+
```

#### 4.2 Performance Testing
```bash
# Run performance test script
python scripts/performance/check_inventory_performance.py \
  --url http://localhost:8000 \
  --token YOUR_TOKEN \
  --iterations 10
```

**Expected Results**:
- Statistics endpoint: <100ms (cached), <500ms (uncached)
- Search endpoint: <200ms (cached), <800ms (uncached)
- Low stock endpoint: <300ms with indexes

#### 4.3 Cache Verification
```bash
# Check Redis for cached data
redis-cli -u $REDIS_URL

# List inventory cache keys
KEYS inventory:*

# Check a specific cache entry
GET inventory:stats:all

# Verify TTL
TTL inventory:stats:all
# Expected: ~300 seconds (5 minutes)
```

---

### Step 5: Monitoring Setup

#### 5.1 Database Monitoring
```sql
-- Monitor query performance
SELECT 
    query,
    calls,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
WHERE query LIKE '%emag_products_v2%'
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Monitor index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'emag_products_v2'
ORDER BY idx_scan DESC;
```

#### 5.2 Cache Monitoring
```bash
# Redis stats
redis-cli -u $REDIS_URL INFO stats

# Monitor cache hit rate
redis-cli -u $REDIS_URL INFO stats | grep keyspace_hits
redis-cli -u $REDIS_URL INFO stats | grep keyspace_misses

# Calculate hit rate
# hit_rate = hits / (hits + misses) * 100
```

#### 5.3 Application Monitoring
```bash
# Check application metrics
curl http://localhost:8000/metrics

# Monitor response times
curl http://localhost:8000/api/v1/emag-inventory/statistics \
  -w "\nTime: %{time_total}s\n" \
  -o /dev/null -s
```

---

## 🔄 Rollback Procedure

If issues occur, follow this rollback procedure:

### 1. Rollback Database Migration
```bash
# Rollback to previous migration
alembic downgrade -1

# Verify rollback
alembic current
```

### 2. Rollback Code
```bash
# Revert to previous version
git checkout HEAD~1

# Restart application
sudo systemctl restart magflow-api
```

### 3. Restore Database (if needed)
```bash
# Stop application
sudo systemctl stop magflow-api

# Restore from backup
psql $DATABASE_URL < backup_YYYYMMDD_HHMMSS.sql

# Restart application
sudo systemctl start magflow-api
```

---

## 📊 Post-Deployment Validation

### 1. Functional Tests
- [ ] Statistics endpoint returns data
- [ ] Search endpoint works with various queries
- [ ] Excel export generates valid files
- [ ] Caching is working (check response times)
- [ ] All filters work correctly

### 2. Performance Tests
- [ ] Query response times improved
- [ ] Cache hit rate >60% after warm-up
- [ ] Database load reduced
- [ ] No memory leaks
- [ ] No error rate increase

### 3. User Acceptance
- [ ] Frontend loads inventory page
- [ ] Export button works
- [ ] Search is fast and accurate
- [ ] No user-reported issues

---

## 🐛 Troubleshooting

### Issue: Migration Fails

**Symptoms**: Alembic upgrade fails with error

**Solution**:
```bash
# Check current state
alembic current

# Check for conflicts
alembic history

# Manual fix if needed
psql $DATABASE_URL
# Then manually create indexes or fix conflicts

# Stamp migration as complete
alembic stamp head
```

### Issue: Indexes Not Used

**Symptoms**: Queries still slow after migration

**Solution**:
```sql
-- Force analyze
ANALYZE emag_products_v2;

-- Check if indexes exist
\d emag_products_v2

-- Check query plan
EXPLAIN ANALYZE
SELECT * FROM emag_products_v2 
WHERE stock_quantity <= 20 
AND account_type = 'MAIN';

-- If not using index, check statistics
SELECT * FROM pg_stats 
WHERE tablename = 'emag_products_v2';
```

### Issue: Cache Not Working

**Symptoms**: All responses show `"cached": false`

**Solution**:
```bash
# Check Redis connection
redis-cli -u $REDIS_URL ping

# Check application logs
tail -f /var/log/magflow/app.log | grep -i cache

# Verify REDIS_ENABLED setting
echo $REDIS_ENABLED

# Test cache manually
redis-cli -u $REDIS_URL SET test:key "test value"
redis-cli -u $REDIS_URL GET test:key
```

### Issue: Excel Export Fails

**Symptoms**: 500 error on export endpoint

**Solution**:
```bash
# Verify openpyxl is installed
pip show openpyxl

# Reinstall if needed
pip install --force-reinstall openpyxl

# Check application logs
tail -f /var/log/magflow/app.log | grep -i excel

# Test with small dataset
curl -X GET "http://localhost:8000/api/v1/emag-inventory/export/low-stock-excel?limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 📈 Performance Benchmarks

### Before Optimization
- Statistics endpoint: 2-5 seconds
- Low stock query: 3-8 seconds
- Search: 1-3 seconds
- Database CPU: 60-80%

### After Optimization (Expected)
- Statistics endpoint: 0.01-0.5 seconds (90-99% improvement)
- Low stock query: 0.2-0.8 seconds (85-95% improvement)
- Search: 0.05-0.3 seconds (85-95% improvement)
- Database CPU: 20-40% (50% reduction)

### Cache Performance (Expected)
- Cache hit rate: 60-80% after warm-up
- Cache response time: <50ms
- Database load reduction: 50-70%

---

## 🔐 Security Considerations

### 1. Database Access
- Ensure migration user has CREATE INDEX permission
- Verify connection is encrypted (SSL)
- Audit migration logs

### 2. Cache Security
- Redis should not be publicly accessible
- Use Redis AUTH if available
- Monitor for cache poisoning

### 3. API Security
- All endpoints require authentication
- Rate limiting is enforced
- Audit logs enabled

---

## 📝 Maintenance

### Daily
- Monitor cache hit rate
- Check error logs
- Verify response times

### Weekly
- Review slow query logs
- Analyze index usage
- Check cache memory usage

### Monthly
- Vacuum and analyze database
- Review and optimize queries
- Update performance benchmarks

---

## 📞 Support

### Deployment Issues
- Check logs: `/var/log/magflow/app.log`
- Database logs: `/var/log/postgresql/`
- Redis logs: `/var/log/redis/`

### Performance Issues
- Run performance test script
- Check database query stats
- Monitor cache hit rate

### Contact
- **DevOps**: devops@magflow.com
- **Backend Team**: backend@magflow.com
- **On-Call**: +40-XXX-XXX-XXX

---

## ✅ Deployment Checklist

### Pre-Deployment
- [ ] Code reviewed and approved
- [ ] Tests passing in CI/CD
- [ ] Staging deployment successful
- [ ] Database backup created
- [ ] Rollback plan documented

### Deployment
- [ ] Code deployed
- [ ] Dependencies installed
- [ ] Database migration applied
- [ ] Application restarted
- [ ] Smoke tests passed

### Post-Deployment
- [ ] Performance tests passed
- [ ] Monitoring configured
- [ ] Documentation updated
- [ ] Team notified
- [ ] Deployment logged

---

**Deployment Date**: 2025-10-10  
**Version**: 1.1.0  
**Status**: ✅ Ready for Production
