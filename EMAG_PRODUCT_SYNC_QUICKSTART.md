# eMAG Product Synchronization - Quick Start Guide

## 🚀 Quick Setup (5 minutes)

### 1. Configure Credentials

Add to your `.env` file:

```bash
# MAIN Account
EMAG_MAIN_USERNAME=your_main_email@example.com
EMAG_MAIN_PASSWORD=your_main_password

# FBE Account  
EMAG_FBE_USERNAME=your_fbe_email@example.com
EMAG_FBE_PASSWORD=your_fbe_password

# Enable automatic sync
EMAG_ENABLE_SCHEDULED_SYNC=true
EMAG_SYNC_INTERVAL_MINUTES=60
```

### 2. Test Connection

```bash
curl -X POST "http://localhost:8000/api/v1/emag/products/test-connection?account_type=main" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Run Initial Sync

```bash
curl -X POST http://localhost:8000/api/v1/emag/products/sync \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_type": "both",
    "mode": "full",
    "run_async": true
  }'
```

### 4. Monitor Progress

```bash
curl -X GET http://localhost:8000/api/v1/emag/products/status \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 📊 Common Operations

### Incremental Sync (Daily Use)

```bash
curl -X POST http://localhost:8000/api/v1/emag/products/sync \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_type": "both",
    "mode": "incremental",
    "max_pages": 10
  }'
```

### View Synced Products

```bash
curl -X GET "http://localhost:8000/api/v1/emag/products/products?limit=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Search Products

```bash
curl -X GET "http://localhost:8000/api/v1/emag/products/products?search=laptop&account_type=main" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Check Statistics

```bash
curl -X GET http://localhost:8000/api/v1/emag/products/statistics \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🔄 Automatic Synchronization

The system automatically syncs products every hour when enabled:

```bash
# Enable in .env
EMAG_ENABLE_SCHEDULED_SYNC=true

# Start Celery worker and beat
celery -A app.core.celery worker --beat --loglevel=info
```

## 📈 Monitoring

### Database Query

```sql
-- Check sync status
SELECT 
    account_type,
    COUNT(*) as total_products,
    COUNT(*) FILTER (WHERE is_active = true) as active_products,
    MAX(last_synced_at) as last_sync
FROM emag_products_v2
GROUP BY account_type;
```

### View Logs

```bash
# Recent syncs
curl -X GET "http://localhost:8000/api/v1/emag/products/history?limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Failed syncs only
curl -X GET "http://localhost:8000/api/v1/emag/products/history?status=failed" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🎯 Best Practices

1. **Initial Setup**: Run full sync once, then use incremental
2. **Regular Updates**: Enable scheduled sync (hourly)
3. **Monitor**: Check sync history daily
4. **Backup**: Backup database before major syncs
5. **Off-Peak**: Schedule full syncs during low-traffic hours (2-4 AM)

## 🔧 Troubleshooting

### Sync Fails

```bash
# Test connection
curl -X POST "http://localhost:8000/api/v1/emag/products/test-connection?account_type=main" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Check recent errors
curl -X GET "http://localhost:8000/api/v1/emag/products/history?status=failed&limit=5" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Rate Limits

If you hit rate limits:
- Reduce `max_pages` parameter
- Increase `EMAG_SYNC_INTERVAL_MINUTES`
- Use `run_async: true` for background processing

### Missing Products

```bash
# Run full sync
curl -X POST http://localhost:8000/api/v1/emag/products/sync \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"mode": "full", "account_type": "both"}'
```

## 📚 Full Documentation

For detailed information, see: `docs/EMAG_PRODUCT_SYNC_GUIDE.md`

## 🆘 Support

- Check logs: `logs/emag_sync.log`
- Database: Query `emag_sync_logs` table
- API docs: `http://localhost:8000/docs`

---

**Ready to sync?** Start with step 1 above! 🎉
