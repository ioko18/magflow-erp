#!/usr/bin/env python3
"""
Complete Integration Test for eMAG Enhancements.

Tests all new endpoints and services to verify complete integration.
"""

import asyncio
import sys
import requests
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"
LOGIN_EMAIL = "admin@example.com"
LOGIN_PASSWORD = "secret"


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(test_name, success, details=""):
    """Print test result."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"    {details}")


def get_auth_token():
    """Get JWT authentication token."""
    print_section("Authentication")
    
    try:
        response = requests.post(
            f"{API_BASE}/auth/login",
            json={"username": LOGIN_EMAIL, "password": LOGIN_PASSWORD},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print_result("Login", True, f"Token obtained")
            return token
        else:
            print_result("Login", False, f"Status: {response.status_code}")
            return None
    except Exception as e:
        print_result("Login", False, f"Error: {e}")
        return None


def test_health_endpoint(token):
    """Test health endpoint."""
    print_section("Health Check Endpoint")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(
            f"{API_BASE}/emag/management/health",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "unknown")
            health_score = data.get("health_score", 0)
            print_result(
                "Health Endpoint",
                True,
                f"Status: {status}, Score: {health_score}"
            )
            return True
        else:
            print_result("Health Endpoint", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        print_result("Health Endpoint", False, f"Error: {e}")
        return False


def test_monitoring_endpoints(token):
    """Test monitoring endpoints."""
    print_section("Monitoring Endpoints")
    
    headers = {"Authorization": f"Bearer {token}"}
    results = []
    
    endpoints = [
        ("/emag/management/monitoring/metrics", "Metrics"),
        ("/emag/management/monitoring/sync-stats", "Sync Stats"),
        ("/emag/management/monitoring/product-stats", "Product Stats"),
    ]
    
    for endpoint, name in endpoints:
        try:
            response = requests.get(
                f"{API_BASE}{endpoint}",
                headers=headers,
                timeout=10
            )
            
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                if isinstance(data, dict):
                    details += f", Keys: {len(data)}"
            
            print_result(name, success, details)
            results.append(success)
        except Exception as e:
            print_result(name, False, f"Error: {e}")
            results.append(False)
    
    return all(results)


def test_rate_limiter_endpoints(token):
    """Test rate limiter endpoints."""
    print_section("Rate Limiter Endpoints")
    
    headers = {"Authorization": f"Bearer {token}"}
    results = []
    
    # Test stats endpoint
    try:
        response = requests.get(
            f"{API_BASE}/emag/management/rate-limiter/stats",
            headers=headers,
            timeout=10
        )
        
        success = response.status_code == 200
        details = f"Status: {response.status_code}"
        if success:
            data = response.json()
            orders_requests = data.get("orders_requests", 0)
            details += f", Orders: {orders_requests}"
        
        print_result("Rate Limiter Stats", success, details)
        results.append(success)
    except Exception as e:
        print_result("Rate Limiter Stats", False, f"Error: {e}")
        results.append(False)
    
    # Test reset endpoint
    try:
        response = requests.post(
            f"{API_BASE}/emag/management/rate-limiter/reset",
            headers=headers,
            timeout=10
        )
        
        success = response.status_code == 200
        print_result("Rate Limiter Reset", success, f"Status: {response.status_code}")
        results.append(success)
    except Exception as e:
        print_result("Rate Limiter Reset", False, f"Error: {e}")
        results.append(False)
    
    return all(results)


def test_backup_endpoints(token):
    """Test backup endpoints."""
    print_section("Backup Endpoints")
    
    headers = {"Authorization": f"Bearer {token}"}
    results = []
    
    # Test list backups
    try:
        response = requests.get(
            f"{API_BASE}/emag/management/backup/list",
            headers=headers,
            timeout=10
        )
        
        success = response.status_code == 200
        details = f"Status: {response.status_code}"
        if success:
            data = response.json()
            details += f", Backups: {len(data)}"
        
        print_result("List Backups", success, details)
        results.append(success)
    except Exception as e:
        print_result("List Backups", False, f"Error: {e}")
        results.append(False)
    
    # Test create backup (small backup for testing)
    try:
        response = requests.post(
            f"{API_BASE}/emag/management/backup/create",
            headers=headers,
            params={
                "include_products": False,
                "include_offers": False,
                "include_orders": False,
                "include_sync_logs": True,
                "compress": True,
            },
            timeout=30
        )
        
        success = response.status_code == 200
        details = f"Status: {response.status_code}"
        if success:
            data = response.json()
            if data.get("success"):
                size_mb = data.get("file_size_bytes", 0) / 1024 / 1024
                details += f", Size: {size_mb:.2f} MB"
        
        print_result("Create Backup", success, details)
        results.append(success)
    except Exception as e:
        print_result("Create Backup", False, f"Error: {e}")
        results.append(False)
    
    return all(results)


def test_existing_endpoints(token):
    """Test that existing endpoints still work."""
    print_section("Existing Endpoints (Regression Test)")
    
    headers = {"Authorization": f"Bearer {token}"}
    results = []
    
    endpoints = [
        ("/health", "Health"),
        ("/emag/enhanced/status", "eMAG Status"),
        ("/emag/enhanced/products/all", "Products List"),
    ]
    
    for endpoint, name in endpoints:
        try:
            response = requests.get(
                f"{API_BASE}{endpoint}",
                headers=headers,
                timeout=10
            )
            
            success = response.status_code == 200
            print_result(name, success, f"Status: {response.status_code}")
            results.append(success)
        except Exception as e:
            print_result(name, False, f"Error: {e}")
            results.append(False)
    
    return all(results)


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("  eMAG Integration - Complete Integration Test")
    print("=" * 60)
    print(f"\nTesting against: {BASE_URL}")
    print(f"API Base: {API_BASE}")
    
    # Get authentication token
    token = get_auth_token()
    if not token:
        print("\n❌ FAILED: Could not authenticate")
        print("Please ensure the backend is running and credentials are correct.")
        return 1
    
    # Run all tests
    test_results = {
        "Health Endpoint": test_health_endpoint(token),
        "Monitoring Endpoints": test_monitoring_endpoints(token),
        "Rate Limiter Endpoints": test_rate_limiter_endpoints(token),
        "Backup Endpoints": test_backup_endpoints(token),
        "Existing Endpoints": test_existing_endpoints(token),
    }
    
    # Summary
    print_section("Test Summary")
    
    passed = sum(1 for result in test_results.values() if result)
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} test groups passed")
    
    if passed == total:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("The eMAG integration enhancements are fully integrated and working.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test group(s) failed.")
        print("Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
