#!/usr/bin/env python3
"""
Simple End-to-End Test for eMAG Product Publishing

Usage:
    python test_publishing_simple.py
"""

import asyncio
import sys

import httpx

BASE_URL = "http://localhost:8000"
CREDENTIALS = {"username": "admin@example.com", "password": "secret"}


async def test_endpoints():
    """Test all product publishing endpoints"""
    results = {"passed": 0, "failed": 0}

    print("\n" + "="*60)
    print("  eMAG Product Publishing - E2E Test")
    print("="*60)

    # Authenticate
    print("\n🔐 Authenticating...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/v1/auth/login",
                json=CREDENTIALS,
                timeout=10.0
            )

            if response.status_code == 200:
                token = response.json().get("access_token")
                print("✓ Authentication successful")
                headers = {"Authorization": f"Bearer {token}"}
            else:
                print(f"✗ Authentication failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"✗ Authentication error: {e}")
        return False

    # Test VAT Rates
    print("\n📊 Testing VAT Rates...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/api/v1/emag/publishing/vat-rates?account_type=main",
                headers=headers,
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                count = data.get("data", {}).get("count", 0)
                print(f"✓ VAT Rates: {count} rates found")
                results["passed"] += 1
            else:
                print(f"✗ VAT Rates failed: {response.status_code}")
                results["failed"] += 1
    except Exception as e:
        print(f"✗ VAT Rates error: {e}")
        results["failed"] += 1

    # Test Handling Times
    print("\n⏱️  Testing Handling Times...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/api/v1/emag/publishing/handling-times?account_type=main",
                headers=headers,
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                count = data.get("data", {}).get("count", 0)
                print(f"✓ Handling Times: {count} options found")
                results["passed"] += 1
            else:
                print(f"✗ Handling Times failed: {response.status_code}")
                results["failed"] += 1
    except Exception as e:
        print(f"✗ Handling Times error: {e}")
        results["failed"] += 1

    # Test Categories
    print("\n📁 Testing Categories...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/api/v1/emag/publishing/categories?current_page=1&items_per_page=5&account_type=main",
                headers=headers,
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                results_data = data.get("data", {}).get("results", [])
                print(f"✓ Categories: {len(results_data)} categories retrieved")

                # Show first category
                if results_data:
                    cat = results_data[0]
                    print(f"  Sample: ID={cat.get('id')}, Name={cat.get('name')}")

                results["passed"] += 1
            else:
                print(f"✗ Categories failed: {response.status_code}")
                results["failed"] += 1
    except Exception as e:
        print(f"✗ Categories error: {e}")
        results["failed"] += 1

    # Test Allowed Categories
    print("\n✅ Testing Allowed Categories...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/api/v1/emag/publishing/categories/allowed?account_type=main",
                headers=headers,
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                categories = data.get("data", {}).get("categories", [])
                print(f"✓ Allowed Categories: {len(categories)} categories")
                results["passed"] += 1
            else:
                print(f"✗ Allowed Categories failed: {response.status_code}")
                results["failed"] += 1
    except Exception as e:
        print(f"✗ Allowed Categories error: {e}")
        results["failed"] += 1

    # Display Results
    print("\n" + "="*60)
    print("  Test Results Summary")
    print("="*60)
    total = results["passed"] + results["failed"]
    pass_rate = (results["passed"] / total * 100) if total > 0 else 0
    print(f"Total Tests: {total}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Pass Rate: {pass_rate:.1f}%")

    if results["failed"] == 0:
        print("\n✅ All tests passed!")
        return True
    else:
        print(f"\n❌ {results['failed']} test(s) failed")
        return False


async def main():
    """Main entry point"""
    success = await test_endpoints()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
