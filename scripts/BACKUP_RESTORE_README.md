# MagFlow ERP - Backup & Restore Documentation

## Overview

Complete backup and restore solution for the MagFlow ERP system, including database, project files, and configuration.

## Table of Contents

1. [Features](#features)
2. [Prerequisites](#prerequisites)
3. [Backup Script](#backup-script)
4. [Restore Script](#restore-script)
5. [Backup Structure](#backup-structure)
6. [Usage Examples](#usage-examples)
7. [Scheduling Automated Backups](#scheduling-automated-backups)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

## Features

### Backup Script (`backup_complete.sh`)

- ✅ **PostgreSQL Database Backup**
  - SQL format (compressed with gzip)
  - Custom format (for pg_restore)
  - Schema-only backup
  - Database statistics

- ✅ **Project Files Backup**
  - Complete project directory
  - Excludes temporary files (node_modules, __pycache__, etc.)
  - Compressed tar.gz archive
  - File listing included

- ✅ **Configuration Backup**
  - Environment files (.env)
  - JWT keys
  - SSL certificates
  - Docker configuration
  - nginx configuration

- ✅ **Verification & Integrity**
  - SHA-256 checksums for all files
  - Archive integrity testing
  - Backup manifest with metadata

- ✅ **Additional Features**
  - Detailed logging with timestamps
  - Automatic cleanup of old backups (30-day retention)
  - Pre-flight checks
  - Error handling and rollback
  - Human-readable summary

### Restore Script (`restore_complete.sh`)

- ✅ **Interactive Restore**
  - List available backups
  - Select specific backup
  - Choose what to restore (database, files, config, or all)

- ✅ **Safety Features**
  - Pre-restore validation
  - Safety backups before restore
  - Confirmation prompts
  - Post-restore verification

- ✅ **Flexible Options**
  - Database only
  - Files only
  - Configuration only
  - Selective or full restore

## Prerequisites

### Required Software

```bash
# Check if required tools are installed
docker --version
tar --version
gzip --version
shasum --version
jq --version
```

### Install Missing Tools

```bash
# Install jq (JSON processor) if not available
brew install jq

# Ensure Docker Desktop is running
open -a Docker
```

### Permissions

```bash
# Make scripts executable
chmod +x /Users/macos/anaconda3/envs/MagFlow/scripts/backup_complete.sh
chmod +x /Users/macos/anaconda3/envs/MagFlow/scripts/restore_complete.sh
```

## Backup Script

### Configuration

Edit the script to customize these variables:

```bash
# Project paths
PROJECT_DIR="/Users/macos/anaconda3/envs/MagFlow"
BACKUP_BASE_DIR="/Users/macos/Dropbox/MagFlow_backup"

# Docker container name
DB_CONTAINER="magflow_db"

# Database credentials
DB_NAME="magflow"
DB_USER="app"

# Retention policy (days)
RETENTION_DAYS=30
```

### Running the Backup

```bash
# Navigate to scripts directory
cd /Users/macos/anaconda3/envs/MagFlow/scripts

# Run backup
./backup_complete.sh
```

### What Gets Backed Up

#### Database
- Full database dump (SQL + Custom format)
- Schema-only backup
- Database statistics
- Table sizes and row counts

#### Project Files
- All source code
- Documentation
- Scripts
- Configuration templates
- **Excludes**: node_modules, __pycache__, .git, *.log, test-reports, etc.

#### Configuration
- `.env` files
- `jwt-keys/` directory
- `certs/` directory
- Docker Compose files
- nginx configuration
- Other config files (alembic.ini, pyproject.toml, etc.)

### Backup Output

```
/Users/macos/Dropbox/MagFlow_backup/
└── 20251002_220838/
    ├── database/
    │   ├── magflow_db_20251002_220838.sql.gz
    │   ├── magflow_db_20251002_220838.dump
    │   ├── schema_20251002_220838.sql
    │   ├── db_stats_20251002_220838.txt
    │   └── checksums.txt
    ├── files/
    │   ├── project_files_20251002_220838.tar.gz
    │   ├── contents.txt
    │   ├── checksum.txt
    │   └── exclude_patterns.txt
    ├── config/
    │   ├── sensitive_config_20251002_220838.tar.gz
    │   ├── env/
    │   ├── jwt-keys/
    │   ├── certs/
    │   ├── docker/
    │   └── checksum.txt
    ├── logs/
    │   └── backup_20251002_220838.log
    ├── BACKUP_MANIFEST.json
    └── BACKUP_SUMMARY.txt
```

## Restore Script

### Running the Restore

```bash
# Navigate to scripts directory
cd /Users/macos/anaconda3/envs/MagFlow/scripts

# Run restore (interactive)
./restore_complete.sh
```

### Restore Process

1. **Select Backup**
   - Script lists all available backups
   - Shows date, time, size, and verification status
   - Select backup by number

2. **Choose Restore Options**
   - Database only
   - Files only
   - Configuration only
   - Database + Configuration
   - Everything (full restore)

3. **Confirmation**
   - Review what will be restored
   - Confirm to proceed

4. **Safety Backup**
   - Script creates safety backup of current state
   - Allows rollback if restore fails

5. **Restore Execution**
   - Restores selected components
   - Shows progress and logs

6. **Verification**
   - Verifies restored components
   - Reports any issues

### Manual Restore Commands

If you prefer manual restore:

#### Database Restore

```bash
# Using SQL dump
gunzip -c /path/to/backup/database/magflow_db_TIMESTAMP.sql.gz | \
  docker exec -i magflow_db psql -U app -d magflow

# Using custom format
docker exec -i magflow_db pg_restore -U app -d magflow \
  --clean --if-exists < /path/to/backup/database/magflow_db_TIMESTAMP.dump
```

#### Files Restore

```bash
# Extract project files
tar -xzf /path/to/backup/files/project_files_TIMESTAMP.tar.gz \
  -C /Users/macos/anaconda3/envs/
```

#### Configuration Restore

```bash
# Extract configuration
tar -xzf /path/to/backup/config/sensitive_config_TIMESTAMP.tar.gz \
  -C /tmp/restore_config

# Copy files to project
cp /tmp/restore_config/env/.env /Users/macos/anaconda3/envs/MagFlow/
cp -r /tmp/restore_config/jwt-keys/* /Users/macos/anaconda3/envs/MagFlow/jwt-keys/
cp -r /tmp/restore_config/certs/* /Users/macos/anaconda3/envs/MagFlow/certs/
```

## Backup Structure

### BACKUP_MANIFEST.json

Complete metadata about the backup:

```json
{
  "backup_info": {
    "name": "MagFlow ERP Complete Backup",
    "version": "2.0.0",
    "timestamp": "20251002_220838",
    "date": "2025-10-02",
    "time": "22:08:38"
  },
  "source": {
    "project_directory": "/Users/macos/anaconda3/envs/MagFlow",
    "database_container": "magflow_db",
    "database_name": "magflow"
  },
  "database_backup": {
    "sql_compressed": {
      "file": "magflow_db_20251002_220838.sql.gz",
      "size": "2.3M",
      "checksum": "abc123...",
      "restore_command": "..."
    }
  },
  "verification": {
    "status": "PASSED",
    "checksums_verified": true
  },
  "restore_instructions": [...]
}
```

### BACKUP_SUMMARY.txt

Human-readable summary with quick restore commands.

## Usage Examples

### Example 1: Daily Backup

```bash
# Run daily backup
cd /Users/macos/anaconda3/envs/MagFlow/scripts
./backup_complete.sh

# Check backup log
tail -f /Users/macos/Dropbox/MagFlow_backup/LATEST/logs/backup_*.log
```

### Example 2: Pre-Deployment Backup

```bash
# Create backup before deploying changes
./backup_complete.sh

# Deploy changes
docker-compose down
git pull
docker-compose up -d

# If something goes wrong, restore
./restore_complete.sh
```

### Example 3: Database-Only Backup

```bash
# For quick database backup, use the existing script
cd /Users/macos/anaconda3/envs/MagFlow/scripts
./backup.sh
```

### Example 4: Verify Backup Integrity

```bash
# Navigate to backup directory
cd /Users/macos/Dropbox/MagFlow_backup/20251002_220838

# Verify database checksums
cd database
shasum -c checksums.txt

# Verify files archive
cd ../files
tar -tzf project_files_*.tar.gz > /dev/null && echo "Archive OK"

# Check manifest
cd ..
cat BACKUP_MANIFEST.json | jq '.verification'
```

## Scheduling Automated Backups

### Using Cron (macOS/Linux)

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /Users/macos/anaconda3/envs/MagFlow/scripts/backup_complete.sh >> /tmp/magflow_backup_cron.log 2>&1

# Add weekly full backup on Sunday at 3 AM
0 3 * * 0 /Users/macos/anaconda3/envs/MagFlow/scripts/backup_complete.sh >> /tmp/magflow_backup_cron.log 2>&1
```

### Using launchd (macOS)

Create a plist file:

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
    <key>StandardOutPath</key>
    <string>/tmp/magflow_backup.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/magflow_backup_error.log</string>
</dict>
</plist>
```

Save to `~/Library/LaunchAgents/com.magflow.backup.plist` and load:

```bash
launchctl load ~/Library/LaunchAgents/com.magflow.backup.plist
```

## Best Practices

### 1. Regular Backups

- **Daily**: Automated backups during off-peak hours
- **Pre-deployment**: Manual backup before any major changes
- **Weekly**: Full backup verification

### 2. Backup Storage

- **Primary**: Dropbox (cloud storage with versioning)
- **Secondary**: External hard drive or NAS
- **Offsite**: Consider additional cloud backup (AWS S3, Google Drive)

### 3. Retention Policy

- **Daily backups**: Keep for 7 days
- **Weekly backups**: Keep for 4 weeks
- **Monthly backups**: Keep for 12 months
- **Yearly backups**: Keep indefinitely

### 4. Security

- **Encrypt sensitive backups**: Use encryption for backups containing credentials
- **Restrict access**: Limit who can access backup files
- **Secure transfer**: Use secure protocols (SFTP, SCP) for remote backups
- **Audit logs**: Review backup logs regularly

### 5. Testing

- **Monthly restore test**: Verify backups can be restored
- **Document procedures**: Keep restore procedures up to date
- **Train team**: Ensure team knows how to restore

### 6. Monitoring

- **Check backup success**: Review logs daily
- **Monitor disk space**: Ensure sufficient space for backups
- **Alert on failures**: Set up notifications for failed backups

## Troubleshooting

### Issue: "Database container not running"

```bash
# Check Docker status
docker ps

# Start container
docker-compose up -d

# Check container logs
docker logs magflow_db
```

### Issue: "Permission denied"

```bash
# Make scripts executable
chmod +x scripts/backup_complete.sh
chmod +x scripts/restore_complete.sh

# Check directory permissions
ls -la /Users/macos/Dropbox/MagFlow_backup
```

### Issue: "Disk space full"

```bash
# Check available space
df -h /Users/macos/Dropbox

# Clean old backups manually
rm -rf /Users/macos/Dropbox/MagFlow_backup/OLD_TIMESTAMP

# Adjust retention policy in script
```

### Issue: "Backup verification failed"

```bash
# Check backup log
cat /Users/macos/Dropbox/MagFlow_backup/TIMESTAMP/logs/backup_*.log

# Verify checksums manually
cd /Users/macos/Dropbox/MagFlow_backup/TIMESTAMP/database
shasum -c checksums.txt

# Re-run backup if needed
./backup_complete.sh
```

### Issue: "Restore fails with database errors"

```bash
# Check database container logs
docker logs magflow_db

# Verify database is accessible
docker exec magflow_db psql -U app -d postgres -c "SELECT 1;"

# Try restoring to a new database first
docker exec magflow_db psql -U app -d postgres -c "CREATE DATABASE magflow_test;"
gunzip -c backup.sql.gz | docker exec -i magflow_db psql -U app -d magflow_test
```

### Issue: "jq command not found"

```bash
# Install jq
brew install jq

# Or use alternative JSON parser
python3 -m json.tool < BACKUP_MANIFEST.json
```

## Support

For issues or questions:

1. Check the logs in `/Users/macos/Dropbox/MagFlow_backup/TIMESTAMP/logs/`
2. Review the BACKUP_MANIFEST.json for backup details
3. Consult the MagFlow ERP documentation
4. Contact the development team

## Version History

- **v2.0.0** (2025-10-02): Complete rewrite with enhanced features
  - Added comprehensive backup verification
  - Improved error handling
  - Added restore script
  - Enhanced logging and reporting
  - Added backup manifest

- **v1.0.0**: Initial backup script
  - Basic database and volume backup

## License

Copyright © 2025 MagFlow ERP Team. All rights reserved.
