#!/usr/bin/env python3
"""
Sincronizare REALĂ din eMag API - Direct
Folosește serviciul de sincronizare existent
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.emag.emag_product_sync_service import EmagProductSyncService
from app.core.config import get_settings
from app.core.dependency_injection import ServiceContext


async def main():
    """Sincronizare reală din eMag API"""
    print("🚀 Sincronizare REALĂ din eMag FBE API")
    print("=" * 60)
    
    try:
        # Initialize service
        settings = get_settings()
        context = ServiceContext(settings=settings)
        
        # Create sync service
        sync_service = EmagProductSyncService(
            context=context,
            account_type="fbe"
        )
        
        print("📡 Conectare la eMag API...")
        print("⏳ Sincronizare în curs (poate dura 2-5 minute)...")
        print("")
        
        # Run sync
        result = await sync_service.sync_products(
            full_sync=False,
            max_pages=10  # Limitează la 10 pagini pentru test
        )
        
        print("\n✅ Sincronizare Completă!")
        print("=" * 60)
        print(f"📦 Produse sincronizate: {result.get('synced', 0)}")
        print(f"➕ Produse noi: {result.get('created', 0)}")
        print(f"🔄 Produse actualizate: {result.get('updated', 0)}")
        print(f"❌ Erori: {result.get('errors', 0)}")
        print("=" * 60)
        
        if result.get('errors', 0) > 0:
            print("\n⚠️  Unele produse au avut erori")
        else:
            print("\n🎉 Toate produsele sincronizate cu succes!")
            
        print("\n📋 Următorul pas:")
        print("Rulează: docker exec -i magflow_db psql -U app -d magflow < scripts/sql/sync_emag_fbe_to_inventory.sql")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Eroare la sincronizare: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
