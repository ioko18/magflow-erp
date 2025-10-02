#!/usr/bin/env python3
"""
Sincronizare doar pentru contul FBE.
"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from sqlalchemy import select, and_
from app.core.database import async_session_factory
from app.services.emag_api_client import EmagApiClient
from app.models.emag_models import EmagProductV2

load_dotenv()

def safe_int(value, default=0):
    if value is None or value == "":
        return default
    try:
        return int(float(str(value).strip())) if str(value).strip() else default
    except (ValueError, TypeError):
        return default

def safe_float(value, default=None):
    if value is None or value == "":
        return default
    try:
        return float(str(value).strip()) if str(value).strip() else default
    except (ValueError, TypeError):
        return default

def safe_str(value, default=""):
    if value is None:
        return default
    try:
        return str(value).strip()
    except:
        return default

async def sync_fbe_complete():
    """Sincronizare completă FBE."""
    
    username = os.getenv("EMAG_FBE_USERNAME", "galactronice.fbe@yahoo.com")
    password = os.getenv("EMAG_FBE_PASSWORD", "GB6on54")
    base_url = "https://marketplace-api.emag.ro/api-3"
    
    print("\n" + "="*70)
    print("🚀 Full FBE Account Sync")
    print("="*70)
    
    stats = {
        "fetched": 0,
        "created": 0,
        "updated": 0,
        "errors": 0,
        "start": datetime.now()
    }
    
    async with EmagApiClient(username, password, base_url, timeout=60) as client:
        page = 1
        
        while True:
            try:
                print(f"\n📥 Page {page}...", end=" ", flush=True)
                
                response = await client.get_products(page=page, items_per_page=100)
                products = response.get("results", [])
                
                if not products:
                    print("✅ Done")
                    break
                
                print(f"{len(products)} products", end=" | ", flush=True)
                stats["fetched"] += len(products)
                
                # Save each product
                for product in products:
                    sku = product.get("part_number") or product.get("sku")
                    if not sku:
                        stats["errors"] += 1
                        continue
                    
                    async with async_session_factory() as session:
                        try:
                            stmt = select(EmagProductV2).where(
                                and_(
                                    EmagProductV2.sku == sku,
                                    EmagProductV2.account_type == "fbe"
                                )
                            )
                            result = await session.execute(stmt)
                            existing = result.scalar_one_or_none()
                            
                            # Extract stock
                            stock_qty = 0
                            if "stock" in product:
                                stock_data = product["stock"]
                                if isinstance(stock_data, list) and stock_data:
                                    stock_qty = safe_int(stock_data[0].get("value", 0))
                                elif isinstance(stock_data, dict):
                                    stock_qty = safe_int(stock_data.get("value", 0))
                                else:
                                    stock_qty = safe_int(stock_data)
                            
                            # Extract characteristics
                            characteristics = {}
                            if "characteristics" in product and isinstance(product["characteristics"], list):
                                for char in product["characteristics"]:
                                    if isinstance(char, dict) and "id" in char and "value" in char:
                                        characteristics[str(char["id"])] = {
                                            "id": char["id"],
                                            "value": char["value"],
                                            "tag": char.get("tag"),
                                        }
                            
                            if existing:
                                # Update
                                existing.name = safe_str(product.get("name"))
                                existing.price = safe_float(product.get("sale_price") or product.get("price"))
                                existing.stock_quantity = stock_qty
                                existing.is_active = product.get("status") == 1
                                existing.last_synced_at = datetime.utcnow()
                                existing.sync_status = "synced"
                                stats["updated"] += 1
                            else:
                                # Create
                                new_product = EmagProductV2(
                                    emag_id=safe_str(product.get("id")),
                                    sku=sku,
                                    name=safe_str(product.get("name")),
                                    account_type="fbe",
                                    description=safe_str(product.get("description")),
                                    brand=safe_str(product.get("brand") or product.get("brand_name")),
                                    price=safe_float(product.get("sale_price") or product.get("price")),
                                    currency="RON",
                                    stock_quantity=stock_qty,
                                    category_id=safe_str(product.get("category_id")),
                                    emag_category_id=safe_str(product.get("category_id")),
                                    emag_category_name=safe_str(product.get("category_name")),
                                    is_active=product.get("status") == 1,
                                    status=safe_str(product.get("status")),
                                    images=product.get("images", []) if isinstance(product.get("images"), list) else [],
                                    emag_characteristics=characteristics,
                                    attributes={"ean_codes": product.get("ean", []) if isinstance(product.get("ean"), list) else []},
                                    sync_status="synced",
                                    last_synced_at=datetime.utcnow()
                                )
                                session.add(new_product)
                                stats["created"] += 1
                            
                            await session.commit()
                            
                        except Exception as e:
                            await session.rollback()
                            stats["errors"] += 1
                            if stats["errors"] <= 5:  # Show first 5 errors only
                                print(f"\n⚠️  Error {sku}: {e}")
                
                print(f"✅ Created: {stats['created']}, Updated: {stats['updated']}")
                
                if len(products) < 100:
                    break
                
                page += 1
                await asyncio.sleep(0.4)
                
            except Exception as e:
                print(f"\n❌ Page error: {e}")
                break
    
    elapsed = (datetime.now() - stats["start"]).total_seconds()
    
    print("\n" + "="*70)
    print(f"✅ FBE Sync Complete")
    print("="*70)
    print(f"Fetched:  {stats['fetched']}")
    print(f"Created:  {stats['created']}")
    print(f"Updated:  {stats['updated']}")
    print(f"Errors:   {stats['errors']}")
    print(f"Time:     {elapsed:.1f}s")
    print(f"Rate:     {stats['fetched']/elapsed:.1f} products/sec")
    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(sync_fbe_complete())
