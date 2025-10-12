#!/usr/bin/env python3
"""
Test script for eMAG Integration Phase 1 Implementation.

This script verifies all new implementations including:
- Order Management Service
- Enhanced API Client methods
- API Endpoints
- Database models
"""

import asyncio
import sys
from datetime import datetime
from typing import Any

# Add parent directory to path
sys.path.insert(0, '/Users/macos/anaconda3/envs/MagFlow')

from app.services.emag_api_client import EmagApiClient
from app.services.emag_order_service import EmagOrderService

from app.config.emag_config import get_emag_config
from app.core.database import async_session_factory


class Phase1Tester:
    """Test all Phase 1 implementations."""

    def __init__(self):
        self.results = {
            "api_client": {},
            "order_service": {},
            "database": {},
            "overall": "pending"
        }
        self.config_main = get_emag_config("main")
        self.config_fbe = get_emag_config("fbe")

    async def test_api_client_methods(self) -> dict[str, Any]:
        """Test new API client methods."""
        print("\n" + "="*80)
        print("TESTING: eMAG API Client Methods")
        print("="*80)

        results = {}

        try:
            async with EmagApiClient(
                username=self.config_main.api_username,
                password=self.config_main.api_password,
                base_url=self.config_main.base_url
            ) as client:

                # Test 1: Light Offer API method exists
                print("\n✓ Testing: update_offer_light method...")
                assert hasattr(client, 'update_offer_light'), "Method update_offer_light not found"
                results['update_offer_light'] = "✅ EXISTS"
                print("  ✅ Method exists")

                # Test 2: Stock PATCH method exists
                print("\n✓ Testing: update_stock_only method...")
                assert hasattr(client, 'update_stock_only'), "Method update_stock_only not found"
                results['update_stock_only'] = "✅ EXISTS"
                print("  ✅ Method exists")

                # Test 3: Order management methods
                order_methods = [
                    'get_order_by_id',
                    'acknowledge_order',
                    'save_order',
                    'attach_invoice',
                    'attach_warranty'
                ]
                print("\n✓ Testing: Order management methods...")
                for method in order_methods:
                    assert hasattr(client, method), f"Method {method} not found"
                    results[method] = "✅ EXISTS"
                    print(f"  ✅ {method}")

                # Test 4: AWB management methods
                awb_methods = ['create_awb', 'get_awb', 'get_courier_accounts']
                print("\n✓ Testing: AWB management methods...")
                for method in awb_methods:
                    assert hasattr(client, method), f"Method {method} not found"
                    results[method] = "✅ EXISTS"
                    print(f"  ✅ {method}")

                # Test 5: Campaign methods
                campaign_methods = ['propose_to_campaign', 'check_smart_deals_eligibility']
                print("\n✓ Testing: Campaign management methods...")
                for method in campaign_methods:
                    assert hasattr(client, method), f"Method {method} not found"
                    results[method] = "✅ EXISTS"
                    print(f"  ✅ {method}")

                # Test 6: Commission methods
                commission_methods = ['get_commission_estimate', 'search_product_by_ean']
                print("\n✓ Testing: Commission calculator methods...")
                for method in commission_methods:
                    assert hasattr(client, method), f"Method {method} not found"
                    results[method] = "✅ EXISTS"
                    print(f"  ✅ {method}")

                # Test 7: RMA methods
                rma_methods = ['get_rma_requests', 'save_rma']
                print("\n✓ Testing: RMA management methods...")
                for method in rma_methods:
                    assert hasattr(client, method), f"Method {method} not found"
                    results[method] = "✅ EXISTS"
                    print(f"  ✅ {method}")

                # Test 8: EAN matching
                print("\n✓ Testing: find_products_by_eans method...")
                assert hasattr(client, 'find_products_by_eans'), "Method find_products_by_eans not found"
                results['find_products_by_eans'] = "✅ EXISTS"
                print("  ✅ Method exists")

                print("\n" + "="*80)
                print(f"API CLIENT TESTS: ✅ ALL PASSED ({len(results)} methods verified)")
                print("="*80)

                return {"status": "success", "methods_tested": len(results), "details": results}

        except Exception as e:
            print(f"\n❌ API Client test failed: {str(e)}")
            return {"status": "failed", "error": str(e), "details": results}

    async def test_order_service(self) -> dict[str, Any]:
        """Test Order Service implementation."""
        print("\n" + "="*80)
        print("TESTING: Order Management Service")
        print("="*80)

        results = {}

        try:
            async with async_session_factory() as session:
                # Test service initialization
                print("\n✓ Testing: Service initialization...")
                service = EmagOrderService("main", session)
                await service.initialize()
                results['initialization'] = "✅ SUCCESS"
                print("  ✅ Service initialized")

                # Test methods exist
                methods = [
                    'sync_new_orders',
                    'acknowledge_order',
                    'update_order_status',
                    'attach_invoice',
                    'get_metrics'
                ]

                print("\n✓ Testing: Service methods...")
                for method in methods:
                    assert hasattr(service, method), f"Method {method} not found"
                    results[method] = "✅ EXISTS"
                    print(f"  ✅ {method}")

                # Test metrics
                print("\n✓ Testing: Metrics tracking...")
                metrics = service.get_metrics()
                assert 'account_type' in metrics, "Metrics missing account_type"
                assert 'metrics' in metrics, "Metrics missing metrics dict"
                results['metrics'] = "✅ WORKING"
                print(f"  ✅ Metrics: {metrics}")

                await service.close()

                print("\n" + "="*80)
                print(f"ORDER SERVICE TESTS: ✅ ALL PASSED ({len(results)} checks)")
                print("="*80)

                return {"status": "success", "checks": len(results), "details": results}

        except Exception as e:
            print(f"\n❌ Order Service test failed: {str(e)}")
            return {"status": "failed", "error": str(e), "details": results}

    async def test_database_models(self) -> dict[str, Any]:
        """Test database models."""
        print("\n" + "="*80)
        print("TESTING: Database Models")
        print("="*80)

        results = {}

        try:
            from app.models.emag_models import EmagOrder

            # Test model exists
            print("\n✓ Testing: EmagOrder model...")
            results['model_exists'] = "✅ EXISTS"
            print("  ✅ Model imported successfully")

            # Test required fields
            required_fields = [
                'id', 'emag_order_id', 'account_type', 'status', 'status_name',
                'customer_name', 'customer_email', 'total_amount', 'payment_method',
                'awb_number', 'invoice_url', 'acknowledged_at', 'finalized_at'
            ]

            print("\n✓ Testing: Model fields...")
            for field in required_fields:
                assert hasattr(EmagOrder, field), f"Field {field} not found"
                results[f'field_{field}'] = "✅ EXISTS"
            print(f"  ✅ All {len(required_fields)} required fields present")

            # Test table name
            print("\n✓ Testing: Table configuration...")
            assert EmagOrder.__tablename__ == 'emag_orders', "Wrong table name"
            results['table_name'] = "✅ CORRECT"
            print("  ✅ Table name: emag_orders")

            print("\n" + "="*80)
            print(f"DATABASE MODEL TESTS: ✅ ALL PASSED ({len(results)} checks)")
            print("="*80)

            return {"status": "success", "checks": len(results), "details": results}

        except Exception as e:
            print(f"\n❌ Database model test failed: {str(e)}")
            return {"status": "failed", "error": str(e), "details": results}

    async def test_api_endpoints(self) -> dict[str, Any]:
        """Test API endpoints registration."""
        print("\n" + "="*80)
        print("TESTING: API Endpoints Registration")
        print("="*80)

        results = {}

        try:
            # Test endpoint module exists
            print("\n✓ Testing: Endpoint module...")
            from app.api.v1.endpoints import emag_orders
            results['module_exists'] = "✅ EXISTS"
            print("  ✅ emag_orders module imported")

            # Test router exists
            print("\n✓ Testing: Router...")
            assert hasattr(emag_orders, 'router'), "Router not found"
            results['router_exists'] = "✅ EXISTS"
            print("  ✅ Router defined")

            # Test router is registered
            print("\n✓ Testing: Router registration...")
            from app.api.v1.api import api_router

            # Check if routes are registered
            routes = [route.path for route in api_router.routes]
            order_routes = [r for r in routes if '/emag/orders' in r]

            assert len(order_routes) > 0, "No order routes registered"
            results['routes_registered'] = f"✅ {len(order_routes)} ROUTES"
            print(f"  ✅ {len(order_routes)} order routes registered")

            for route in order_routes:
                print(f"    - {route}")

            print("\n" + "="*80)
            print(f"API ENDPOINT TESTS: ✅ ALL PASSED ({len(results)} checks)")
            print("="*80)

            return {"status": "success", "checks": len(results), "details": results}

        except Exception as e:
            print(f"\n❌ API endpoint test failed: {str(e)}")
            return {"status": "failed", "error": str(e), "details": results}

    async def run_all_tests(self):
        """Run all tests."""
        print("\n" + "="*80)
        print("eMAG INTEGRATION PHASE 1 - IMPLEMENTATION VERIFICATION")
        print("="*80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Run tests
        self.results['api_client'] = await self.test_api_client_methods()
        self.results['order_service'] = await self.test_order_service()
        self.results['database'] = await self.test_database_models()
        self.results['api_endpoints'] = await self.test_api_endpoints()

        # Calculate overall result
        all_passed = all(
            result.get('status') == 'success'
            for result in self.results.values()
            if isinstance(result, dict)
        )

        self.results['overall'] = "success" if all_passed else "failed"

        # Print summary
        print("\n" + "="*80)
        print("FINAL SUMMARY")
        print("="*80)

        print("\n📊 Test Results:")
        for category, result in self.results.items():
            if category != 'overall' and isinstance(result, dict):
                status = result.get('status', 'unknown')
                icon = "✅" if status == "success" else "❌"
                print(f"  {icon} {category.upper()}: {status}")
                if status == "success":
                    if 'methods_tested' in result:
                        print(f"     → {result['methods_tested']} methods verified")
                    elif 'checks' in result:
                        print(f"     → {result['checks']} checks passed")

        print("\n" + "="*80)
        if all_passed:
            print("✅ ALL TESTS PASSED - PHASE 1 IMPLEMENTATION VERIFIED!")
        else:
            print("❌ SOME TESTS FAILED - REVIEW ERRORS ABOVE")
        print("="*80)
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return self.results


async def main():
    """Main test runner."""
    tester = Phase1Tester()
    results = await tester.run_all_tests()

    # Exit with appropriate code
    exit_code = 0 if results['overall'] == 'success' else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
