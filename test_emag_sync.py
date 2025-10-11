#!/usr/bin/env python3
"""
Test eMag Inventory Sync
Sincronizează stocul din emag_product_offers în inventory_items
"""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.db import async_session_maker
from app.api.v1.endpoints.inventory.emag_inventory_sync import _sync_emag_to_inventory


async def main():
    """Run sync test"""
    print("🚀 Starting eMag Inventory Sync Test...")
    print("=" * 60)
    
    async with async_session_maker() as db:
        try:
            stats = await _sync_emag_to_inventory(db, account_type="fbe")
            
            print("\n✅ Sync Completed Successfully!")
            print("=" * 60)
            print(f"📦 Warehouse Created: {stats['warehouse_created']}")
            print(f"📊 Products Synced: {stats['products_synced']}")
            print(f"➕ Created: {stats.get('created', 0)}")
            print(f"🔄 Updated: {stats.get('updated', 0)}")
            print(f"❌ Errors: {stats['errors']}")
            print(f"⚠️  Low Stock Count: {stats['low_stock_count']}")
            print("=" * 60)
            
            if stats['errors'] > 0:
                print("\n⚠️  Some errors occurred during sync")
            else:
                print("\n🎉 All products synced successfully!")
                
        except Exception as e:
            print(f"\n❌ Sync Failed: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
