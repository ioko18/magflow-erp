# MagFlow ERP - eMAG Integration Deployment Guide

**Date:** 2025-09-29  
**Version:** 2.0  
**Status:** ✅ Ready for Deployment

---

## 📋 Overview

This guide provides step-by-step instructions for deploying the enhanced eMAG integration features to the MagFlow ERP system.

---

## 🎯 What's New

### Backend Enhancements
1. ✅ **Complete Orders Sync** - All eMAG API v4.4.8 order fields supported
2. ✅ **Order Validation** - Comprehensive validation conforming to eMAG specs
3. ✅ **Rate Limiting** - 12 RPS for orders, 3 RPS for other operations
4. ✅ **Error Handling** - Custom exceptions with exponential backoff retry
5. ✅ **Monitoring Service** - Real-time health and performance tracking
6. ✅ **Backup Service** - Automated backup and recovery
7. ✅ **Management Endpoints** - New API endpoints for system management

### Database Changes
- ✅ New field: `shipping_tax_voucher_split` in `emag_orders` table
- ✅ Migration ready: `c8e960008812_add_shipping_tax_voucher_split_to_orders.py`

---

## 🚀 Deployment Steps

### Step 1: Backup Current System

```bash
# Create backup of current database
cd /Users/macos/anaconda3/envs/MagFlow
python3 -c "
from app.services.backup_service import BackupService
from app.core.database import get_async_session
import asyncio

async def backup():
    async with get_async_session() as db:
        service = BackupService(db)
        result = await service.create_backup(compress=True)
        print(f'Backup created: {result}')

asyncio.run(backup())
"
```

### Step 2: Apply Database Migration

```bash
# Apply the new migration
cd /Users/macos/anaconda3/envs/MagFlow
alembic upgrade head

# Verify migration
alembic current
```

Expected output:
```
c8e960008812 (head)
```

### Step 3: Verify New Modules

```bash
# Run verification script
python3 verify_implementation.py
```

Expected output:
```
✅ PASS - Module Imports
✅ PASS - Cancellation Reasons
✅ PASS - Order Validation
✅ PASS - Error Classes
✅ PASS - Rate Limiter
✅ PASS - Database Model

Total: 6/6 checks passed
```

### Step 4: Run Tests

```bash
# Run comprehensive tests
python3 -m pytest tests/test_emag_enhancements.py -v

# Expected: 24/24 tests passing
```

### Step 5: Start Backend

```bash
# Option 1: Using start script
./start_dev.sh backend

# Option 2: Using uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Option 3: Using Docker
docker-compose up -d backend
```

### Step 6: Verify Backend Health

```bash
# Check health endpoint
curl http://localhost:8000/health

# Check API docs
open http://localhost:8000/docs
```

### Step 7: Test New Endpoints

```bash
# Get authentication token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@example.com","password":"secret"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Test health endpoint
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/emag/management/health

# Test monitoring metrics
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/emag/management/monitoring/metrics

# Test rate limiter stats
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/emag/management/rate-limiter/stats

# Test backup list
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/emag/management/backup/list
```

### Step 8: Run Integration Tests

```bash
# Run complete integration test
python3 test_integration_complete.py
```

Expected output:
```
✅ PASS - Health Endpoint
✅ PASS - Monitoring Endpoints
✅ PASS - Rate Limiter Endpoints
✅ PASS - Backup Endpoints
✅ PASS - Existing Endpoints

Total: 5/5 test groups passed
```

---

## 📊 New API Endpoints

### Management Endpoints

Base path: `/api/v1/emag/management`

#### Health & Monitoring
- `GET /health` - Get eMAG integration health status
- `GET /monitoring/metrics` - Get detailed monitoring metrics
- `GET /monitoring/sync-stats` - Get sync statistics (24h)
- `GET /monitoring/product-stats` - Get product statistics

#### Rate Limiter
- `GET /rate-limiter/stats` - Get rate limiter statistics
- `POST /rate-limiter/reset` - Reset rate limiter statistics

#### Backup & Recovery
- `POST /backup/create` - Create a backup
- `GET /backup/list` - List all backups
- `POST /backup/cleanup` - Delete old backups
- `POST /backup/restore` - Restore from backup
- `POST /backup/schedule` - Schedule background backup

---

## 🔧 Configuration

### Environment Variables

Add to `.env` file:

```bash
# Rate Limiting (optional, defaults provided)
EMAG_RATE_LIMIT_ORDERS_RPS=12
EMAG_RATE_LIMIT_OTHER_RPS=3

# Backup Configuration
BACKUP_DIR=backups
BACKUP_RETENTION_DAYS=30

# Monitoring
MONITORING_ENABLED=true
MONITORING_ALERT_EMAIL=admin@example.com
```

### Rate Limiter Configuration

The rate limiter is automatically configured with eMAG API v4.4.8 specifications:
- **Orders**: 12 requests/second (720/minute)
- **Other**: 3 requests/second (180/minute)
- **Jitter**: 0-100ms random delay

To disable rate limiting in development:

```python
# In app/services/emag_api_client.py
client = EmagApiClient(
    username=username,
    password=password,
    use_rate_limiter=False  # Disable for testing
)
```

---

## 🧪 Testing Checklist

### Pre-Deployment Tests
- [ ] All unit tests passing (24/24)
- [ ] Verification script passing (6/6)
- [ ] Database migration applied successfully
- [ ] No linting errors
- [ ] Backend starts without errors

