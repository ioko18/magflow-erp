# eMAG Product Sync V2 - Quick Start Guide

## 🚀 Quick Start (3 Steps)

### 1. Test Connections
Open the **eMAG Product Sync V2** page and click:
- **Test Connection** for MAIN account
- **Test Connection** for FBE account

Both should show ✓ **Connected**

### 2. Configure Sync (Optional)
Click **Configure Sync** to adjust:
- **Account Type**: Both (recommended) | MAIN Only | FBE Only
- **Sync Mode**: Incremental (fast) | Full (complete) | Selective
- **Max Pages**: 10 (test) | null (all products)
- **Conflict Strategy**: eMAG Priority (recommended)

### 3. Start Sync
Click the big blue button:
**Start Incremental Sync - BOTH**

Watch the progress bar and wait for completion!

---

## 📊 Current Status

### Database Stats
```
MAIN Account:  1,274 products ✓
FBE Account:   1,271 products ✓
TOTAL:         2,545 products
Last Sync:     2025-10-01 17:08 UTC
```

### Latest Sync Results
```
Duration:      9.13 seconds
Processed:     200 products
Updated:       200 products
Failed:        0 products
Success Rate:  100%
```

---

## 🎯 Sync Modes Explained

### Incremental (Recommended)
- **Speed**: ⚡ Fast
- **Use Case**: Daily updates
- **What it does**: Syncs only changed products
- **Best for**: Regular maintenance

### Full
- **Speed**: 🐢 Slow
- **Use Case**: Initial setup or major updates
- **What it does**: Syncs all products from scratch
- **Best for**: First-time sync or data recovery

### Selective
- **Speed**: ⚡ Very Fast
- **Use Case**: Specific products
- **What it does**: Syncs only filtered products
- **Best for**: Targeted updates

---

## 🔧 Common Tasks

### Daily Sync
```
1. Open eMAG Product Sync V2
2. Click "Start Incremental Sync - BOTH"
3. Wait ~10 seconds
4. Done!
```

### Check Product Count
```
1. Look at statistics cards at top
2. See "Total Products", "MAIN Account", "FBE Account"
```

### View Synced Products
```
1. Click "Synced Products" tab
2. Use search box to find products
3. Filter by account (MAIN/FBE)
4. Click eye icon to see details
```

### Export Products
```
1. Go to "Synced Products" tab
2. Apply filters if needed
3. Click "Export CSV" button
4. File downloads automatically
```

### View Sync History
```
1. Click "Sync History" tab
2. See timeline of all syncs
3. Check duration, items, errors
```

---

## ⚠️ Troubleshooting

### Connection Failed
**Problem**: Test connection shows ✗ Failed

**Solution**:
1. Check `.env` file has correct credentials
2. Verify `EMAG_MAIN_USERNAME` and `EMAG_MAIN_PASSWORD`
3. Verify `EMAG_FBE_USERNAME` and `EMAG_FBE_PASSWORD`
4. Restart backend: `docker-compose restart backend`

### Sync Stuck
**Problem**: Sync running for > 15 minutes

**Solution**:
1. Click "Cleanup Stuck" button in top right
2. Confirm cleanup
3. Start new sync

### No Products Showing
**Problem**: Products tab is empty

**Solution**:
1. Check if sync completed successfully
2. Click "Refresh" button
3. Check database: `docker exec magflow_db psql -U app -d magflow -c "SELECT COUNT(*) FROM emag_products_v2;"`

---

## 📱 Command Line Alternative

### Run Sync from Terminal
```bash
cd /Users/macos/anaconda3/envs/MagFlow
python3 run_emag_sync.py
```

### Check Database
```bash
# Count products
docker exec magflow_db psql -U app -d magflow -c \
  "SELECT account_type, COUNT(*) FROM emag_products_v2 GROUP BY account_type;"

# View recent syncs
docker exec magflow_db psql -U app -d magflow -c \
  "SELECT * FROM emag_sync_logs ORDER BY started_at DESC LIMIT 5;"
```

---

## 🎨 UI Features

### Statistics Cards (Top)
- **Total Products**: Combined count from both accounts
- **MAIN Account**: Products from MAIN account
- **FBE Account**: Products from FBE account
- **Status Badge**: Shows if sync is running or idle

### Connection Tests
- Test MAIN and FBE connections separately
- Green = Connected ✓
- Red = Failed ✗

### Sync Controls
- **Big Blue Button**: Start synchronization
- **Configure Sync**: Adjust sync settings
- **Refresh**: Reload all data
- **Auto-refresh**: Toggle automatic updates (30s)
- **Cleanup Stuck**: Fix stuck synchronizations

### Products Table
- **Search**: Find by name or SKU
- **Filter**: By account type (MAIN/FBE)
- **Sort**: Click column headers
- **Details**: Click eye icon for full info
- **Export**: Download as CSV

### Sync History Timeline
- Visual timeline of all syncs
- Color-coded by status (green=success, red=failed)
- Shows duration, items processed, errors

---

## 💡 Best Practices

### Daily Routine
1. **Morning**: Run incremental sync (takes ~10 seconds)
2. **Check**: Review sync history for any errors
3. **Monitor**: Keep auto-refresh ON during work hours

### Weekly Maintenance
1. **Review**: Check sync history for patterns
2. **Cleanup**: Run cleanup if any stuck syncs
3. **Export**: Download product list for records

### Monthly Tasks
1. **Full Sync**: Run once per month for data integrity
2. **Audit**: Compare product counts with eMAG dashboard
3. **Backup**: Export products to CSV for backup

---

## 📞 Support

### Logs Location
```
/Users/macos/anaconda3/envs/MagFlow/logs/emag_sync.log
```

### Check Logs
```bash
tail -100 logs/emag_sync.log
```

### Database Access
```bash
docker exec -it magflow_db psql -U app -d magflow
```

### API Documentation
```
http://localhost:8000/docs
```

---

## ✅ Success Indicators

You know everything is working when:
- ✓ Both connection tests show green
- ✓ Sync completes in < 1 minute
- ✓ No failed items in sync results
- ✓ Products appear in database
- ✓ Last sync time is recent
- ✓ No errors in sync history

---

**Last Updated**: October 1, 2025  
**System Version**: V2  
**Status**: ✅ OPERATIONAL
