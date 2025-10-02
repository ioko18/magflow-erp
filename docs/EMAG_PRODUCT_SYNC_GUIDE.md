# eMAG Product Synchronization Guide

## Overview

This guide explains how to use the comprehensive eMAG product synchronization system in MagFlow ERP. The system synchronizes products from both MAIN and FBE eMAG accounts to your local database, providing improved performance, offline capabilities, and better data control.

## Table of Contents

1. [Benefits of Local Synchronization](#benefits)
2. [Architecture](#architecture)
3. [Configuration](#configuration)
4. [Usage](#usage)
5. [API Reference](#api-reference)
6. [Scheduled Synchronization](#scheduled-sync)
7. [Monitoring](#monitoring)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Benefits of Local Synchronization {#benefits}

### Performance
- **Instant Access**: Data is available immediately without API latency
- **Reduced API Calls**: Minimize requests to eMAG API, avoiding rate limits
- **Faster Queries**: Database indexes enable quick searches and filtering

### Availability
- **Offline Capability**: Continue working even if eMAG API is temporarily unavailable
- **Reliability**: No dependency on external service uptime for read operations

### Data Control
- **Custom Fields**: Add business-specific fields to product data
- **Transformations**: Apply custom calculations and data processing
- **Audit Trail**: Track all changes with complete history

### Integration
- **Unified Access**: All modules access the same synchronized data
- **Simplified Code**: No need for direct API calls throughout the application
- **Consistency**: Single source of truth for product information

---

## Architecture {#architecture}

### Components

```
┌─────────────────┐
│  eMAG API       │
│  (MAIN + FBE)   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  EmagProductSyncService │
│  - Fetch products       │
│  - Conflict resolution  │
│  - Batch processing     │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  PostgreSQL Database    │
│  - emag_products_v2     │
│  - emag_sync_logs       │
│  - emag_sync_progress   │
└─────────────────────────┘
```

### Database Tables

#### `emag_products_v2`
Stores synchronized product data with full eMAG API v4.4.9 fields:
- Basic information (SKU, name, description, brand)
- Pricing and inventory
- Categories and classification
- Images and media
- eMAG-specific fields (validation, competition, genius)
- GPSR compliance data
- Sync tracking metadata

#### `emag_sync_logs`
Tracks synchronization operations:
- Sync type and account
- Status and timing
- Statistics (created, updated, failed)
- Error details

#### `emag_sync_progress`
Real-time progress tracking:
- Current page/item
- Percentage complete
- Estimated completion time

---

## Configuration {#configuration}

### Environment Variables

Add these to your `.env` file:

```bash
# MAIN Account
EMAG_MAIN_USERNAME=your_main_username
EMAG_MAIN_PASSWORD=your_main_password
EMAG_MAIN_BASE_URL=https://marketplace-api.emag.ro/api-3

# FBE Account
EMAG_FBE_USERNAME=your_fbe_username
EMAG_FBE_PASSWORD=your_fbe_password
EMAG_FBE_BASE_URL=https://marketplace-api.emag.ro/api-3

# Sync Configuration
EMAG_SYNC_INTERVAL_MINUTES=60
EMAG_ENABLE_SCHEDULED_SYNC=true
EMAG_MAIN_LOG_RETENTION=30
```

### Sync Modes

1. **Incremental** (Recommended)
   - Syncs only changed products
   - Fast and efficient
   - Use for regular updates

2. **Full**
   - Syncs all products
   - Slower but comprehensive
   - Use for initial sync or recovery

3. **Selective**
   - Syncs specific products
   - Requires additional filters
   - Use for targeted updates

### Conflict Resolution Strategies

1. **EMAG_PRIORITY** (Recommended)
   - eMAG data always wins
   - Ensures consistency with marketplace
   - Default strategy

2. **LOCAL_PRIORITY**
   - Local modifications preserved
   - Use when local data is authoritative

3. **NEWEST_WINS**
   - Most recently modified data wins
   - Balanced approach

4. **MANUAL**
   - Requires manual intervention
   - Use for critical data conflicts

---

## Usage {#usage}

### Manual Synchronization

#### Via API

```bash
# Incremental sync (both accounts)
curl -X POST http://localhost:8000/api/v1/emag/products/sync \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_type": "both",
    "mode": "incremental",
    "max_pages": 10,
    "conflict_strategy": "emag_priority"
  }'

# Full sync (MAIN account only)
curl -X POST http://localhost:8000/api/v1/emag/products/sync \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_type": "main",
    "mode": "full",
    "conflict_strategy": "emag_priority"
  }'

# Async sync (background)
curl -X POST http://localhost:8000/api/v1/emag/products/sync \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_type": "both",
    "mode": "incremental",
    "run_async": true
  }'
```

#### Via Python

```python
from app.services.emag_product_sync_service import (
    EmagProductSyncService,
    SyncMode,
    ConflictResolutionStrategy,
)
from app.db import get_db

async def sync_products():
    async with get_db() as db:
        async with EmagProductSyncService(
            db=db,
            account_type="both",
            conflict_strategy=ConflictResolutionStrategy.EMAG_PRIORITY,
        ) as sync_service:
            result = await sync_service.sync_all_products(
                mode=SyncMode.INCREMENTAL,
                max_pages=10,
                items_per_page=100,
                include_inactive=False,
            )
            print(f"Synced {result['total_processed']} products")
            print(f"Created: {result['created']}, Updated: {result['updated']}")
```

### Checking Sync Status

```bash
# Get current sync status
curl -X GET http://localhost:8000/api/v1/emag/products/status \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get sync statistics
curl -X GET http://localhost:8000/api/v1/emag/products/statistics \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get sync history
curl -X GET "http://localhost:8000/api/v1/emag/products/history?limit=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Querying Synced Products

```bash
# Get synced products
curl -X GET "http://localhost:8000/api/v1/emag/products/products?skip=0&limit=50" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Search products
curl -X GET "http://localhost:8000/api/v1/emag/products/products?search=laptop&account_type=main" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## API Reference {#api-reference}

### POST `/api/v1/emag/products/sync`
Trigger product synchronization.

**Request Body:**
```json
{
  "account_type": "both",
  "mode": "incremental",
  "max_pages": 10,
  "items_per_page": 100,
  "include_inactive": false,
  "conflict_strategy": "emag_priority",
  "run_async": false
}
```

**Response:**
```json
{
  "status": "completed",
  "message": "Product synchronization completed successfully",
  "data": {
    "total_processed": 500,
    "created": 50,
    "updated": 450,
    "unchanged": 0,
    "failed": 0,
    "errors": []
  }
}
```

### GET `/api/v1/emag/products/status`
Get current synchronization status.

**Response:**
```json
{
  "is_running": true,
  "current_sync": {
    "id": "uuid",
    "account_type": "both",
    "operation": "incremental_sync",
    "started_at": "2025-10-01T10:00:00Z",
    "total_items": 1000,
    "processed_items": 500
  },
  "recent_syncs": [...]
}
```

### GET `/api/v1/emag/products/statistics`
Get synchronization statistics.

**Response:**
```json
{
  "products_by_account": {
    "main": 5000,
    "fbe": 3000
  },
  "total_products": 8000,
  "recent_syncs": [...]
}
```

### GET `/api/v1/emag/products/history`
Get synchronization history.

**Query Parameters:**
- `limit`: Maximum records (1-100)
- `account_type`: Filter by account
- `status`: Filter by status

### GET `/api/v1/emag/products/products`
Get synchronized products.

**Query Parameters:**
- `skip`: Pagination offset
- `limit`: Maximum records (1-100)
- `account_type`: Filter by account
- `search`: Search in SKU or name

### POST `/api/v1/emag/products/test-connection`
Test connection to eMAG API.

**Query Parameters:**
- `account_type`: Account to test (main/fbe)

---

## Scheduled Synchronization {#scheduled-sync}

### Celery Beat Configuration

The system includes automatic scheduled synchronization using Celery Beat:

#### Default Schedule

| Task | Frequency | Description |
|------|-----------|-------------|
| Product Sync | Every hour | Incremental sync (10 pages) |
| Full Product Sync | Daily at 2 AM | Complete sync (all pages) |
| Order Sync | Every 5 minutes | New orders |
| Auto-acknowledge | Every 10 minutes | Acknowledge new orders |
| Cleanup Logs | Daily at 3 AM | Remove old sync logs |
| Health Check | Every 15 minutes | System health monitoring |

#### Enable/Disable Scheduled Sync

```bash
# Enable scheduled product sync
EMAG_ENABLE_SCHEDULED_SYNC=true

# Disable scheduled product sync (manual only)
EMAG_ENABLE_SCHEDULED_SYNC=false
```

#### Customize Sync Interval

```bash
# Sync every 30 minutes
EMAG_SYNC_INTERVAL_MINUTES=30

# Sync every 2 hours
EMAG_SYNC_INTERVAL_MINUTES=120
```

### Starting Celery Workers

```bash
# Start Celery worker
celery -A app.core.celery worker --loglevel=info

# Start Celery beat scheduler
celery -A app.core.celery beat --loglevel=info

# Start both together
celery -A app.core.celery worker --beat --loglevel=info
```

---

## Monitoring {#monitoring}

### Sync Logs

Monitor synchronization through logs:

```bash
# View recent sync logs
tail -f logs/emag_sync.log

# Filter by account
grep "account=main" logs/emag_sync.log

# View errors only
grep "ERROR" logs/emag_sync.log
```

### Database Queries

```sql
-- Recent sync operations
SELECT 
    sync_type,
    account_type,
    operation,
    status,
    started_at,
    duration_seconds,
    total_items,
    created_items,
    updated_items,
    failed_items
FROM emag_sync_logs
WHERE sync_type = 'products'
ORDER BY started_at DESC
LIMIT 10;

-- Product counts by account
SELECT 
    account_type,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE is_active = true) as active,
    COUNT(*) FILTER (WHERE sync_status = 'synced') as synced
FROM emag_products_v2
GROUP BY account_type;

-- Failed syncs
SELECT *
FROM emag_sync_logs
WHERE status = 'failed'
  AND sync_type = 'products'
ORDER BY started_at DESC;
```

### Grafana Dashboards

Monitor sync metrics in Grafana:
- Sync success rate
- Sync duration trends
- Product count over time
- Error rates
- API response times

---

## Best Practices {#best-practices}

### 1. Sync Frequency

- **Regular Updates**: Use incremental sync every hour
- **Full Sync**: Run daily during off-peak hours (2-4 AM)
- **Real-time Needs**: For critical updates, trigger manual sync

### 2. Error Handling

- **Monitor Logs**: Regularly check sync logs for errors
- **Retry Failed**: Manually retry failed syncs
- **Alert Setup**: Configure alerts for sync failures

### 3. Performance Optimization

- **Batch Size**: Use 100 items per page (maximum)
- **Page Limits**: Set reasonable max_pages for regular syncs
- **Off-Peak Sync**: Schedule heavy syncs during low-traffic hours

### 4. Data Quality

- **Validation**: Enable product validation checks
- **Conflict Strategy**: Use EMAG_PRIORITY for consistency
- **Manual Review**: Periodically review sync statistics

### 5. Backup and Recovery

- **Database Backups**: Regular backups before full syncs
- **Sync History**: Keep 30 days of sync logs
- **Recovery Plan**: Document recovery procedures

---

## Troubleshooting {#troubleshooting}

### Common Issues

#### 1. Sync Fails with Authentication Error

**Problem**: Invalid credentials or IP not whitelisted

**Solution**:
```bash
# Test connection
curl -X POST http://localhost:8000/api/v1/emag/products/test-connection?account_type=main \
  -H "Authorization: Bearer YOUR_TOKEN"

# Verify credentials in .env
echo $EMAG_MAIN_USERNAME
echo $EMAG_MAIN_PASSWORD

# Check IP whitelist in eMAG seller portal
```

#### 2. Rate Limit Exceeded

**Problem**: Too many API requests

**Solution**:
- Reduce sync frequency
- Increase delay between requests
- Use smaller page sizes
- Spread syncs across time

#### 3. Sync Hangs or Times Out

**Problem**: Large dataset or slow network

**Solution**:
- Set max_pages limit
- Run sync in background (async)
- Increase timeout settings
- Check network connectivity

#### 4. Duplicate Products

**Problem**: Same product from different accounts

**Solution**:
- Products are stored separately by account_type
- Use SKU + account_type as unique key
- Implement product matching logic if needed

#### 5. Missing Products

**Problem**: Not all products synced

**Solution**:
```bash
# Check sync logs for errors
curl -X GET http://localhost:8000/api/v1/emag/products/history?status=failed

# Run full sync
curl -X POST http://localhost:8000/api/v1/emag/products/sync \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"mode": "full", "account_type": "both"}'
```

### Debug Mode

Enable detailed logging:

```bash
# In .env
EMAG_MAIN_DETAILED_LOG=true
EMAG_FBE_DETAILED_LOG=true
LOG_LEVEL=DEBUG
```

### Support

For additional help:
1. Check logs: `logs/emag_sync.log`
2. Review sync history in database
3. Test API connection
4. Contact eMAG support for API issues

---

## Examples

### Example 1: Initial Setup

```bash
# 1. Configure credentials
cat >> .env << EOF
EMAG_MAIN_USERNAME=your_username
EMAG_MAIN_PASSWORD=your_password
EMAG_FBE_USERNAME=your_fbe_username
EMAG_FBE_PASSWORD=your_fbe_password
EMAG_ENABLE_SCHEDULED_SYNC=true
EOF

# 2. Test connection
curl -X POST http://localhost:8000/api/v1/emag/products/test-connection?account_type=main \
  -H "Authorization: Bearer YOUR_TOKEN"

# 3. Run initial full sync
curl -X POST http://localhost:8000/api/v1/emag/products/sync \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"mode": "full", "account_type": "both", "run_async": true}'

# 4. Monitor progress
watch -n 5 'curl -s http://localhost:8000/api/v1/emag/products/status \
  -H "Authorization: Bearer YOUR_TOKEN" | jq'
```

### Example 2: Daily Operations

```bash
# Morning: Check overnight sync
curl -X GET http://localhost:8000/api/v1/emag/products/statistics \
  -H "Authorization: Bearer YOUR_TOKEN" | jq

# During day: Manual incremental sync if needed
curl -X POST http://localhost:8000/api/v1/emag/products/sync \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"mode": "incremental", "max_pages": 5}'

# Evening: Review sync history
curl -X GET http://localhost:8000/api/v1/emag/products/history?limit=10 \
  -H "Authorization: Bearer YOUR_TOKEN" | jq
```

### Example 3: Troubleshooting

```bash
# 1. Check for failed syncs
curl -X GET "http://localhost:8000/api/v1/emag/products/history?status=failed" \
  -H "Authorization: Bearer YOUR_TOKEN" | jq

# 2. View error details
psql -d magflow -c "SELECT errors FROM emag_sync_logs WHERE status = 'failed' ORDER BY started_at DESC LIMIT 1;"

# 3. Retry with smaller batch
curl -X POST http://localhost:8000/api/v1/emag/products/sync \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"mode": "incremental", "max_pages": 2, "items_per_page": 50}'
```

---

## Conclusion

The eMAG product synchronization system provides a robust, scalable solution for maintaining a local copy of your marketplace products. By following this guide and implementing the recommended best practices, you can ensure reliable, efficient synchronization that enhances your ERP system's performance and capabilities.

For questions or issues, refer to the troubleshooting section or contact the development team.
