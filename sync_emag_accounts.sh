#!/bin/bash
# eMAG Multi-Account Sync Scripts

echo "🚀 eMAG Multi-Account Synchronization"
echo "====================================="

# Function to sync specific account
sync_account() {
    local account_type=$1
    local account_name=$2

    echo "📡 Syncing $account_name account..."
    EMAG_ACCOUNT_TYPE=$account_type python3 sync_emag_sync.py

    if [ $? -eq 0 ]; then
        echo "✅ $account_name sync completed successfully"
    else
        echo "❌ $account_name sync failed"
    fi
    echo ""
}

# Main Account Sync
sync_account "main" "MAIN (Seller-Fulfilled)"

# FBE Account Sync
sync_account "fbe" "FBE (Fulfillment by eMAG)"

# Auto Mode Sync (tries MAIN first, fallback to FBE)
echo "🔄 Running AUTO mode (MAIN first, FBE fallback)..."
EMAG_ACCOUNT_TYPE=auto python3 sync_emag_sync.py

if [ $? -eq 0 ]; then
    echo "✅ AUTO mode sync completed successfully"
else
    echo "❌ AUTO mode sync failed"
fi

echo "🎯 All sync operations completed!"
