#!/usr/bin/env python3
"""
Script de testare pentru a determina numărul real de produse din API-ul eMAG.
"""

import asyncio
import os
from dotenv import load_dotenv
import aiohttp

load_dotenv()

async def count_emag_products(username: str, password: str, account_name: str):
    """Count actual products from eMAG API with proper pagination."""
    
    base_url = "https://marketplace-api.emag.ro/api-3"
    auth = aiohttp.BasicAuth(username, password)
    
    async with aiohttp.ClientSession(auth=auth) as session:
        page = 1
        total_products = 0
        unique_skus = set()
        
        print(f"\n{'='*60}")
        print(f"Testing {account_name} Account")
        print(f"{'='*60}")
        
        while True:
            try:
                url = f"{base_url}/product_offer/read"
                data = {
                    "currentPage": page,
                    "itemsPerPage": 100,  # Max allowed by eMAG API
                }
                
                async with session.post(url, json=data, timeout=30) as response:
                    if response.status != 200:
                        print(f"❌ Error on page {page}: HTTP {response.status}")
                        break
                    
                    result = await response.json()
                    
                    # Check for API errors
                    if result.get("isError", False):
                        messages = result.get("messages", [])
                        print(f"❌ API Error on page {page}: {messages}")
                        break
                    
                    # Get products from results
                    products = result.get("results", [])
                    
                    if not products:
                        print(f"\n✅ No more products on page {page}")
                        break
                    
                    # Count unique SKUs
                    page_skus = set()
                    for product in products:
                        sku = product.get("part_number") or product.get("sku")
                        if sku:
                            unique_skus.add(sku)
                            page_skus.add(sku)
                    
                    total_products += len(products)
                    new_unique = len(page_skus - (unique_skus - page_skus))
                    
                    print(f"Page {page:3d}: {len(products):3d} products | "
                          f"New unique: {new_unique:3d} | "
                          f"Total unique: {len(unique_skus):4d} | "
                          f"Total processed: {total_products:4d}")
                    
                    # Check if we got less than requested (last page)
                    if len(products) < 100:
                        print(f"\n✅ Last page reached (got {len(products)} products)")
                        break
                    
                    page += 1
                    
                    # Safety limit to prevent infinite loops
                    if page > 1000:
                        print(f"\n⚠️ Safety limit reached (1000 pages)")
                        break
                    
                    # Small delay to respect rate limits
                    await asyncio.sleep(0.4)
                    
            except asyncio.TimeoutError:
                print(f"⚠️ Timeout on page {page}")
                break
            except Exception as e:
                print(f"❌ Error on page {page}: {e}")
                break
        
        print(f"\n{'='*60}")
        print(f"Results for {account_name}")
        print(f"{'='*60}")
        print(f"Total products processed: {total_products}")
        print(f"Unique SKUs found: {len(unique_skus)}")
        print(f"Pages processed: {page - 1}")
        print(f"Duplicate products: {total_products - len(unique_skus)}")
        
        return {
            "account": account_name,
            "total_products": total_products,
            "unique_skus": len(unique_skus),
            "pages_processed": page - 1,
            "duplicates": total_products - len(unique_skus),
            "sku_list": sorted(list(unique_skus))
        }


async def main():
    """Main test function."""
    
    # Get credentials from environment
    main_username = os.getenv("EMAG_MAIN_USERNAME", "galactronice@yahoo.com")
    main_password = os.getenv("EMAG_MAIN_PASSWORD", "NB1WXDm")
    
    fbe_username = os.getenv("EMAG_FBE_USERNAME", "galactronice.fbe@yahoo.com")
    fbe_password = os.getenv("EMAG_FBE_PASSWORD", "GB6on54")
    
    print("\n" + "="*60)
    print("eMAG API Product Count Test")
    print("="*60)
    
    # Test MAIN account
    main_results = await count_emag_products(main_username, main_password, "MAIN")
    
    # Wait between accounts
    await asyncio.sleep(2)
    
    # Test FBE account
    fbe_results = await count_emag_products(fbe_username, fbe_password, "FBE")
    
    # Combined results
    print(f"\n{'='*60}")
    print("COMBINED RESULTS")
    print(f"{'='*60}")
    print(f"MAIN Account:")
    print(f"  - Products: {main_results['total_products']}")
    print(f"  - Unique SKUs: {main_results['unique_skus']}")
    print(f"  - Duplicates: {main_results['duplicates']}")
    print(f"\nFBE Account:")
    print(f"  - Products: {fbe_results['total_products']}")
    print(f"  - Unique SKUs: {fbe_results['unique_skus']}")
    print(f"  - Duplicates: {fbe_results['duplicates']}")
    
    # Check for overlapping SKUs
    main_skus = set(main_results['sku_list'])
    fbe_skus = set(fbe_results['sku_list'])
    overlap = main_skus & fbe_skus
    
    print(f"\nCross-Account Analysis:")
    print(f"  - SKUs in both accounts: {len(overlap)}")
    print(f"  - MAIN only: {len(main_skus - fbe_skus)}")
    print(f"  - FBE only: {len(fbe_skus - main_skus)}")
    print(f"  - Total unique across both: {len(main_skus | fbe_skus)}")
    
    if overlap:
        print(f"\n⚠️ Warning: {len(overlap)} SKUs found in both accounts!")
        if len(overlap) <= 10:
            print(f"Overlapping SKUs: {', '.join(sorted(list(overlap)))}")
    
    print(f"\n{'='*60}")
    print("CONCLUSION")
    print(f"{'='*60}")
    
    if main_results['unique_skus'] == 1179 and fbe_results['unique_skus'] == 1171:
        print("✅ API returns expected product counts!")
        print("   Issue is in synchronization code, not API.")
    elif main_results['unique_skus'] < 200 and fbe_results['unique_skus'] < 200:
        print("⚠️ API appears to return limited products.")
        print("   This might be an API limitation or account restriction.")
    else:
        print(f"📊 API returns different counts than expected:")
        print(f"   Expected MAIN: 1179, Got: {main_results['unique_skus']}")
        print(f"   Expected FBE: 1171, Got: {fbe_results['unique_skus']}")
    
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
