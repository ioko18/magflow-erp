#!/usr/bin/env python3
"""
Test script pentru noile funcționalități de sincronizare eMAG multi-account.
Demonstrează capabilitățile îmbunătățite ale sistemului.
"""

from datetime import datetime

import requests

# Configurare
BACKEND_URL = "http://localhost:8001"
FRONTEND_URL = "http://localhost:3001"

def test_sync_endpoint(mode: str, max_pages: int = 5, batch_size: int = 25):
    """Testează endpoint-ul de sincronizare îmbunătățit."""
    print(f"\n🧪 Testing {mode.upper()} sync mode...")

    payload = {
        "mode": mode,
        "maxPages": max_pages,
        "batchSize": batch_size,
        "progressInterval": 5
    }

    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/emag/sync",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ {mode.upper()} sync started successfully!")
            print(f"   📋 Sync ID: {result['data']['sync_id']}")
            print(f"   🏢 Accounts: {', '.join(result['data']['accounts'])}")
            print(f"   📊 Max Pages: {result['data']['max_pages']}")
            print(f"   📦 Batch Size: {result['data']['batch_size']}")
            print(f"   ⏰ Started: {result['data']['started_at']}")
            return result
        else:
            print(f"❌ {mode.upper()} sync failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None

    except Exception as e:
        print(f"❌ {mode.upper()} sync error: {e}")
        return None

def test_progress_endpoint():
    """Testează endpoint-ul de progres."""
    print("\n📊 Testing sync progress endpoint...")

    try:
        response = requests.get(
            f"{BACKEND_URL}/api/v1/admin/sync-progress",
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ Progress endpoint working!")
            print(f"   🏃 Running: {result['data']['isRunning']}")
            print(f"   📈 Processed: {result['data']['processedOffers']}")
            return result
        else:
            print(f"❌ Progress endpoint failed: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Progress endpoint error: {e}")
        return None

def test_export_endpoint(sync_id: str):
    """Testează endpoint-ul de export."""
    print(f"\n📤 Testing export endpoint for sync: {sync_id}")

    try:
        response = requests.get(
            f"{BACKEND_URL}/api/v1/admin/sync-export/{sync_id}",
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ Export endpoint working!")
            print(f"   📋 Sync ID: {result['data']['sync_id']}")
            print(f"   🏢 Account: {result['data']['account_type']}")
            print(f"   📊 Offers: {result['data']['total_offers_processed']}")
            print(f"   ⏱️ Duration: {result['data']['duration_seconds']}s")
            print(f"   📦 Products: {len(result['data']['products_synced'])}")
            return result
        else:
            print(f"❌ Export endpoint failed: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Export endpoint error: {e}")
        return None

def test_frontend_connectivity():
    """Testează conectivitatea frontend."""
    print("\n🌐 Testing frontend connectivity...")

    try:
        response = requests.get(f"{FRONTEND_URL}/", timeout=5)
        if response.status_code == 200:
            print(f"✅ Frontend accessible at {FRONTEND_URL}")
            print(f"   📱 eMAG Integration page: {FRONTEND_URL}/emag")
            return True
        else:
            print(f"❌ Frontend not accessible: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frontend connectivity error: {e}")
        return False

def run_comprehensive_test():
    """Rulează teste comprehensive pentru toate funcționalitățile."""
    print("=" * 80)
    print("🚀 eMAG Multi-Account Sync - Comprehensive Test Suite")
    print("=" * 80)
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test 1: Frontend connectivity
    frontend_ok = test_frontend_connectivity()

    # Test 2: Progress endpoint
    progress_ok = test_progress_endpoint()

    # Test 3: MAIN account sync
    main_result = test_sync_endpoint("main", max_pages=3, batch_size=20)

    # Test 4: FBE account sync
    fbe_result = test_sync_endpoint("fbe", max_pages=2, batch_size=15)

    # Test 5: Multi-account sync
    both_result = test_sync_endpoint("both", max_pages=5, batch_size=30)

    # Test 6: Export functionality
    export_ok = False
    if both_result and 'data' in both_result:
        sync_id = both_result['data']['sync_id']
        export_result = test_export_endpoint(sync_id)
        export_ok = export_result is not None

    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)

    tests = [
        ("Frontend Connectivity", frontend_ok),
        ("Progress Endpoint", progress_ok),
        ("MAIN Account Sync", main_result is not None),
        ("FBE Account Sync", fbe_result is not None),
        ("Multi-Account Sync", both_result is not None),
        ("Export Functionality", export_ok)
    ]

    passed = sum(1 for _, result in tests if result)
    total = len(tests)

    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")

    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! The enhanced eMAG integration is working perfectly!")
        print(f"\n🌐 Access the enhanced interface at: {FRONTEND_URL}/emag")
    else:
        print("⚠️  Some tests failed. Check the logs above for details.")

    print(f"\n⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def interactive_demo():
    """Demonstrație interactivă a funcționalităților."""
    print("\n" + "=" * 60)
    print("🎮 Interactive Demo Mode")
    print("=" * 60)

    while True:
        print("\nChoose an option:")
        print("1. Test MAIN account sync")
        print("2. Test FBE account sync")
        print("3. Test multi-account sync (BOTH)")
        print("4. Check sync progress")
        print("5. Export sync data")
        print("6. Run full test suite")
        print("0. Exit")

        choice = input("\nEnter your choice (0-6): ").strip()

        if choice == "0":
            print("👋 Goodbye!")
            break
        elif choice == "1":
            test_sync_endpoint("main")
        elif choice == "2":
            test_sync_endpoint("fbe")
        elif choice == "3":
            test_sync_endpoint("both")
        elif choice == "4":
            test_progress_endpoint()
        elif choice == "5":
            sync_id = input("Enter sync ID to export: ").strip()
            if sync_id:
                test_export_endpoint(sync_id)
            else:
                print("❌ Invalid sync ID")
        elif choice == "6":
            run_comprehensive_test()
        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_demo()
    else:
        run_comprehensive_test()
