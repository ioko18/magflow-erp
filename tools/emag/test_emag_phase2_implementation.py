#!/usr/bin/env python3
"""
Test script for eMAG Integration Phase 2 Implementation.

This script verifies all Phase 2 implementations including:
- AWB Management Service
- EAN Product Matching Service
- Invoice Generation Service
- API Endpoints
"""

import asyncio
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, '/Users/macos/anaconda3/envs/MagFlow')

from app.services.emag_awb_service import EmagAWBService
from app.services.emag_ean_matching_service import EmagEANMatchingService
from app.services.emag_invoice_service import EmagInvoiceService
from app.config.emag_config import get_emag_config


class Phase2Tester:
    """Test all Phase 2 implementations."""
    
    def __init__(self):
        self.results = {
            "awb_service": {},
            "ean_service": {},
            "invoice_service": {},
            "api_endpoints": {},
            "overall": "pending"
        }
        self.config_main = get_emag_config("main")
    
    async def test_awb_service(self):
        """Test AWB Management Service."""
        print("\n" + "="*80)
        print("TESTING: AWB Management Service")
        print("="*80)
        
        results = {}
        
        try:
            # Test service initialization
            print("\n✓ Testing: Service initialization...")
            service = EmagAWBService("main")
            await service.initialize()
            results['initialization'] = "✅ SUCCESS"
            print("  ✅ Service initialized")
            
            # Test methods exist
            methods = [
                'get_courier_accounts',
                'generate_awb',
                'get_awb_details',
                'bulk_generate_awbs',
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
            print(f"AWB SERVICE TESTS: ✅ ALL PASSED ({len(results)} checks)")
            print("="*80)
            
            return {"status": "success", "checks": len(results), "details": results}
            
        except Exception as e:
            print(f"\n❌ AWB Service test failed: {str(e)}")
            return {"status": "failed", "error": str(e), "details": results}
    
    async def test_ean_service(self):
        """Test EAN Product Matching Service."""
        print("\n" + "="*80)
        print("TESTING: EAN Product Matching Service")
        print("="*80)
        
        results = {}
        
        try:
            # Test service initialization
            print("\n✓ Testing: Service initialization...")
            service = EmagEANMatchingService("main")
            await service.initialize()
            results['initialization'] = "✅ SUCCESS"
            print("  ✅ Service initialized")
            
            # Test methods exist
            methods = [
                'find_products_by_ean',
                'bulk_find_products_by_eans',
                'match_or_suggest_product',
                'validate_ean_format',
                'get_metrics'
            ]
            
            print("\n✓ Testing: Service methods...")
            for method in methods:
                assert hasattr(service, method), f"Method {method} not found"
                results[method] = "✅ EXISTS"
                print(f"  ✅ {method}")
            
            # Test EAN validation
            print("\n✓ Testing: EAN validation...")
            valid_ean = "5901234123457"  # Valid EAN-13
            validation = await service.validate_ean_format(valid_ean)
            assert validation['valid'], "Valid EAN marked as invalid"
            results['ean_validation'] = "✅ WORKING"
            print(f"  ✅ EAN validation: {validation}")
            
            # Test metrics
            print("\n✓ Testing: Metrics tracking...")
            metrics = service.get_metrics()
            assert 'account_type' in metrics, "Metrics missing account_type"
            results['metrics'] = "✅ WORKING"
            print(f"  ✅ Metrics: {metrics}")
            
            await service.close()
            
            print("\n" + "="*80)
            print(f"EAN SERVICE TESTS: ✅ ALL PASSED ({len(results)} checks)")
            print("="*80)
            
            return {"status": "success", "checks": len(results), "details": results}
            
        except Exception as e:
            print(f"\n❌ EAN Service test failed: {str(e)}")
            return {"status": "failed", "error": str(e), "details": results}
    
    async def test_invoice_service(self):
        """Test Invoice Generation Service."""
        print("\n" + "="*80)
        print("TESTING: Invoice Generation Service")
        print("="*80)
        
        results = {}
        
        try:
            # Test service initialization
            print("\n✓ Testing: Service initialization...")
            service = EmagInvoiceService("main")
            await service.initialize()
            results['initialization'] = "✅ SUCCESS"
            print("  ✅ Service initialized")
            
            # Test methods exist
            methods = [
                'generate_invoice_data',
                'generate_and_attach_invoice',
                'bulk_generate_invoices',
                'get_metrics'
            ]
            
            print("\n✓ Testing: Service methods...")
            for method in methods:
                assert hasattr(service, method), f"Method {method} not found"
                results[method] = "✅ EXISTS"
                print(f"  ✅ {method}")
            
            # Test helper methods
            helper_methods = [
                '_generate_invoice_number',
                '_format_products_for_invoice',
                '_calculate_subtotal',
                '_calculate_vat'
            ]
            
            print("\n✓ Testing: Helper methods...")
            for method in helper_methods:
                assert hasattr(service, method), f"Helper method {method} not found"
                results[f'helper_{method}'] = "✅ EXISTS"
                print(f"  ✅ {method}")
            
            # Test invoice number generation
            print("\n✓ Testing: Invoice number generation...")
            invoice_num = service._generate_invoice_number(12345)
            assert len(invoice_num) > 0, "Invoice number empty"
            results['invoice_number_gen'] = "✅ WORKING"
            print(f"  ✅ Generated: {invoice_num}")
            
            # Test metrics
            print("\n✓ Testing: Metrics tracking...")
            metrics = service.get_metrics()
            assert 'account_type' in metrics, "Metrics missing account_type"
            results['metrics'] = "✅ WORKING"
            print(f"  ✅ Metrics: {metrics}")
            
            await service.close()
            
            print("\n" + "="*80)
            print(f"INVOICE SERVICE TESTS: ✅ ALL PASSED ({len(results)} checks)")
            print("="*80)
            
            return {"status": "success", "checks": len(results), "details": results}
            
        except Exception as e:
            print(f"\n❌ Invoice Service test failed: {str(e)}")
            return {"status": "failed", "error": str(e), "details": results}
    
    async def test_api_endpoints(self):
        """Test API endpoints registration."""
        print("\n" + "="*80)
        print("TESTING: Phase 2 API Endpoints Registration")
        print("="*80)
        
        results = {}
        
        try:
            # Test endpoint module exists
            print("\n✓ Testing: Endpoint module...")
            from app.api.v1.endpoints import emag_phase2
            results['module_exists'] = "✅ EXISTS"
            print("  ✅ emag_phase2 module imported")
            
            # Test router exists
            print("\n✓ Testing: Router...")
            assert hasattr(emag_phase2, 'router'), "Router not found"
            results['router_exists'] = "✅ EXISTS"
            print("  ✅ Router defined")
            
            # Test router is registered
            print("\n✓ Testing: Router registration...")
            from app.api.v1.api import api_router
            
            # Check if routes are registered
            routes = [route.path for route in api_router.routes]
            phase2_routes = [r for r in routes if '/emag/phase2' in r]
            
            assert len(phase2_routes) > 0, "No phase2 routes registered"
            results['routes_registered'] = f"✅ {len(phase2_routes)} ROUTES"
            print(f"  ✅ {len(phase2_routes)} phase2 routes registered")
            
            # Count routes by category
            awb_routes = [r for r in phase2_routes if '/awb' in r]
            ean_routes = [r for r in phase2_routes if '/ean' in r]
            invoice_routes = [r for r in phase2_routes if '/invoice' in r]
            
            print(f"\n  📊 Route breakdown:")
            print(f"    - AWB routes: {len(awb_routes)}")
            print(f"    - EAN routes: {len(ean_routes)}")
            print(f"    - Invoice routes: {len(invoice_routes)}")
            
            results['awb_routes'] = f"✅ {len(awb_routes)}"
            results['ean_routes'] = f"✅ {len(ean_routes)}"
            results['invoice_routes'] = f"✅ {len(invoice_routes)}"
            
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
        print("eMAG INTEGRATION PHASE 2 - IMPLEMENTATION VERIFICATION")
        print("="*80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run tests
        self.results['awb_service'] = await self.test_awb_service()
        self.results['ean_service'] = await self.test_ean_service()
        self.results['invoice_service'] = await self.test_invoice_service()
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
        total_checks = 0
        for category, result in self.results.items():
            if category != 'overall' and isinstance(result, dict):
                status = result.get('status', 'unknown')
                icon = "✅" if status == "success" else "❌"
                checks = result.get('checks', 0)
                total_checks += checks
                print(f"  {icon} {category.upper()}: {status}")
                if status == "success":
                    print(f"     → {checks} checks passed")
        
        print(f"\n  📈 Total checks: {total_checks}")
        
        print("\n" + "="*80)
        if all_passed:
            print("✅ ALL TESTS PASSED - PHASE 2 IMPLEMENTATION VERIFIED!")
        else:
            print("❌ SOME TESTS FAILED - REVIEW ERRORS ABOVE")
        print("="*80)
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return self.results


async def main():
    """Main test runner."""
    tester = Phase2Tester()
    results = await tester.run_all_tests()
    
    # Exit with appropriate code
    exit_code = 0 if results['overall'] == 'success' else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
