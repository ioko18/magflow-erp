# MagFlow ERP - Backup Quick Start Guide

## 🚀 Quick Commands

### Run Backup
```bash
cd /Users/macos/anaconda3/envs/MagFlow/scripts
./backup_complete.sh
```

### Run Restore
```bash
cd /Users/macos/anaconda3/envs/MagFlow/scripts
./restore_complete.sh
```

## 📁 Backup Location
```
/Users/macos/Dropbox/MagFlow_backup/
```

## ✅ What Gets Backed Up

### 1. Database (PostgreSQL)
- ✓ Full SQL dump (compressed)
- ✓ Custom format for pg_restore
- ✓ Schema-only backup
- ✓ Database statistics

### 2. Project Files (145MB)
- ✓ All source code
- ✓ Scripts and documentation
- ✓ Configuration templates
- ✗ Excludes: node_modules, __pycache__, .git, logs

### 3. Configuration (32KB)
- ✓ Environment files (.env*)
- ✓ JWT keys (12 files)
- ✓ SSL certificates
- ✓ Docker configuration
- ✓ nginx configuration

## 📊 Latest Backup Results

**Date:** 2025-10-02 22:17:28  
**Total Size:** 158MB  
**Status:** ✓ PASSED  
**Files:** 38,844 files backed up  
**Retention:** 30 days (until 2025-11-01)

### Backup Contents:
```
20251002_221728/
├── database/
│   ├── magflow_db_20251002_221728.sql.gz (4.7M)
│   ├── magflow_db_20251002_221728.dump (5.0M)
│   ├── schema_20251002_221728.sql (136K)
│   ├── db_stats_20251002_221728.txt (8.3K)
│   └── checksums.txt (471B)
├── files/
│   ├── project_files_20251002_221728.tar.gz (145M)
│   ├── contents.txt (2.5M)
│   └── checksum.txt (103B)
├── config/
│   ├── sensitive_config_20251002_221728.tar.gz (32K)
│   ├── env/ (7 files)
│   ├── jwt-keys/ (12 files)
│   ├── certs/ (10 files)
│   ├── docker/ (6 files)
│   └── nginx/ (2 files)
├── logs/
│   └── backup_20251002_221728.log (87K)
├── BACKUP_MANIFEST.json (3.9K)
└── BACKUP_SUMMARY.txt (2.1K)
```

## 🔄 Quick Restore Commands

### Restore Database Only
```bash
gunzip -c /Users/macos/Dropbox/MagFlow_backup/20251002_221728/database/magflow_db_20251002_221728.sql.gz | \
  docker exec -i magflow_db psql -U app -d magflow
```

### Restore Files Only
```bash
tar -xzf /Users/macos/Dropbox/MagFlow_backup/20251002_221728/files/project_files_20251002_221728.tar.gz \
  -C /Users/macos/anaconda3/envs/
```

### Restore Configuration Only
```bash
tar -xzf /Users/macos/Dropbox/MagFlow_backup/20251002_221728/config/sensitive_config_20251002_221728.tar.gz \
  -C /tmp/restore && \
cp /tmp/restore/env/.env /Users/macos/anaconda3/envs/MagFlow/
```

## ⏰ Automated Backups

### Using Cron (Daily at 2 AM)
```bash
# Edit crontab
crontab -e

# Add this line:
0 2 * * * /Users/macos/anaconda3/envs/MagFlow/scripts/backup_complete.sh >> /tmp/magflow_backup_cron.log 2>&1
```

### Using launchd (macOS)
Create file: `~/Library/LaunchAgents/com.magflow.backup.plist`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.magflow.backup</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/macos/anaconda3/envs/MagFlow/scripts/backup_complete.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>2</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.magflow.backup.plist
```

## 🔍 Verify Backup

### Check Backup Status
```bash
cat /Users/macos/Dropbox/MagFlow_backup/20251002_221728/BACKUP_SUMMARY.txt
```

### Verify Checksums
```bash
cd /Users/macos/Dropbox/MagFlow_backup/20251002_221728/database
shasum -c checksums.txt
```

### Test Archive Integrity
```bash
tar -tzf /Users/macos/Dropbox/MagFlow_backup/20251002_221728/files/project_files_20251002_221728.tar.gz > /dev/null && echo "✓ Archive OK"
```

## ⚠️ Important Notes

1. **Security:** Configuration archive contains sensitive credentials and JWT keys
2. **Storage:** Backups are stored in Dropbox with 30-day retention
3. **Testing:** Test restore procedure monthly
4. **Monitoring:** Check backup logs regularly
5. **Space:** Ensure sufficient disk space (each backup ~158MB)

## 📚 Documentation

- **Full Documentation:** [BACKUP_RESTORE_README.md](./BACKUP_RESTORE_README.md)
- **Backup Script:** [backup_complete.sh](./backup_complete.sh)
- **Restore Script:** [restore_complete.sh](./restore_complete.sh)

## 🆘 Troubleshooting

### Database container not running
```bash
docker ps
docker-compose up -d
```

### Permission denied
```bash
chmod +x scripts/backup_complete.sh scripts/restore_complete.sh
```

### Disk space full
```bash
df -h /Users/macos/Dropbox
# Clean old backups manually if needed
rm -rf /Users/macos/Dropbox/MagFlow_backup/OLD_TIMESTAMP
```

### Check backup logs
```bash
tail -f /Users/macos/Dropbox/MagFlow_backup/LATEST/logs/backup_*.log
```

## 📞 Support

For issues or questions, check:
1. Backup logs in `/Users/macos/Dropbox/MagFlow_backup/TIMESTAMP/logs/`
2. BACKUP_MANIFEST.json for detailed backup information
3. Full documentation in BACKUP_RESTORE_README.md

---

**Last Updated:** 2025-10-02  
**Script Version:** 2.0.0  
**Status:** ✅ Production Ready
