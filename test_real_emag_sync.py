#!/usr/bin/env python3
"""
Test script pentru sincronizarea reală cu API-ul eMAG.
"""

import asyncio
import os
from dotenv import load_dotenv
from app.services.enhanced_emag_service import EnhancedEmagIntegrationService
from app.core.database import get_async_session


async def test_real_emag_sync():
    """Testează sincronizarea reală cu API-ul eMAG pentru ambele conturi."""

    # Încarcă variabilele de mediu
    load_dotenv()

    print("🚀 Testez sincronizarea reală cu API-ul eMAG...")

    # Test sincronizare MAIN account
    print("\n📱 Testez sincronizarea contului MAIN...")

    try:
        async with EnhancedEmagIntegrationService("main") as main_service:
            print("✅ Serviciu MAIN inițializat")

            # Sincronizare produse - doar prima pagină pentru test
            print("📦 Sincronizez produsele din contul MAIN (prima pagină)...")
            main_results = await main_service._sync_products_from_account(
                max_pages=1,  # Doar prima pagină pentru test
                delay_between_requests=1.0,
                include_inactive=False,
            )

            print(f"✅ MAIN - Sincronizate {main_results['products_count']} produse")
            print(f"📊 MAIN - Pagini procesate: {main_results['pages_processed']}")

            # Afișează primele 3 produse
            if main_results["products"]:
                print("🔍 Primele 3 produse MAIN:")
                for i, product in enumerate(main_results["products"][:3]):
                    print(
                        f"  {i+1}. {product['name']} (SKU: {product['sku']}) - {product['action']}"
                    )

    except Exception as e:
        print(f"❌ Eroare sincronizare MAIN: {e}")

    print("\n" + "=" * 60)

    # Test sincronizare FBE account
    print("\n🏪 Testez sincronizarea contului FBE...")

    try:
        async with EnhancedEmagIntegrationService("fbe") as fbe_service:
            print("✅ Serviciu FBE inițializat")

            # Sincronizare produse - doar prima pagină pentru test
            print("📦 Sincronizez produsele din contul FBE (prima pagină)...")
            fbe_results = await fbe_service._sync_products_from_account(
                max_pages=1,  # Doar prima pagină pentru test
                delay_between_requests=1.0,
                include_inactive=False,
            )

            print(f"✅ FBE - Sincronizate {fbe_results['products_count']} produse")
            print(f"📊 FBE - Pagini procesate: {fbe_results['pages_processed']}")

            # Afișează primele 3 produse
            if fbe_results["products"]:
                print("🔍 Primele 3 produse FBE:")
                for i, product in enumerate(fbe_results["products"][:3]):
                    print(
                        f"  {i+1}. {product['name']} (SKU: {product['sku']}) - {product['action']}"
                    )

    except Exception as e:
        print(f"❌ Eroare sincronizare FBE: {e}")

    print("\n" + "=" * 60)

    # Verifică produsele în baza de date
    print("\n🗄️  Verific produsele în baza de date...")

    try:
        async for db in get_async_session():
            from sqlalchemy import select, func
            from app.models.emag_models import EmagProductV2

            # Numără produsele per cont
            main_count_stmt = select(func.count(EmagProductV2.id)).where(
                EmagProductV2.account_type == "main"
            )
            main_count = await db.execute(main_count_stmt)
            main_total = main_count.scalar()

            fbe_count_stmt = select(func.count(EmagProductV2.id)).where(
                EmagProductV2.account_type == "fbe"
            )
            fbe_count = await db.execute(fbe_count_stmt)
            fbe_total = fbe_count.scalar()

            print(f"📊 Produse în baza de date:")
            print(f"   MAIN: {main_total} produse")
            print(f"   FBE: {fbe_total} produse")
            print(f"   TOTAL: {main_total + fbe_total} produse")

            # Afișează ultimele 5 produse sincronizate
            recent_stmt = (
                select(EmagProductV2)
                .order_by(EmagProductV2.last_synced_at.desc())
                .limit(5)
            )
            recent_result = await db.execute(recent_stmt)
            recent_products = recent_result.scalars().all()

            if recent_products:
                print(f"\n🕒 Ultimele 5 produse sincronizate:")
                for i, product in enumerate(recent_products):
                    sync_time = (
                        product.last_synced_at.strftime("%H:%M:%S")
                        if product.last_synced_at
                        else "N/A"
                    )
                    print(
                        f"  {i+1}. [{product.account_type.upper()}] {product.name[:50]}... (SKU: {product.sku}) - {sync_time}"
                    )

            break

    except Exception as e:
        print(f"❌ Eroare verificare baza de date: {e}")

    print("\n✅ Test sincronizare completat!")


if __name__ == "__main__":
    asyncio.run(test_real_emag_sync())