### Post-Deployment Tests
- [ ] Health endpoint returns 200 OK
- [ ] Monitoring endpoints accessible
- [ ] Rate limiter working correctly
- [ ] Backup creation successful
- [ ] Existing endpoints still working
- [ ] Frontend can connect to backend
- [ ] Authentication working
- [ ] eMAG sync operations functional

---

## 📈 Monitoring

### Health Check

```bash
# Check system health
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/emag/management/health \
  | python3 -m json.tool
```

Response:
```json
{
  "status": "healthy",
  "health_score": 100.0,
  "metrics": {
    "requests_per_minute": 45.2,
    "error_rate": 0.01,
    "average_response_time": 150.5,
    "rate_limit_usage": 0.25,
    "sync_success_rate": 0.98
  },
  "alerts": {
    "high_error_rate": false,
    "slow_response": false,
    "rate_limit_warning": false,
    "sync_failure": false
  }
}
```

### Alert Thresholds

The system will alert when:
- **Error rate** > 5%
- **Response time** > 2000ms
- **Rate limit usage** > 80%
- **Sync success rate** < 95%

---

## 🔄 Scheduled Tasks

### Automated Backup

Setup cron job for daily backups:

```bash
# Add to crontab
0 2 * * * cd /Users/macos/anaconda3/envs/MagFlow && python3 -c "from app.services.backup_service import scheduled_backup; import asyncio; asyncio.run(scheduled_backup())"
```

Or use Celery beat:

```python
# In app/tasks/celery_config.py
from celery.schedules import crontab

beat_schedule = {
    'daily-emag-backup': {
        'task': 'app.tasks.emag_tasks.create_backup',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
}
```

---

## 🐛 Troubleshooting

### Issue: Migration Fails

```bash
# Check current migration
alembic current

# Check migration history
alembic history

# Downgrade if needed
alembic downgrade -1

# Re-apply
alembic upgrade head
```

### Issue: Import Errors

```bash
# Verify Python path
python3 -c "import sys; print('\n'.join(sys.path))"

# Reinstall dependencies
pip install -r requirements.txt

# Check module imports
python3 verify_implementation.py
```

### Issue: Rate Limiter Too Aggressive

```python
# Temporarily disable in development
# In app/services/emag_api_client.py
client = EmagApiClient(
    username=username,
    password=password,
    use_rate_limiter=False
)
```

### Issue: Backup Fails

```bash
# Check backup directory permissions
ls -la backups/

# Create directory if missing
mkdir -p backups
chmod 755 backups

# Test backup manually
python3 -c "
from app.services.backup_service import BackupService
import asyncio

async def test():
    from app.core.database import get_async_session
    async with get_async_session() as db:
        service = BackupService(db)
        result = await service.create_backup(
            include_products=False,
            include_sync_logs=True,
            compress=True
        )
        print(result)

asyncio.run(test())
"
```

---

## 📚 Additional Resources

### Documentation
- `EMAG_RECOMMENDATIONS_IMPLEMENTATION_COMPLETE.md` - Full implementation details
- `EMAG_INTEGRATION_RECOMMENDATIONS.md` - Original recommendations
- `docs/EMAG_FULL_SYNC_GUIDE.md` - Sync guide
- API Documentation: http://localhost:8000/docs

### Test Files
- `tests/test_emag_enhancements.py` - Unit tests
- `test_integration_complete.py` - Integration tests
- `verify_implementation.py` - Verification script

### Code Files
- `app/core/emag_errors.py` - Error handling
- `app/core/emag_rate_limiter.py` - Rate limiting
- `app/core/emag_constants.py` - Constants and enums
- `app/services/order_validation.py` - Order validation
- `app/services/emag_monitoring.py` - Monitoring service
- `app/services/backup_service.py` - Backup service
- `app/api/v1/endpoints/emag_management.py` - Management endpoints

---

## ✅ Deployment Checklist

### Pre-Deployment
- [ ] Code reviewed and approved
- [ ] All tests passing
- [ ] Database backup created
- [ ] Migration tested in staging
- [ ] Documentation updated
- [ ] Team notified

### Deployment
- [ ] Apply database migration
- [ ] Deploy new code
- [ ] Restart backend services
- [ ] Verify health endpoints
- [ ] Run integration tests
- [ ] Monitor logs for errors

### Post-Deployment
- [ ] Verify all endpoints working
- [ ] Check monitoring metrics
- [ ] Test backup creation
- [ ] Verify rate limiting
- [ ] Update team on status
- [ ] Monitor for 24 hours

---

## 🎉 Success Criteria

Deployment is successful when:
- ✅ All 24 unit tests passing
- ✅ All 6 verification checks passing
- ✅ All 5 integration test groups passing
- ✅ Health endpoint returns "healthy" status
- ✅ No errors in application logs
- ✅ Existing functionality unaffected
- ✅ New endpoints accessible and functional

---

## 📞 Support

For issues or questions:
- Check logs: `tail -f logs/app.log`
- Review documentation in `docs/` directory
- Run verification: `python3 verify_implementation.py`
- Test integration: `python3 test_integration_complete.py`

---

**Deployment Guide Version:** 1.0  
**Last Updated:** 2025-09-29  
**Status:** ✅ Ready for Production
