#!/usr/bin/env python3
"""
Simple eMAG Sync Script for MagFlow ERP.

This script performs a basic eMAG API test without requiring the full
application stack, useful for testing API connectivity and credentials.
"""

import asyncio
import base64
import os
import sys
from datetime import datetime
from pathlib import Path

import aiohttp

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
env_file = project_root / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if line.strip() and not line.startswith("#") and "=" in line:
                key, value = line.strip().split("=", 1)
                os.environ[key] = value


class SimpleEmagClient:
    """Simple eMAG API client for testing."""

    def __init__(self, username: str, password: str, account_type: str = "main"):
        self.username = username
        self.password = password
        self.account_type = account_type
        self.base_url = "https://marketplace-api.emag.ro/api-3"

        # Create Basic Auth header
        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.auth_header = f"Basic {encoded_credentials}"

    async def test_connection(self):
        """Test API connection with a simple request."""
        url = f"{self.base_url}/product_offer/read"

        headers = {
            "Authorization": self.auth_header,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Simple request to get first page with 1 item
        data = {"data": {"currentPage": 1, "itemsPerPage": 1}}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json=data, headers=headers, timeout=30
                ) as response:
                    status = response.status
                    content_type = response.headers.get("Content-Type", "")

                    if "json" in content_type.lower():
                        result = await response.json()
                    else:
                        text = await response.text()
                        result = {"error": "Non-JSON response", "body": text[:500]}

                    return {
                        "status_code": status,
                        "success": status == 200,
                        "content_type": content_type,
                        "response": result,
                    }
        except Exception as e:
            return {
                "status_code": 0,
                "success": False,
                "error": str(e),
                "response": None,
            }

    async def get_products_sample(self, max_pages: int = 2):
        """Get a sample of products from eMAG."""
        url = f"{self.base_url}/product_offer/read"

        headers = {
            "Authorization": self.auth_header,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        all_products = []

        for page in range(1, max_pages + 1):
            print(f"  Fetching page {page}...")

            data = {
                "data": {
                    "currentPage": page,
                    "itemsPerPage": 10,  # Small number for testing
                }
            }

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url, json=data, headers=headers, timeout=30
                    ) as response:
                        if response.status == 200:
                            result = await response.json()

                            if not result.get("isError", True):
                                products = result.get("results", [])
                                all_products.extend(products)
                                print(f"    ✅ Page {page}: {len(products)} products")

                                # Check if we have more pages
                                pagination = result.get("pagination", {})
                                if page >= pagination.get("totalPages", 0):
                                    total_pages = pagination.get("totalPages", 0)
                                    print(
                                        "    ℹ️  Reached last page ("
                                        f"{total_pages}"
                                        ")"
                                    )
                                    break
                            else:
                                error_msg = result.get(
                                    "messages", [{"message": "Unknown error"}]
                                )[0].get("message", "Unknown error")
                                print(f"    ❌ Page {page}: API error - {error_msg}")
                                break
                        elif response.status == 429:
                            print(f"    ⚠️  Page {page}: Rate limited, waiting...")
                            await asyncio.sleep(2)
                            continue
                        else:
                            print(f"    ❌ Page {page}: HTTP {response.status}")
                            break

            except Exception as e:
                print(f"    ❌ Page {page}: Exception - {str(e)}")
                break

            # Small delay between requests
            await asyncio.sleep(1.5)

        return all_products


async def test_emag_sync(account_type: str = "main", max_pages: int = 2):
    """Test eMAG synchronization."""
    print(f"\nTesting eMAG {account_type.upper()} Account Sync")
    print("=" * 50)

    # Get credentials
    username = os.getenv(f"EMAG_{account_type.upper()}_USERNAME")
    password = os.getenv(f"EMAG_{account_type.upper()}_PASSWORD")

    if not username or not password:
        print(f"❌ {account_type.upper()} account credentials not configured")
        return False

    print(f"Account: {username}")
    print(f"Max pages: {max_pages}")

    # Create client
    client = SimpleEmagClient(username, password, account_type)

    # Test connection
    print("\n1. Testing API connection...")
    connection_result = await client.test_connection()

    if connection_result["success"]:
        print("   ✅ Connection successful")

        # Check response structure
        response = connection_result.get("response", {})
        if isinstance(response, dict):
            if not response.get("isError", True):
                response.get("results", [])
                pagination = response.get("pagination", {})
                print("   ✅ API response valid")
                print(
                    "   ℹ️  Total items available: "
                    f"{pagination.get('totalItems', 'unknown')}"
                )
                print(
                    "   ℹ️  Total pages available: "
                    f"{pagination.get('totalPages', 'unknown')}"
                )
            else:
                error_msg = response.get("messages", [{"message": "Unknown error"}])[
                    0
                ].get("message", "Unknown error")
                print(f"   ⚠️  API returned error: {error_msg}")
        else:
            print("   ⚠️  Unexpected response format")
    else:
        print(
            f"   ❌ Connection failed: {connection_result.get('error', 'Unknown error')}"
        )
        if connection_result.get("status_code") == 401:
            print("   ℹ️  Check credentials and IP whitelist")
        elif connection_result.get("status_code") == 429:
            print("   ℹ️  Rate limited - try again later")
        return False

    # Test product sync
    print(f"\n2. Testing product sync ({max_pages} pages)...")
    products = await client.get_products_sample(max_pages)

    print("\n3. Sync Results:")
    print(f"   Products retrieved: {len(products)}")

    if products:
        sample_product = products[0]
        print("   Sample product:")
        print(f"     ID: {sample_product.get('id', 'N/A')}")
        print(f"     SKU: {sample_product.get('part_number', 'N/A')}")
        print(f"     Name: {sample_product.get('name', 'N/A')[:50]}...")
        print(
            "     Price: "
            f"{sample_product.get('price', 'N/A')} "
            f"{sample_product.get('currency', 'RON')}"
        )
        print(f"     Stock: {sample_product.get('stock', 'N/A')}")

    return len(products) > 0


async def main():
    """Main function."""
    print("MagFlow ERP - Simple eMAG Sync Test")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test both accounts
    main_success = await test_emag_sync("main", 2)
    fbe_success = await test_emag_sync("fbe", 2)

    # Summary
    print("\nSync Test Summary")
    print("=" * 50)
    print(f"MAIN Account: {'✅ SUCCESS' if main_success else '❌ FAILED'}")
    print(f"FBE Account:  {'✅ SUCCESS' if fbe_success else '❌ FAILED'}")

    if main_success or fbe_success:
        print("\n✅ eMAG integration is working!")
        print("✅ Ready for full synchronization")
    else:
        print("\n❌ eMAG integration needs attention")
        print("❌ Check credentials and network connectivity")

    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    asyncio.run(main())
