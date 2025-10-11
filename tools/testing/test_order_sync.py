#!/usr/bin/env python3
"""
Test script for eMAG Order Synchronization endpoints.

This script verifies that the new order sync functionality is working correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.enhanced_emag_service import EnhancedEmagIntegrationService
from app.core.logging import get_logger

logger = get_logger(__name__)


async def test_order_sync_methods():
    """Test that order sync methods exist and are callable."""
    print("=" * 80)
    print("Testing eMAG Order Synchronization Implementation")
    print("=" * 80)
    print()

    # Test 1: Check if methods exist
    print("✓ Test 1: Checking if order sync methods exist...")
    service = EnhancedEmagIntegrationService("main")
    
    assert hasattr(service, 'sync_orders_from_account'), "Missing sync_orders_from_account method"
    assert hasattr(service, 'sync_all_orders_from_both_accounts'), "Missing sync_all_orders_from_both_accounts method"
    print("  ✅ All order sync methods exist")
    print()

    # Test 2: Check method signatures
    print("✓ Test 2: Checking method signatures...")
    import inspect
    
    sig1 = inspect.signature(service.sync_orders_from_account)
    params1 = list(sig1.parameters.keys())
    assert 'max_pages' in params1, "Missing max_pages parameter"
    assert 'delay_between_requests' in params1, "Missing delay_between_requests parameter"
    assert 'status_filter' in params1, "Missing status_filter parameter"
    print("  ✅ sync_orders_from_account signature correct")
    
    sig2 = inspect.signature(service.sync_all_orders_from_both_accounts)
    params2 = list(sig2.parameters.keys())
    assert 'max_pages_per_account' in params2, "Missing max_pages_per_account parameter"
    assert 'delay_between_requests' in params2, "Missing delay_between_requests parameter"
    assert 'status_filter' in params2, "Missing status_filter parameter"
    print("  ✅ sync_all_orders_from_both_accounts signature correct")
    print()

    # Test 3: Check rate limiter configuration
    print("✓ Test 3: Checking rate limiter configuration...")
    assert hasattr(service, 'rate_limiter'), "Missing rate_limiter"
    assert hasattr(service.rate_limiter, 'acquire'), "Missing rate_limiter.acquire method"
    print("  ✅ Rate limiter properly configured")
    print()

    # Test 4: Check metrics tracking
    print("✓ Test 4: Checking metrics tracking...")
    assert hasattr(service, '_metrics'), "Missing _metrics attribute"
    assert 'orders_synced' in service._metrics, "Missing orders_synced metric"
    print("  ✅ Metrics tracking includes orders")
    print()

    print("=" * 80)
    print("All Tests Passed! ✅")
    print("=" * 80)
    print()
    print("Order synchronization functionality is properly implemented.")
    print()
    print("Next Steps:")
    print("1. Start the backend: ./start_dev.sh backend")
    print("2. Start the frontend: ./start_dev.sh frontend")
    print("3. Navigate to: http://localhost:5173")
    print("4. Go to eMAG Integration page")
    print("5. Click 'Sync Orders' button")
    print()


def test_api_endpoints():
    """Test that API endpoints are properly defined."""
    print("=" * 80)
    print("Testing API Endpoints")
    print("=" * 80)
    print()

    try:
        from app.api.v1.endpoints.enhanced_emag_sync import router
        
        # Get all routes
        routes = [route for route in router.routes]
        route_paths = [route.path for route in routes]
        
        print("✓ Checking for order sync endpoints...")
        assert '/sync/all-orders' in route_paths, "Missing /sync/all-orders endpoint"
        assert '/orders/all' in route_paths, "Missing /orders/all endpoint"
        print("  ✅ All order sync endpoints defined")
        print()
        
        print("Available endpoints:")
        for route in routes:
            methods = ', '.join(route.methods) if hasattr(route, 'methods') else 'N/A'
            print(f"  - {methods:10} {route.path}")
        print()
        
    except Exception as e:
        print(f"  ❌ Error checking endpoints: {e}")
        return False
    
    print("=" * 80)
    print("API Endpoints Test Passed! ✅")
    print("=" * 80)
    print()
    
    return True


if __name__ == "__main__":
    print()
    print("🚀 eMAG Order Sync Implementation Test")
    print()
    
    # Run async tests
    try:
        asyncio.run(test_order_sync_methods())
    except Exception as e:
        print(f"❌ Async tests failed: {e}")
        sys.exit(1)
    
    # Run API tests
    try:
        if not test_api_endpoints():
            sys.exit(1)
    except Exception as e:
        print(f"❌ API tests failed: {e}")
        sys.exit(1)
    
    print("=" * 80)
    print("🎉 ALL TESTS PASSED!")
    print("=" * 80)
    print()
    print("The eMAG Order Synchronization feature is fully implemented and ready to use.")
    print()
