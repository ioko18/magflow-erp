#!/usr/bin/env python3
"""
Run eMAG Product Synchronization for MAIN and FBE accounts.
This script directly calls the sync service to synchronize products.
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Now import app modules
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.services.emag_product_sync_service import EmagProductSyncService, SyncMode
from app.core.logging import get_logger

logger = get_logger(__name__)


async def run_sync():
    """Run product synchronization for both MAIN and FBE accounts."""
    
    print("\n" + "="*70)
    print("  eMAG Product Synchronization - MAIN & FBE Accounts")
    print("="*70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return False
    
    print(f"Database: {database_url.split('@')[1] if '@' in database_url else 'configured'}")
    
    # Create database engine and session
    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    results = {}
    
    # Sync both accounts
    for account_type in ["main", "fbe"]:
        print(f"\n{'─'*70}")
        print(f"  Synchronizing {account_type.upper()} Account")
        print(f"{'─'*70}\n")
        
        # Check credentials
        username = os.getenv(f"EMAG_{account_type.upper()}_USERNAME")
        password = os.getenv(f"EMAG_{account_type.upper()}_PASSWORD")
        
        if not username or not password:
            print(f"❌ Missing credentials for {account_type.upper()} account")
            results[account_type] = {"success": False, "error": "Missing credentials"}
            continue
        
        print(f"Account: {username}")
        print(f"Mode: Incremental")
        print(f"Max Pages: 5 (for testing)")
        print(f"Items per Page: 100\n")
        
        try:
            async with async_session_factory() as session:
                # Create sync service
                async with EmagProductSyncService(
                    db=session,
                    account_type=account_type,
                    conflict_strategy="emag_priority",
                ) as sync_service:
                    # Run synchronization
                    result = await sync_service.sync_all_products(
                        mode=SyncMode.INCREMENTAL,
                        max_pages=5,  # Limit to 5 pages for testing
                        items_per_page=100,
                        include_inactive=False,
                        timeout_seconds=600,  # 10 minutes timeout
                    )
                    
                    # Commit the session
                    await session.commit()
                    
                    # Store results
                    results[account_type] = {
                        "success": True,
                        "data": result
                    }
                    
                    # Print results
                    print(f"\n✅ {account_type.upper()} Account Sync Completed!")
                    print(f"   Total Processed: {result.get('total_processed', 0)}")
                    print(f"   Created: {result.get('created', 0)}")
                    print(f"   Updated: {result.get('updated', 0)}")
                    print(f"   Unchanged: {result.get('unchanged', 0)}")
                    print(f"   Failed: {result.get('failed', 0)}")
                    
                    if result.get('errors'):
                        print(f"\n⚠️  Errors encountered: {len(result['errors'])}")
                        for i, error in enumerate(result['errors'][:5], 1):
                            print(f"   {i}. {error}")
                        if len(result['errors']) > 5:
                            print(f"   ... and {len(result['errors']) - 5} more")
        
        except Exception as e:
            print(f"\n❌ {account_type.upper()} Account Sync Failed!")
            print(f"   Error: {str(e)}")
            logger.error(f"Sync failed for {account_type}: {e}", exc_info=True)
            results[account_type] = {
                "success": False,
                "error": str(e)
            }
        
        # Small delay between accounts
        if account_type == "main":
            await asyncio.sleep(2)
    
    # Close engine
    await engine.dispose()
    
    # Print summary
    print(f"\n{'='*70}")
    print("  Synchronization Summary")
    print(f"{'='*70}\n")
    
    for account_type, result in results.items():
        status = "✅ SUCCESS" if result.get("success") else "❌ FAILED"
        print(f"{account_type.upper()} Account: {status}")
        
        if result.get("success") and result.get("data"):
            data = result["data"]
            print(f"  - Processed: {data.get('total_processed', 0)}")
            print(f"  - Created: {data.get('created', 0)}")
            print(f"  - Updated: {data.get('updated', 0)}")
        elif result.get("error"):
            print(f"  - Error: {result['error']}")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")
    
    # Return success if at least one account synced
    return any(r.get("success") for r in results.values())


if __name__ == "__main__":
    try:
        success = asyncio.run(run_sync())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Synchronization interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        sys.exit(1)
