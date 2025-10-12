"""
Script to update MagFlow database with product information from eMAG API.
"""
import asyncio
import os
import re

# Import database models and session
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp
from dotenv import load_dotenv
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

# Add the app directory to the Python path
app_dir = str(Path(__file__).parent.parent / "app")
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

# Now import the modules
from app.db.session import get_async_session
from app.models.emag_offers import EmagProduct, EmagProductOffer

# Load environment variables
load_dotenv()

# API settings
EMAG_API_URL = os.getenv("EMAG_API_BASE_URL", "https://marketplace-api.emag.ro/api-3")
EMAG_API_USERNAME = os.getenv("EMAG_MAIN_USERNAME")
EMAG_API_PASSWORD = os.getenv("EMAG_MAIN_PASSWORD")

if not EMAG_API_USERNAME or not EMAG_API_PASSWORD:
    raise ValueError("eMAG API credentials not found in environment variables")


def clean_html(html: str) -> str:
    """Remove HTML tags from a string."""
    if not html:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', html)
    return ' '.join(clean.split())


def extract_product_name(offer: dict[str, Any]) -> str:
    """Extract product name from offer data."""
    # Try to get name from description first
    description = offer.get('description', '')
    name_match = re.search(r'<strong>Nume produs:</strong>\s*([^<]+)', description)
    if name_match:
        return clean_html(name_match.group(1).strip())

    # Fallback to name field
    name = offer.get('name', '')
    if name:
        # Clean up the name
        name = name.split(',')[0].split(' si ')[0].split(' pentru ')[0].strip()
        return clean_html(name)

    return "Unnamed Product"


async def get_or_create_emag_category(session: AsyncSession, category_name: str) -> dict:
    """Get or create an eMAG category mapping.

    Since we don't have a dedicated category mapping table, we'll just return
    a dictionary with the category information.
    """
    if not category_name:
        return None

    # For now, just return a dictionary with the category name
    # In a real implementation, this would check the database for an existing mapping
    return {
        'name': category_name,
        'emag_name': category_name,
        'status': 'active'
    }


async def update_or_create_emag_product(session: AsyncSession, offer: dict[str, Any]) -> EmagProduct:
    """Update or create an eMAG product in the database from eMAG offer data."""
    emag_id = str(offer.get('id'))
    name = extract_product_name(offer)
    description = clean_html(offer.get('description', ''))

    # Prepare product data
    product_data = {
        'emag_id': emag_id,
        'name': name,
        'description': description,
        'part_number': offer.get('part_number'),
        'emag_category_id': offer.get('category_id'),
        'emag_brand_id': offer.get('brand_id'),
        'emag_category_name': offer.get('category'),
        'emag_brand_name': offer.get('brand'),
        'characteristics': offer.get('characteristics', []),
        'images': [img.get('url') for img in offer.get('images', []) if img.get('url')],
        'is_active': offer.get('status') == 1,  # Assuming status 1 means active
        'last_imported_at': datetime.utcnow(),
        'emag_updated_at': offer.get('updated_at'),
        'raw_data': offer
    }

    # Create or update the eMAG product
    stmt = (
        insert(EmagProduct)
        .values(**product_data)
        .on_conflict_do_update(
            index_elements=['emag_id'],
            set_={
                'name': product_data['name'],
                'description': product_data['description'],
                'part_number': product_data['part_number'],
                'emag_category_id': product_data['emag_category_id'],
                'emag_brand_id': product_data['emag_brand_id'],
                'emag_category_name': product_data['emag_category_name'],
                'emag_brand_name': product_data['emag_brand_name'],
                'characteristics': product_data['characteristics'],
                'images': product_data['images'],
                'is_active': product_data['is_active'],
                'last_imported_at': product_data['last_imported_at'],
                'emag_updated_at': product_data['emag_updated_at'],
                'raw_data': product_data['raw_data'],
                'updated_at': datetime.utcnow()
            }
        )
        .returning(EmagProduct)
    )

    result = await session.execute(stmt)
    emag_product = result.scalar_one()

    # Create or update the offer
    offer_data = {
        'emag_product_id': emag_id,
        'emag_offer_id': offer.get('offer_id', emag_id),  # Use offer_id if available, otherwise use product_id
        'price': float(offer.get('sale_price', 0)),
        'sale_price': float(offer.get('sale_price', 0)),
        'currency': offer.get('currency', 'RON'),
        'stock': int(offer.get('stock', 0)),
        'stock_status': 'in_stock' if offer.get('stock', 0) > 0 else 'out_of_stock',
        'handling_time': offer.get('handling_time', [{}])[0].get('value') if isinstance(offer.get('handling_time'), list) else None,
        'status': 'active' if offer.get('status') == 1 else 'inactive',
        'is_available': bool(offer.get('status') == 1 and offer.get('stock', 0) > 0),
        'is_visible': bool(offer.get('status') == 1),
        'vat_rate': float(offer.get('vat_rate', 19)) if offer.get('vat_rate') is not None else None,
        'vat_included': True,  # Default to True as per eMAG's standard
        'warehouse_id': None,  # This would come from the offer data if available
        'warehouse_name': None,  # This would come from the offer data if available
        'account_type': 'main',  # Default to main account
        'warranty': int(offer.get('warranty', 0)) if offer.get('warranty') is not None else None,
        'last_imported_at': datetime.utcnow(),
        'emag_updated_at': offer.get('updated_at'),
        'import_batch_id': f"batch_{int(datetime.utcnow().timestamp())}",
        'raw_data': offer,
        'metadata_': {}
    }

    stmt = (
        insert(EmagProductOffer)
        .values(**offer_data)
        .on_conflict_do_update(
            index_elements=['emag_product_id', 'emag_offer_id'],
            set_={
                'price': offer_data['price'],
                'sale_price': offer_data['sale_price'],
                'currency': offer_data['currency'],
                'stock': offer_data['stock'],
                'stock_status': offer_data['stock_status'],
                'handling_time': offer_data['handling_time'],
                'status': offer_data['status'],
                'is_available': offer_data['is_available'],
                'is_visible': offer_data['is_visible'],
                'vat_rate': offer_data['vat_rate'],
                'warranty': offer_data['warranty'],
                'last_imported_at': offer_data['last_imported_at'],
                'emag_updated_at': offer_data['emag_updated_at'],
                'updated_at': datetime.utcnow()
            }
        )
    )

    await session.execute(stmt)
    await session.commit()

    # We're not handling category mappings in this version
    # as we don't have the EmagCategoryMapping model available
    # In a real implementation, you would handle category mappings here

    return emag_product


