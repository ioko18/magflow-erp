#!/bin/bash
# Production eMAG Sync Script
# Usage: ./sync_production.sh [main|fbe|both] [days]

ACCOUNT=${1:-both}
DAYS=${2:-1}
LOG_LEVEL=${3:-INFO}

echo "🚀 Starting production eMAG sync..."
echo "Account: $ACCOUNT"
echo "Days: $DAYS"
echo "Log Level: $LOG_LEVEL"
echo "========================================"

cd /Users/macos/anaconda3/envs/MagFlow

python3 sync_emag_orders.py \
    --account "$ACCOUNT" \
    --days "$DAYS" \
    --log-level "$LOG_LEVEL" \
    --batch-size 20 \
    --concurrency 3

echo "✅ Production sync completed!"
