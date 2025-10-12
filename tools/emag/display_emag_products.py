#!/usr/bin/env python3
"""
Display 5 products from eMAG Marketplace
"""

import os

import requests


def display_emag_products():
    """Display 5 products from eMAG Marketplace"""

    # Load credentials
    username = os.getenv("EMAG_API_USERNAME", "galactronice@yahoo.com")
    password = os.getenv("EMAG_API_PASSWORD", "NB1WXDm")
    api_url = "https://marketplace-api.emag.ro/api-3"

    print("🔐 Connecting to eMAG API...")
    print(f"📊 Username: {username}")
    print("-" * 50)

    try:
        # Fetch offers from eMAG
        print("📦 Fetching products from eMAG...")
        url = f"{api_url}/product_offer/read"
        data = {"data": {"currentPage": 1, "itemsPerPage": 5}}  # Get only 5 products

        response = requests.post(url, auth=(username, password), json=data, timeout=30)
        response.raise_for_status()

        result = response.json()
        if result.get("isError"):
            print(f"❌ API Error: {result.get('messages', [])}")
            return

        offers = result.get("results", [])
        print(f"✅ Got {len(offers)} products from eMAG")
        print("-" * 50)

        # Display products in a nice format
        for i, offer in enumerate(offers, 1):
            print(f"📦 Product {i}:")
            print(f"   ID: {offer.get('id', 'N/A')}")
            print(f"   Name: {offer.get('name', 'N/A')}")
            print(f"   Part Number: {offer.get('part_number', 'N/A')}")
            print(f"   Status: {'Active' if offer.get('status') == 1 else 'Inactive'}")
            print(f"   Stock: {offer.get('general_stock', 'N/A')}")
            print(f"   Price: {offer.get('price', 'N/A')}")
            print(f"   Sale Price: {offer.get('sale_price', 'N/A')}")
            if offer.get('images') and len(offer['images']) > 0:
                print(f"   Images: {len(offer['images'])} available")
            print("-" * 30)

        print("✅ Successfully displayed 5 products from eMAG Marketplace!")

    except Exception as e:
        print(f"❌ Error fetching products: {e}")

if __name__ == "__main__":
    display_emag_products()