async def fetch_emag_offers(session: aiohttp.ClientSession, page: int = 1, per_page: int = 10) -> list[dict[str, Any]]:
    """Fetch product offers from eMAG API asynchronously."""
    auth = aiohttp.BasicAuth(EMAG_API_USERNAME, EMAG_API_PASSWORD)
    headers = {"Content-Type": "application/json"}
    data = {"page": page, "per_page": per_page}

    try:
        async with session.post(
            f"{EMAG_API_URL}/product_offer/read",
            auth=auth,
            headers=headers,
            json=data
        ) as response:
            response.raise_for_status()
            result = await response.json()

            if result.get('isError', False):
                print(f"API error: {result.get('messages', 'Unknown error')}")
                return []

            return result.get('results', [])
    except Exception as e:
        print(f"Error fetching eMAG offers: {e}")
        return []


async def main():
    """Main function to update products from eMAG."""
    print("Starting product update from eMAG...")

    # Create aiohttp client session
    async with aiohttp.ClientSession() as http_session:
        # Get database session
        async for db_session in get_async_session():
            try:
                # Fetch offers from eMAG
                print("Fetching products from eMAG...")
                offers = await fetch_emag_offers(http_session, per_page=5)  # Adjust per_page as needed

                if not offers:
                    print("No offers found or error fetching offers.")
                    return

                # Process each offer
                for i, offer in enumerate(offers, 1):
                    try:
                        product_name = extract_product_name(offer)
                        print(f"Processing product {i}/{len(offers)}: {product_name[:50]}...")
                        emag_product = await update_or_create_emag_product(db_session, offer)
                        print(f"  - {'Updated' if hasattr(emag_product, 'id') and emag_product.id else 'Created'} eMAG product: {emag_product.name}")
                    except Exception as e:
                        print(f"Error processing offer {i}: {e}")
                        import traceback
                        traceback.print_exc()

                print("Product update completed successfully!")

            except Exception as e:
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()
                if 'db_session' in locals():
                    await db_session.rollback()
            finally:
                if 'db_session' in locals():
                    await db_session.close()


if __name__ == "__main__":
    asyncio.run(main())
