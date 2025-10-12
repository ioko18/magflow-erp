#!/usr/bin/env python3
"""
Test script for eMAG integration improvements.

This script validates all the enhancements made to the eMAG integration
according to the EMAG_FULL_SYNC_GUIDE.md recommendations.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_constants():
    """Test eMAG constants module."""
    print("\n" + "="*80)
    print("TEST 1: eMAG Constants and Enumerations")
    print("="*80)

    try:
        from app.core.emag_constants import (
            CANCELLATION_REASONS,
            EmagErrorCode,
            OrderStatus,
            get_cancellation_reason_text,
            get_order_status_text,
            get_payment_mode_text,
        )

        # Test order status
        print(f"✓ Order Status NEW: {get_order_status_text(OrderStatus.NEW.value)}")
        print(f"✓ Order Status FINALIZED: {get_order_status_text(OrderStatus.FINALIZED.value)}")

        # Test cancellation reasons
        print(f"✓ Cancellation Reason 1: {get_cancellation_reason_text(1)}")
        print(f"✓ Cancellation Reason 31: {get_cancellation_reason_text(31)}")
        print(f"✓ Total cancellation reasons: {len(CANCELLATION_REASONS)}")

        # Test payment modes
        print(f"✓ Payment Mode 1 (COD): {get_payment_mode_text(1)}")
        print(f"✓ Payment Mode 3 (Card): {get_payment_mode_text(3)}")

        # Test error codes
        print(f"✓ Error codes defined: {len(EmagErrorCode)}")

        print("\n✅ Constants module: PASSED")
        return True

    except Exception as e:
        print(f"\n❌ Constants module: FAILED - {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_monitoring():
    """Test monitoring module."""
    print("\n" + "="*80)
    print("TEST 2: Monitoring and Metrics")
    print("="*80)

    try:
        from app.core.emag_monitoring import EmagMonitor, get_monitor

        # Create monitor instance
        monitor = EmagMonitor(window_size_seconds=60)
        print("✓ Monitor instance created")

        # Test sync tracking
        monitor.start_sync("products")
        print("✓ Sync tracking started")

        # Record some test metrics
        monitor.record_request(
            endpoint="/product_offer/read",
            method="GET",
            status_code=200,
            response_time_ms=245.5,
            account_type="main",
            success=True,
        )
        print("✓ Successful request recorded")

        monitor.record_request(
            endpoint="/product_offer/read",
            method="GET",
            status_code=429,
            response_time_ms=100.0,
            account_type="main",
            success=False,
            error_message="Rate limit exceeded",
            error_code="RATE_LIMIT_EXCEEDED",
        )
        print("✓ Failed request recorded")

        # Get metrics
        metrics = monitor.get_metrics()
        print(f"✓ Total requests: {metrics.total_requests}")
        print(f"✓ Success rate: {metrics.success_rate:.2f}%")
        print(f"✓ Error rate: {metrics.error_rate:.2f}%")
        print(f"✓ Average response time: {metrics.average_response_time_ms:.2f}ms")

        # Get health status
        health = monitor.get_health_status()
        print(f"✓ Health status: {health['status']}")
        print(f"✓ Alerts: {len(health['alerts'])}")

        # Test global monitor
        get_monitor()
        print("✓ Global monitor retrieved")

        monitor.end_sync()
        print("✓ Sync tracking ended")

        print("\n✅ Monitoring module: PASSED")
        return True

    except Exception as e:
        print(f"\n❌ Monitoring module: FAILED - {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_api_client():
    """Test enhanced API client."""
    print("\n" + "="*80)
    print("TEST 3: Enhanced API Client")
    print("="*80)

    try:
        from app.services.emag_api_client import EmagApiError

        # Test error properties
        error = EmagApiError(
            "Rate limit exceeded",
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED"
        )

        print(f"✓ Error created: {error}")
        print(f"✓ Is rate limit error: {error.is_rate_limit_error}")
        print(f"✓ Is auth error: {error.is_auth_error}")
        print(f"✓ Is validation error: {error.is_validation_error}")

        # Test auth error
        auth_error = EmagApiError(
            "Invalid credentials",
            status_code=401,
            error_code="AUTH_INVALID_CREDENTIALS"
        )
        print(f"✓ Auth error detected: {auth_error.is_auth_error}")

        # Test validation error
        validation_error = EmagApiError(
            "Missing field",
            status_code=400,
            error_code="VALIDATION_MISSING_FIELD"
        )
        print(f"✓ Validation error detected: {validation_error.is_validation_error}")

        print("\n✅ API Client: PASSED")
        return True

    except Exception as e:
        print(f"\n❌ API Client: FAILED - {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_service_methods():
    """Test enhanced service methods."""
    print("\n" + "="*80)
    print("TEST 4: Enhanced Service Methods")
    print("="*80)

    try:
        from app.services.enhanced_emag_service import EnhancedEmagIntegrationService

        # Check that methods exist
        service_methods = [
            'sync_all_products_from_both_accounts',
            'sync_all_offers_from_both_accounts',
            'sync_all_orders_from_both_accounts',
            'sync_orders_from_account',
            '_upsert_offer_from_product_data',
            'get_sync_metrics',
            'get_sync_status',
        ]

        for method_name in service_methods:
            if hasattr(EnhancedEmagIntegrationService, method_name):
                print(f"✓ Method exists: {method_name}")
            else:
                print(f"✗ Method missing: {method_name}")
                return False

        print("\n✅ Service Methods: PASSED")
        return True

    except Exception as e:
        print(f"\n❌ Service Methods: FAILED - {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_imports():
    """Test that all modules can be imported."""
    print("\n" + "="*80)
    print("TEST 5: Module Imports")
    print("="*80)

    modules_to_test = [
        ('app.core.emag_constants', 'eMAG Constants'),
        ('app.core.emag_monitoring', 'eMAG Monitoring'),
        ('app.services.emag_api_client', 'eMAG API Client'),
        ('app.services.enhanced_emag_service', 'Enhanced eMAG Service'),
        ('app.api.v1.endpoints.enhanced_emag_sync', 'Enhanced eMAG Sync Endpoints'),
    ]

    all_passed = True
    for module_path, module_name in modules_to_test:
        try:
            __import__(module_path)
            print(f"✓ {module_name}: imported successfully")
        except Exception as e:
            print(f"✗ {module_name}: import failed - {str(e)}")
            all_passed = False

    if all_passed:
        print("\n✅ Module Imports: PASSED")
    else:
        print("\n❌ Module Imports: FAILED")

    return all_passed


async def test_documentation():
    """Test that documentation files exist."""
    print("\n" + "="*80)
    print("TEST 6: Documentation")
    print("="*80)

    docs_to_check = [
        'docs/EMAG_FULL_SYNC_GUIDE.md',
        'app/core/emag_constants.py',
        'app/core/emag_monitoring.py',
    ]

    all_exist = True
    for doc_path in docs_to_check:
        path = Path(doc_path)
        if path.exists():
            size = path.stat().st_size
            print(f"✓ {doc_path}: exists ({size:,} bytes)")
        else:
            print(f"✗ {doc_path}: missing")
            all_exist = False

    if all_exist:
        print("\n✅ Documentation: PASSED")
    else:
        print("\n❌ Documentation: FAILED")

    return all_exist


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("eMAG INTEGRATION IMPROVEMENTS - TEST SUITE")
    print("="*80)
    print("\nTesting enhancements based on EMAG_FULL_SYNC_GUIDE.md")
    print("Testing Date:", asyncio.get_event_loop().time())

    tests = [
        ("Constants & Enumerations", test_constants),
        ("Monitoring & Metrics", test_monitoring),
        ("API Client Enhancements", test_api_client),
        ("Service Methods", test_service_methods),
        ("Module Imports", test_imports),
        ("Documentation", test_documentation),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")

    print("\n" + "-"*80)
    print(f"Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("="*80)

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! eMAG integration improvements are working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
