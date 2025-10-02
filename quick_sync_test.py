#!/usr/bin/env python3
"""Test rapid de sincronizare - doar câteva produse."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from sqlalchemy import select, func
from app.core.database import async_session_factory
from app.services.emag_api_client import EmagApiClient
from app.models.emag_models import EmagProductV2

load_dotenv()

async def quick_test():
    """Test rapid - sincronizează doar 10 produse."""
    
    print("\n" + "="*70)
    print("🧪 Quick Sync Test - 10 Products")
    print("="*70)
    
    username = os.getenv("EMAG_MAIN_USERNAME", "galactronice@yahoo.com")
    password = os.getenv("EMAG_MAIN_PASSWORD", "NB1WXDm")
    base_url = "https://marketplace-api.emag.ro/api-3"
    
    # Fetch 10 products
    print("\n📥 Fetching 10 products from API...")
    async with EmagApiClient(username, password, base_url, timeout=60) as client:
        response = await client.get_products(page=1, items_per_page=10)
        products = response.get("results", [])
        print(f"✅ Got {len(products)} products")
    
    # Try to save one
    if products:
        product = products[0]
        sku = product.get("part_number") or product.get("sku")
        print(f"\n💾 Testing save for SKU: {sku}")
        
        async with async_session_factory() as session:
            try:
                # Check if exists
                stmt = select(EmagProductV2).where(
                    EmagProductV2.sku == sku,
                    EmagProductV2.account_type == "main"
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                
                if existing:
                    print(f"✅ Product exists: {existing.name}")
                else:
                    # Try to create
                    new_product = EmagProductV2(
                        emag_id=str(product.get("id", "")),
                        sku=sku,
                        name=product.get("name", ""),
                        account_type="main",
                        price=float(product.get("sale_price") or product.get("price") or 0),
                        currency="RON",
                        is_active=product.get("status") == 1,
                        sync_status="synced"
                    )
                    session.add(new_product)
                    await session.commit()
                    print(f"✅ Product created: {new_product.name}")
                
            except Exception as e:
                await session.rollback()
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
    
    # Check counts
    print("\n📊 Database counts:")
    async with async_session_factory() as session:
        stmt = select(
            EmagProductV2.account_type,
            func.count(EmagProductV2.id)
        ).group_by(EmagProductV2.account_type)
        
        result = await session.execute(stmt)
        counts = dict(result.fetchall())
        
        print(f"  MAIN: {counts.get('main', 0)}")
        print(f"  FBE:  {counts.get('fbe', 0)}")
        print(f"  Total: {sum(counts.values())}")
    
    print("\n" + "="*70)
    print("✅ Quick Test Complete")
    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(quick_test())
