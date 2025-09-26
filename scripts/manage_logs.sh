#!/bin/bash
set -euo pipefail

LOG_DIR="/Users/macos/anaconda3/envs/emag-db-docker/logs"
MAX_DIR_MB=${MAX_DIR_MB:-200}
ARCHIVE_EXPIRY_DAYS=${ARCHIVE_EXPIRY_DAYS:-30}

if [ ! -d "$LOG_DIR" ]; then
  echo "Log directory $LOG_DIR not found" >&2
  exit 1
fi

dir_size_mb=$(du -sm "$LOG_DIR" | cut -f1)
echo "Current log directory size: ${dir_size_mb} MB"

if [ "$dir_size_mb" -gt "$MAX_DIR_MB" ]; then
  timestamp=$(date +"%Y%m%d_%H%M%S")
  archive="$LOG_DIR/archive_${timestamp}.tar.gz"
  echo "Archiving logs to $archive"
  tar -czf "$archive" -C "$LOG_DIR" .

  echo "Truncating .log files"
  find "$LOG_DIR" -type f -name "*.log" -exec truncate -s 0 {} \;
fi

echo "Removing archives older than ${ARCHIVE_EXPIRY_DAYS} days"
find "$LOG_DIR" -type f -name "archive_*.tar.gz" -mtime +"$ARCHIVE_EXPIRY_DAYS" -delete
