#!/usr/bin/env python3
"""
Script to run eMAG product synchronization for both MAIN and FBE accounts.
"""

import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

from app.core.database import async_session_factory
from app.services.emag_product_sync_service import EmagProductSyncService, SyncMode
from app.core.logging import get_logger

logger = get_logger(__name__)


async def run_sync():
    """Run synchronization for both accounts."""
    
    print("=" * 80)
    print("eMAG PRODUCT SYNCHRONIZATION")
    print("=" * 80)
    print()
    
    # Test credentials
    main_username = os.getenv("EMAG_MAIN_USERNAME")
    main_password = os.getenv("EMAG_MAIN_PASSWORD")
    fbe_username = os.getenv("EMAG_FBE_USERNAME")
    fbe_password = os.getenv("EMAG_FBE_PASSWORD")
    
    print("Checking credentials...")
    print(f"MAIN account: {'✓ Configured' if main_username and main_password else '✗ Missing'}")
    print(f"FBE account:  {'✓ Configured' if fbe_username and fbe_password else '✗ Missing'}")
    print()
    
    if not (main_username and main_password):
        print("ERROR: MAIN account credentials not configured!")
        return False
    
    if not (fbe_username and fbe_password):
        print("WARNING: FBE account credentials not configured, will sync MAIN only")
        account_type = "main"
    else:
        account_type = "both"
    
    print(f"Starting synchronization for: {account_type.upper()}")
    print()
    
    try:
        async with async_session_factory() as db:
            async with EmagProductSyncService(
                db=db,
                account_type=account_type,
                conflict_strategy="emag_priority"
            ) as sync_service:
                
                print("Synchronization started...")
                print("Mode: INCREMENTAL")
                print("Max pages: 10 (for testing)")
                print("Items per page: 100")
                print()
                
                result = await sync_service.sync_all_products(
                    mode=SyncMode.INCREMENTAL,
                    max_pages=10,  # Limit for testing
                    items_per_page=100,
                    include_inactive=False,
                    timeout_seconds=600,  # 10 minutes
                )
                
                # Commit the transaction
                await db.commit()
                
                print()
                print("=" * 80)
                print("SYNCHRONIZATION COMPLETED")
                print("=" * 80)
                print()
                print(f"Total processed: {result['total_processed']}")
                print(f"Created:         {result['created']}")
                print(f"Updated:         {result['updated']}")
                print(f"Unchanged:       {result['unchanged']}")
                print(f"Failed:          {result['failed']}")
                print()
                
                if result['errors']:
                    print("ERRORS:")
                    for error in result['errors'][:10]:  # Show first 10 errors
                        print(f"  - {error}")
                    if len(result['errors']) > 10:
                        print(f"  ... and {len(result['errors']) - 10} more errors")
                    print()
                
                return True
                
    except Exception as e:
        print()
        print("=" * 80)
        print("SYNCHRONIZATION FAILED")
        print("=" * 80)
        print()
        print(f"Error: {e}")
        logger.error(f"Sync failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(run_sync())
    sys.exit(0 if success else 1)
