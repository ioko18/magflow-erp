#!/usr/bin/env python3
"""
Debug script to test eMAG API response and data processing
"""

import asyncio
import os
import requests
import json

async def debug_emag_api():
    """Debug eMAG API response and data structure"""
    username = os.getenv('EMAG_MAIN_USERNAME', 'galactronice@yahoo.com')
    password = os.getenv('EMAG_MAIN_PASSWORD', 'NB1WXDm')
    api_url = 'https://marketplace-api.emag.ro/api-3'

    print(f'🔐 Testing API connection with {username}...')

    try:
        url = f'{api_url}/product_offer/read'
        data = {'data': {'currentPage': 1, 'itemsPerPage': 3}}  # Just 3 items for debugging

        print(f"📡 Making request to: {url}")
        print(f"📦 Request data: {json.dumps(data, indent=2)}")

        response = requests.post(url, auth=(username, password), json=data, timeout=30)
        response.raise_for_status()

        result = response.json()
        print(f'✅ API Response status: {result.get("isError")}')
        print(f'✅ Response messages: {result.get("messages", [])}')

        if result.get('isError'):
            print(f'❌ API Error: {result.get("messages", [])}')
            return

        offers = result.get('results', [])
        print(f'✅ Got {len(offers)} offers')

        if offers:
            print('📋 First offer structure:')
            first_offer = offers[0]
            print(f'   Keys: {list(first_offer.keys())}')
            print(f'   ID: {first_offer.get("id")}')
            print(f'   Name: {first_offer.get("name", "")[:100]}...')
            print(f'   Part Number: {first_offer.get("part_number")}')
            print(f'   Status: {first_offer.get("status")}')
            print(f'   Category ID: {first_offer.get("category_id")}')
            print(f'   Brand ID: {first_offer.get("brand_id")}')
            print(f'   Price: {first_offer.get("price")}')
            print(f'   Stock: {first_offer.get("general_stock")}')
            print(f'   Raw first offer: {json.dumps(first_offer, indent=2, default=str)}')

            # Test data validation
            offer_id = str(first_offer.get('id', ''))
            print(f'✅ Validating offer ID: {offer_id} (valid: {bool(offer_id)})')

            # Test product data structure
            product_data = {
                "emag_id": offer_id,
                "name": first_offer.get("name", "")[:500],
                "description": first_offer.get("description", ""),
                "part_number": first_offer.get("part_number", ""),
                "emag_category_id": first_offer.get("category_id"),
                "emag_brand_id": first_offer.get("brand_id"),
                "emag_category_name": first_offer.get("category_name"),
                "emag_brand_name": first_offer.get("brand_name"),
                "characteristics": first_offer.get("characteristics", {}),
                "images": first_offer.get("images", []),
                "is_active": first_offer.get("status") == 1,
                "raw_data": first_offer,
            }
            print(f'✅ Product data structure: {json.dumps(product_data, indent=2, default=str)}')

        else:
            print('❌ No offers returned from API')

    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_emag_api())
