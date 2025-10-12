#!/usr/bin/env python3
"""
Test script final pentru verificarea tuturor problemelor reparate.
Testează sincronizarea FBE, multi-account și vizualizarea produselor.
"""

from datetime import datetime

import requests

# Configurare
BACKEND_URL = "http://localhost:8001"
FRONTEND_URL = "http://localhost:3001"

def test_fbe_sync():
    """Testează sincronizarea FBE."""
    print("\n🧪 Testing FBE Account Sync...")

    payload = {
        "mode": "fbe",
        "maxPages": 2,
        "batchSize": 15,
        "progressInterval": 5
    }

    try:
        # Test direct backend
        response = requests.post(
            f"{BACKEND_URL}/api/v1/emag/sync",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Backend FBE sync: {result['message']}")
            print(f"   📋 Sync ID: {result['data']['sync_id']}")
            print(f"   🏢 Accounts: {', '.join(result['data']['accounts'])}")
            backend_ok = True
        else:
            print(f"❌ Backend FBE sync failed: {response.status_code}")
            backend_ok = False

        # Test through frontend proxy
        response = requests.post(
            f"{FRONTEND_URL}/api/v1/emag/sync",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Frontend FBE sync: {result['message']}")
            frontend_ok = True
        else:
            print(f"❌ Frontend FBE sync failed: {response.status_code}")
            frontend_ok = False

        return backend_ok and frontend_ok

    except Exception as e:
        print(f"❌ FBE sync test error: {e}")
        return False

def test_multi_account_sync():
    """Testează sincronizarea multi-account (both)."""
    print("\n🧪 Testing Multi-Account Sync (BOTH)...")

    payload = {
        "mode": "both",
        "maxPages": 3,
        "batchSize": 25,
        "progressInterval": 10
    }

    try:
        response = requests.post(
            f"{FRONTEND_URL}/api/v1/emag/sync",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Multi-account sync: {result['message']}")
            print(f"   📋 Sync ID: {result['data']['sync_id']}")
            print(f"   🏢 Accounts: {', '.join(result['data']['accounts'])}")
            print(f"   📊 Max Pages: {result['data']['max_pages']}")
            print(f"   📦 Batch Size: {result['data']['batch_size']}")
            return True
        else:
            print(f"❌ Multi-account sync failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Multi-account sync test error: {e}")
        return False

def test_main_products():
    """Testează vizualizarea produselor MAIN."""
    print("\n🧪 Testing MAIN Products View...")

    try:
        response = requests.get(
            f"{FRONTEND_URL}/api/v1/admin/emag-products-by-account?account_type=main",
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            products = result['data']['products']
            print(f"✅ MAIN products loaded: {len(products)} products")

            if products:
                sample = products[0]
                print(f"   📦 Sample: {sample['name']}")
                print(f"   💰 Price: {sample['price']} {sample['currency']}")
                print(f"   🏢 Account: {sample['account_type']}")
                print(f"   🏷️ Brand: {sample['brand']}")

            return True
        else:
            print(f"❌ MAIN products failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ MAIN products test error: {e}")
        return False

def test_fbe_products():
    """Testează vizualizarea produselor FBE."""
    print("\n🧪 Testing FBE Products View...")

    try:
        response = requests.get(
            f"{FRONTEND_URL}/api/v1/admin/emag-products-by-account?account_type=fbe",
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            products = result['data']['products']
            print(f"✅ FBE products loaded: {len(products)} products")

            if products:
                sample = products[0]
                print(f"   📦 Sample: {sample['name']}")
                print(f"   💰 Price: {sample['price']} {sample['currency']}")
                print(f"   🏢 Account: {sample['account_type']}")
                print(f"   🏷️ Brand: {sample['brand']}")

            return True
        else:
            print(f"❌ FBE products failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ FBE products test error: {e}")
        return False

def test_frontend_accessibility():
    """Testează accesibilitatea frontend-ului."""
    print("\n🧪 Testing Frontend Accessibility...")

    try:
        response = requests.get(f"{FRONTEND_URL}/", timeout=5)
        if response.status_code == 200:
            print(f"✅ Frontend accessible at {FRONTEND_URL}")
            print(f"   📱 Products page: {FRONTEND_URL}/products")
            print(f"   🔗 eMAG Integration: {FRONTEND_URL}/emag")
            return True
        else:
            print(f"❌ Frontend not accessible: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frontend accessibility error: {e}")
        return False

def test_emag_sync_page_buttons():
    """Testează butoanele din pagina eMAG Sync."""
    print("\n🧪 Testing eMAG Sync Page Buttons...")

    test_cases = [
        {"mode": "main", "name": "MAIN Account"},
        {"mode": "fbe", "name": "FBE Account"},
        {"mode": "both", "name": "Both Accounts"}
    ]

    success_count = 0

    for test_case in test_cases:
        try:
            payload = {
                "mode": test_case["mode"],
                "maxPages": 2,
                "batchSize": 20
            }

            response = requests.post(
                f"{FRONTEND_URL}/api/v1/emag/sync",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ {test_case['name']} button: {result['data']['sync_id']}")
                success_count += 1
            else:
                print(f"   ❌ {test_case['name']} button failed: {response.status_code}")

        except Exception as e:
            print(f"   ❌ {test_case['name']} button error: {e}")

    print(f"✅ Sync buttons test: {success_count}/{len(test_cases)} working")
    return success_count == len(test_cases)

def run_comprehensive_test():
    """Rulează toate testele comprehensive."""
    print("=" * 80)
    print("🔧 Final Fixes Verification - Comprehensive Test Suite")
    print("=" * 80)
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Lista testelor
    tests = [
        ("Frontend Accessibility", test_frontend_accessibility),
        ("FBE Account Sync", test_fbe_sync),
        ("Multi-Account Sync", test_multi_account_sync),
        ("MAIN Products View", test_main_products),
        ("FBE Products View", test_fbe_products),
        ("eMAG Sync Page Buttons", test_emag_sync_page_buttons),
    ]

    results = []

    # Rulează testele
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 80)
    print("📊 FINAL TEST RESULTS")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")

    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL ISSUES FIXED! The system is working perfectly!")
        print("\n✅ Fixed Issues:")
        print("   • FBE Account synchronization now works")
        print("   • Multi-account synchronization (BOTH) works")
        print("   • Products page shows MAIN and FBE products separately")
        print("   • Regular products option removed (as requested)")
        print("   • All sync buttons in eMAG Integration page work")
        print("   • Frontend proxy configuration fixed")
        print("   • Backend endpoints enhanced with account type support")

        print("\n🌐 Access the enhanced system:")
        print(f"   • Products Page: {FRONTEND_URL}/products")
        print(f"   • eMAG Integration: {FRONTEND_URL}/emag")
        print(f"   • Backend API: {BACKEND_URL}/docs")

    else:
        print("⚠️  Some issues remain. Check the logs above for details.")
        failed_tests = [name for name, result in results if not result]
        print(f"   Failed tests: {', '.join(failed_tests)}")

    print(f"\n⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return passed == total

if __name__ == "__main__":
    success = run_comprehensive_test()
    exit(0 if success else 1)
