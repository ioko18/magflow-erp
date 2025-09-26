# Cron Jobs Overview

## Current User Crontab
- `* * * * *` — Appends a healthcheck timestamp to `/Users/macos/anaconda3/envs/emag-db-docker/logs/scheduler.log`.
- `5 2 * * *` — Runs `/Users/macos/anaconda3/envs/emag-db-docker/scripts/db-maint.sh` (logs to `logs/db-maint.log`).
- `10 3 * * *` — Runs `/Users/macos/anaconda3/envs/emag-db-docker/scripts/db-health.sh` (logs to `logs/db-health.log`).
- `0 8 * * 1` — Runs `/Users/macos/anaconda3/envs/MagFlow/scripts/manage_logs.sh` (log directory archiving and cleanup).

## Verification Status
- Scripts found and executable:
  - `/Users/macos/anaconda3/envs/emag-db-docker/scripts/db-maint.sh`
  - `/Users/macos/anaconda3/envs/emag-db-docker/scripts/db-health.sh`
- Removed old entries for non-existent scripts (`run_offers_pipeline.sh`, `backup_db.sh`).

## Recommendations
- Monitor `/Users/macos/anaconda3/envs/emag-db-docker/logs/` size via `manage_logs.sh` output (`logs/log_maintenance.log`). Adjust `MAX_DIR_MB`/`ARCHIVE_EXPIRY_DAYS` if required.
- Store this documentation alongside deployment runbooks so operators know each cron’s purpose and dependencies.
