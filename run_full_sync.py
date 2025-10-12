#!/usr/bin/env python3
"""
Script complet pentru sincronizarea tuturor produselor eMAG.
Salvează produsele incremental în batch-uri pentru feedback în timp real.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.emag_api_client import EmagApiClient
from dotenv import load_dotenv
from sqlalchemy import and_, select

from app.core.database import async_session_factory
from app.models.emag_models import EmagProductV2

load_dotenv()


async def sync_account_with_incremental_save(
    username: str,
    password: str,
    account_type: str,
    batch_size: int = 50
):
    """
    Sincronizare completă cu salvare incrementală în batch-uri.
    """
    base_url = "https://marketplace-api.emag.ro/api-3"

    print(f"\n{'='*70}")
    print(f"🚀 Starting Full Sync for {account_type.upper()} Account")
    print(f"{'='*70}")

    stats = {
        "total_fetched": 0,
        "total_created": 0,
        "total_updated": 0,
        "total_errors": 0,
        "pages_processed": 0,
        "start_time": datetime.now()
    }

    async with EmagApiClient(
        username=username,
        password=password,
        base_url=base_url,
        timeout=60
    ) as client:

        page = 1
        batch = []

        while True:
            try:
                # Fetch page from API
                print(f"\n📥 Fetching page {page}...", end=" ", flush=True)

                response = await client.get_products(
                    page=page,
                    items_per_page=100,
                    filters={"status": "all"}
                )

                if not response or "results" not in response:
                    print("❌ No results")
                    break

                products = response["results"]

                if not products:
                    print("✅ Last page reached")
                    break

                print(f"✅ Got {len(products)} products")

                stats["total_fetched"] += len(products)
                stats["pages_processed"] = page

                # Add to batch
                batch.extend(products)

                # Save batch if reached batch_size or last page
                if len(batch) >= batch_size or len(products) < 100:
                    print(f"💾 Saving batch of {len(batch)} products...", end=" ", flush=True)

                    batch_stats = await save_products_batch(batch, account_type)
                    stats["total_created"] += batch_stats["created"]
                    stats["total_updated"] += batch_stats["updated"]
                    stats["total_errors"] += batch_stats["errors"]

                    print(f"✅ Created: {batch_stats['created']}, "
                          f"Updated: {batch_stats['updated']}, "
                          f"Errors: {batch_stats['errors']}")

                    # Clear batch
                    batch = []

                # Progress summary
                if page % 5 == 0:
                    elapsed = (datetime.now() - stats["start_time"]).total_seconds()
                    rate = stats["total_fetched"] / elapsed if elapsed > 0 else 0
                    print(f"\n📊 Progress: {stats['total_fetched']} products fetched, "
                          f"{stats['total_created']} created, "
                          f"{stats['total_updated']} updated "
                          f"({rate:.1f} products/sec)")

                # Check if last page
                if len(products) < 100:
                    break

                page += 1

                # Rate limiting
                await asyncio.sleep(0.4)

            except Exception as e:
                print(f"\n❌ Error on page {page}: {e}")
                stats["total_errors"] += 1
                break

        # Save any remaining products in batch
        if batch:
            print(f"\n💾 Saving final batch of {len(batch)} products...", end=" ", flush=True)
            batch_stats = await save_products_batch(batch, account_type)
            stats["total_created"] += batch_stats["created"]
            stats["total_updated"] += batch_stats["updated"]
            stats["total_errors"] += batch_stats["errors"]
            print(f"✅ Created: {batch_stats['created']}, "
                  f"Updated: {batch_stats['updated']}, "
                  f"Errors: {batch_stats['errors']}")

    # Final statistics
    elapsed = (datetime.now() - stats["start_time"]).total_seconds()

    print(f"\n{'='*70}")
    print(f"✅ {account_type.upper()} Account Sync Complete")
    print(f"{'='*70}")
    print(f"Products fetched:  {stats['total_fetched']}")
    print(f"Products created:  {stats['total_created']}")
    print(f"Products updated:  {stats['total_updated']}")
    print(f"Errors:            {stats['total_errors']}")
    print(f"Pages processed:   {stats['pages_processed']}")
    print(f"Time elapsed:      {elapsed:.1f} seconds")
    print(f"Rate:              {stats['total_fetched']/elapsed:.1f} products/sec")
    print(f"{'='*70}\n")

    return stats


async def save_products_batch(products: list, account_type: str) -> dict:
    """
    Salvează un batch de produse în baza de date.
    Returnează statistici despre operațiune.
    """
    stats = {"created": 0, "updated": 0, "errors": 0}

    async with async_session_factory() as session:
        for product_data in products:
            try:
                sku = product_data.get("part_number") or product_data.get("sku")
                if not sku:
                    stats["errors"] += 1
                    continue

                # Check if exists
                stmt = select(EmagProductV2).where(
                    and_(
                        EmagProductV2.sku == sku,
                        EmagProductV2.account_type == account_type
                    )
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    # Update
                    update_product_from_api_data(existing, product_data)
                    existing.last_synced_at = datetime.utcnow()
                    existing.sync_status = "synced"
                    existing.sync_attempts += 1
                    stats["updated"] += 1
                else:
                    # Create
                    new_product = create_product_from_api_data(product_data, account_type)
                    session.add(new_product)
                    stats["created"] += 1

            except Exception as e:
                print(f"\n⚠️  Error processing SKU {sku}: {e}")
                stats["errors"] += 1

        try:
            await session.commit()
        except Exception as e:
            await session.rollback()
            print(f"\n❌ Batch commit error: {e}")
            stats["errors"] += len(products)
            stats["created"] = 0
            stats["updated"] = 0

    return stats


def safe_int(value, default=0):
    """Conversie sigură la int."""
    if value is None or value == "":
        return default
    try:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return default
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_float(value, default=None):
    """Conversie sigură la float."""
    if value is None or value == "":
        return default
    try:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return default
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_str(value, default=""):
    """Conversie sigură la string."""
    if value is None:
        return default
    try:
        return str(value).strip()
    except:
        return default


def create_product_from_api_data(product_data: dict, account_type: str) -> EmagProductV2:
    """Creare produs nou din date API."""

    # Extract stock
    stock_quantity = 0
    if "stock" in product_data:
        stock_data = product_data["stock"]
        if isinstance(stock_data, list) and stock_data:
            stock_quantity = safe_int(stock_data[0].get("value", 0))
        elif isinstance(stock_data, dict):
            stock_quantity = safe_int(stock_data.get("value", 0))
        else:
            stock_quantity = safe_int(stock_data)

    # Extract characteristics
    characteristics = {}
    if "characteristics" in product_data and isinstance(product_data["characteristics"], list):
        for char in product_data["characteristics"]:
            if isinstance(char, dict) and "id" in char and "value" in char:
                characteristics[str(char["id"])] = {
                    "id": char["id"],
                    "value": char["value"],
                    "tag": char.get("tag"),
                }

    # Build attributes
    attributes = {
        "ean_codes": product_data.get("ean", []) if isinstance(product_data.get("ean"), list) else [],
        "vat_id": safe_int(product_data.get("vat_id")),
        "part_number_key": safe_str(product_data.get("part_number_key")),
    }
    attributes = {k: v for k, v in attributes.items() if v is not None and v != ""}

    return EmagProductV2(
        emag_id=safe_str(product_data.get("id")),
        sku=safe_str(product_data.get("part_number") or product_data.get("sku")),
        name=safe_str(product_data.get("name")),
        account_type=account_type,
        description=safe_str(product_data.get("description")),
        brand=safe_str(product_data.get("brand") or product_data.get("brand_name")),
        price=safe_float(product_data.get("sale_price") or product_data.get("price")),
        currency=safe_str(product_data.get("currency"), "RON"),
        stock_quantity=stock_quantity,
        category_id=safe_str(product_data.get("category_id")),
        emag_category_id=safe_str(product_data.get("category_id")),
        emag_category_name=safe_str(product_data.get("category_name")),
        is_active=product_data.get("status") == 1 or product_data.get("status") == "1",
        status=safe_str(product_data.get("status")),
        images=product_data.get("images", []) if isinstance(product_data.get("images"), list) else [],
        emag_characteristics=characteristics,
        attributes=attributes,
        sync_status="synced",
        last_synced_at=datetime.utcnow(),
    )


def update_product_from_api_data(product: EmagProductV2, product_data: dict):
    """Update produs existent cu date API."""

    # Update basic fields
    if "name" in product_data:
        product.name = safe_str(product_data["name"])
    if "description" in product_data:
        product.description = safe_str(product_data["description"])
    if "brand" in product_data or "brand_name" in product_data:
        product.brand = safe_str(product_data.get("brand") or product_data.get("brand_name"))

    # Update price
    if "sale_price" in product_data or "price" in product_data:
        product.price = safe_float(product_data.get("sale_price") or product_data.get("price"))

    # Update stock
    if "stock" in product_data:
        stock_data = product_data["stock"]
        if isinstance(stock_data, list) and stock_data:
            product.stock_quantity = safe_int(stock_data[0].get("value", 0))
        elif isinstance(stock_data, dict):
            product.stock_quantity = safe_int(stock_data.get("value", 0))
        else:
            product.stock_quantity = safe_int(stock_data)

    # Update status
    if "status" in product_data:
        product.status = safe_str(product_data["status"])
        product.is_active = product_data.get("status") == 1 or product_data.get("status") == "1"

    # Update images
    if "images" in product_data:
        product.images = product_data.get("images", []) if isinstance(product_data.get("images"), list) else []


async def main():
    """Main sync function."""

    print("\n" + "="*70)
    print(" "*15 + "🚀 FULL eMAG SYNC - MagFlow ERP")
    print("="*70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    # Get credentials
    main_username = os.getenv("EMAG_MAIN_USERNAME", "galactronice@yahoo.com")
    main_password = os.getenv("EMAG_MAIN_PASSWORD", "NB1WXDm")
    fbe_username = os.getenv("EMAG_FBE_USERNAME", "galactronice.fbe@yahoo.com")
    fbe_password = os.getenv("EMAG_FBE_PASSWORD", "GB6on54")

    overall_start = datetime.now()

    # Sync MAIN account
    main_stats = await sync_account_with_incremental_save(
        main_username,
        main_password,
        "main",
        batch_size=100  # Batch size for database commits
    )

    # Wait between accounts
    await asyncio.sleep(2)

    # Sync FBE account
    fbe_stats = await sync_account_with_incremental_save(
        fbe_username,
        fbe_password,
        "fbe",
        batch_size=100
    )

    # Overall statistics
    overall_elapsed = (datetime.now() - overall_start).total_seconds()
    total_products = main_stats["total_created"] + main_stats["total_updated"] + \
                     fbe_stats["total_created"] + fbe_stats["total_updated"]

    print("\n" + "="*70)
    print(" "*20 + "📊 FINAL STATISTICS")
    print("="*70)
    print("\nMAIN Account:")
    print(f"  Fetched: {main_stats['total_fetched']}")
    print(f"  Created: {main_stats['total_created']}")
    print(f"  Updated: {main_stats['total_updated']}")
    print(f"  Errors:  {main_stats['total_errors']}")

    print("\nFBE Account:")
    print(f"  Fetched: {fbe_stats['total_fetched']}")
    print(f"  Created: {fbe_stats['total_created']}")
    print(f"  Updated: {fbe_stats['total_updated']}")
    print(f"  Errors:  {fbe_stats['total_errors']}")

    print("\nOverall:")
    print(f"  Total products in DB: {total_products}")
    print(f"  Total time: {overall_elapsed:.1f} seconds")
    print(f"  Average rate: {total_products/overall_elapsed:.1f} products/sec")

    print("\n" + "="*70)
    print(" "*20 + "✅ SYNC COMPLETE!")
    print("="*70 + "\n")

    # Verify in database
    print("📊 Verifying database...")
    async with async_session_factory() as session:
        # Count by account type
        from sqlalchemy import func
        stmt = select(
            EmagProductV2.account_type,
            func.count(EmagProductV2.id)
        ).group_by(EmagProductV2.account_type)

        result = await session.execute(stmt)
        counts = dict(result.all())

        print("\nDatabase verification:")
        print(f"  MAIN products: {counts.get('main', 0)}")
        print(f"  FBE products:  {counts.get('fbe', 0)}")
        print(f"  Total:         {sum(counts.values())}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
