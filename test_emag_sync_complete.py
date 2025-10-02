#!/usr/bin/env python3
"""
Comprehensive eMAG Synchronization Test Script
Tests all aspects of the eMAG integration after Section 8 fixes
"""

import requests
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
LOGIN_EMAIL = "admin@example.com"
LOGIN_PASSWORD = "secret"

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def test_authentication():
    """Test JWT authentication"""
    print_section("1. Testing Authentication")
    
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": LOGIN_EMAIL, "password": LOGIN_PASSWORD}
    )
    
    if response.status_code == 200:
        token = response.json().get("access_token")
        print("✅ Authentication successful")
        print(f"   Token: {token[:50]}...")
        return token
    else:
        print(f"❌ Authentication failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

def test_health_check():
    """Test backend health"""
    print_section("2. Testing Backend Health")
    
    response = requests.get(f"{BASE_URL}/health")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Backend is healthy")
        print(f"   Status: {data.get('status')}")
        print(f"   Timestamp: {data.get('timestamp')}")
        return True
    else:
        print(f"❌ Health check failed: {response.status_code}")
        return False

def test_emag_status(token):
    """Test eMAG integration status"""
    print_section("3. Testing eMAG Integration Status")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/api/v1/emag/enhanced/status",
        headers=headers,
        params={"account_type": "both"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✅ eMAG status retrieved successfully")
        print(f"   Health Score: {data.get('health_score')}%")
        print(f"   Health Status: {data.get('health_status')}")
        
        if "main_account" in data:
            main = data["main_account"]
            print("\n   MAIN Account:")
            print(f"     - Status: {main.get('status')}")
            print(f"     - Products: {main.get('products', {}).get('total', 0)}")
            print(f"     - Active: {main.get('products', {}).get('active', 0)}")
            print(f"     - Synced: {main.get('products', {}).get('synced', 0)}")
        
        if "fbe_account" in data:
            fbe = data["fbe_account"]
            print("\n   FBE Account:")
            print(f"     - Status: {fbe.get('status')}")
            print(f"     - Products: {fbe.get('products', {}).get('total', 0)}")
            print(f"     - Active: {fbe.get('products', {}).get('active', 0)}")
            print(f"     - Synced: {fbe.get('products', {}).get('synced', 0)}")
        
        if "summary" in data:
            summary = data["summary"]
            print("\n   Summary:")
            print(f"     - Total Products: {summary.get('total_products', 0)}")
            print(f"     - Active Products: {summary.get('active_products', 0)}")
            print(f"     - Total Stock: {summary.get('total_stock', 0)}")
        
        return True
    else:
        print(f"❌ Status check failed: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return False

def test_product_sync(token):
    """Test product synchronization"""
    print_section("4. Testing Product Synchronization")
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "max_pages_per_account": 1,
        "delay_between_requests": 1.5,
        "include_inactive": True
    }
    
    print("   Starting sync (1 page per account)...")
    response = requests.post(
        f"{BASE_URL}/api/v1/emag/enhanced/sync/all-products",
        headers=headers,
        json=payload
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Synchronization completed successfully")
        print(f"   Total Products Processed: {data.get('total_products_processed', 0)}")
        
        if "main_account" in data and data["main_account"]:
            main = data["main_account"]
            print("\n   MAIN Account:")
            print(f"     - Products: {main.get('products_count', 0)}")
            print(f"     - Pages: {main.get('pages_processed', 0)}")
            print(f"     - Duration: {main.get('duration_seconds', 0):.2f}s")
        
        if "fbe_account" in data and data["fbe_account"]:
            fbe = data["fbe_account"]
            print("\n   FBE Account:")
            print(f"     - Products: {fbe.get('products_count', 0)}")
            print(f"     - Pages: {fbe.get('pages_processed', 0)}")
            print(f"     - Duration: {fbe.get('duration_seconds', 0):.2f}s")
        
        if "combined" in data and data["combined"]:
            combined = data["combined"]
            errors = combined.get("errors", [])
            print("\n   Combined Results:")
            print(f"     - Errors: {len(errors)}")
            
            if errors:
                print("\n   ⚠️  Errors found:")
                for error in errors[:5]:  # Show first 5 errors
                    print(f"     - SKU {error.get('sku')}: {error.get('error', '')[:100]}")
        
        return len(errors) == 0 if "combined" in data else True
    else:
        print(f"❌ Synchronization failed: {response.status_code}")
        print(f"   Response: {response.text[:500]}")
        return False

def test_products_list(token):
    """Test product listing"""
    print_section("5. Testing Product Listing")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/api/v1/emag/enhanced/products/all",
        headers=headers,
        params={"account_type": "both", "max_pages_per_account": 1}
    )
    
    if response.status_code == 200:
        data = response.json()
        products = data.get("products", [])
        print("✅ Products retrieved successfully")
        print(f"   Total Products: {data.get('total_count', 0)}")
        
        if products:
            # Sample product info
            sample = products[0]
            
            print(f"\n   Sample Product (SKU: {sample.get('sku')}):")
            print(f"     - Name: {sample.get('name', '')[:50]}")
            print(f"     - Account: {sample.get('account_type')}")
            print(f"     - Price: {sample.get('price')} {sample.get('currency')}")
            print(f"     - Stock: {sample.get('stock_quantity')}")
            
            # Note: Section 8 fields might not be in the API response
            # They are stored in database but may not be exposed in this endpoint
        
        return True
    else:
        print(f"❌ Product listing failed: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return False

def test_database_section8_fields():
    """Test Section 8 fields in database"""
    print_section("6. Testing Section 8 Fields in Database")
    
    import subprocess
    
    query = """
    SELECT 
        COUNT(*) as total_products,
        COUNT(genius_eligibility) as with_genius,
        COUNT(part_number_key) as with_pnk,
        COUNT(family_id) as with_family,
        COUNT(url) as with_url,
        COUNT(warranty) as with_warranty
    FROM app.emag_products_v2;
    """
    
    try:
        result = subprocess.run(
            [
                "docker", "exec", "magflow_db",
                "psql", "-U", "app", "-d", "magflow",
                "-c", query, "-t"
            ],
            capture_output=True,
            text=True,
            check=True
        )
        
        output = result.stdout.strip()
        if output:
            values = [int(x.strip()) for x in output.split('|')]
            total, genius, pnk, family, url, warranty = values
            
            print("✅ Section 8 fields verified in database")
            print(f"   Total Products: {total}")
            print(f"   With Genius Eligibility: {genius} ({genius/total*100:.1f}%)")
            print(f"   With Part Number Key: {pnk} ({pnk/total*100:.1f}%)")
            print(f"   With Family ID: {family} ({family/total*100:.1f}%)")
            print(f"   With URL: {url} ({url/total*100:.1f}%)")
            print(f"   With Warranty: {warranty} ({warranty/total*100:.1f}%)")
            
            return True
        else:
            print("❌ No data returned from database")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Database query failed: {e}")
        print(f"   Error: {e.stderr}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("  eMAG INTEGRATION COMPREHENSIVE TEST SUITE")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*80)
    
    results = {}
    
    # Test 1: Authentication
    token = test_authentication()
    results["authentication"] = token is not None
    
    if not token:
        print("\n❌ Cannot proceed without authentication")
        return
    
    # Test 2: Health Check
    results["health_check"] = test_health_check()
    
    # Test 3: eMAG Status
    results["emag_status"] = test_emag_status(token)
    
    # Test 4: Product Sync
    results["product_sync"] = test_product_sync(token)
    
    # Test 5: Products List
    results["products_list"] = test_products_list(token)
    
    # Test 6: Database Section 8 Fields
    results["section8_fields"] = test_database_section8_fields()
    
    # Summary
    print_section("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"   {status}  {test_name.replace('_', ' ').title()}")
    
    print(f"\n   Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n   🎉 ALL TESTS PASSED! eMAG integration is working perfectly!")
    else:
        print(f"\n   ⚠️  {total - passed} test(s) failed. Please review the errors above.")
    
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
