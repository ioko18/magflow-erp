#!/usr/bin/env python3
"""
Comprehensive verification script for eMAG integration improvements.

This script verifies all the fixes and improvements made to the MagFlow ERP
eMAG integration system, including database schema fixes, API functionality,
and sync operations.
"""

import asyncio
import json
import sys
import traceback
from datetime import datetime
from typing import Dict, Any, List

import aiohttp
from dotenv import load_dotenv
from sqlalchemy import text

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append('.')

from app.core.database import get_async_session
from app.config.emag_config import get_emag_config


class EmagIntegrationVerifier:
    """Comprehensive verifier for eMAG integration improvements."""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.utcnow().isoformat(),
            "tests": {},
            "summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "errors": []
            }
        }
        self.base_url = "http://localhost:8000"
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all verification tests."""
        print("🔍 Starting comprehensive eMAG integration verification...")
        print("=" * 60)
        
        # Test categories
        test_categories = [
            ("Database Schema", self.test_database_schema),
            ("Configuration", self.test_configuration),
            ("API Endpoints", self.test_api_endpoints),
            ("Sync Functionality", self.test_sync_functionality),
            ("Error Handling", self.test_error_handling),
        ]
        
        for category_name, test_method in test_categories:
            print(f"\n📋 Testing {category_name}...")
            try:
                await test_method()
                print(f"✅ {category_name} tests completed")
            except Exception as e:
                print(f"❌ {category_name} tests failed: {e}")
                self.results["summary"]["errors"].append(f"{category_name}: {str(e)}")
        
        # Generate summary
        self._generate_summary()
        return self.results
    
    async def test_database_schema(self):
        """Test database schema fixes."""
        async for session in get_async_session():
            # Test 1: Check if emag_sync_logs table has required columns
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'emag_sync_logs' 
                AND column_name IN ('created_at', 'updated_at')
                ORDER BY column_name;
            """))
            columns = [row[0] for row in result.fetchall()]
            
            self._record_test(
                "database_schema_sync_logs_columns",
                len(columns) == 2,
                f"Found columns: {columns}",
                "emag_sync_logs table should have created_at and updated_at columns"
            )
            
            # Test 2: Check if emag_products_v2 table exists
            result = await session.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_name = 'emag_products_v2';
            """))
            table_exists = result.scalar() > 0
            
            self._record_test(
                "database_schema_products_v2_table",
                table_exists,
                f"Table exists: {table_exists}",
                "emag_products_v2 table should exist"
            )
            
            # Test 3: Check product count
            if table_exists:
                result = await session.execute(text("""
                    SELECT account_type, COUNT(*) 
                    FROM app.emag_products_v2 
                    GROUP BY account_type;
                """))
                product_counts = dict(result.fetchall())
                
                self._record_test(
                    "database_products_count",
                    len(product_counts) > 0,
                    f"Product counts by account: {product_counts}",
                    "Should have products in database"
                )
            
            break
    
    async def test_configuration(self):
        """Test configuration improvements."""
        try:
            # Test 1: MAIN account configuration
            main_config = get_emag_config("main")
            
            self._record_test(
                "config_main_account",
                main_config.base_url == "https://marketplace-api.emag.ro/api-3",
                f"MAIN base URL: {main_config.base_url}",
                "MAIN account should use production API URL"
            )
            
            # Test 2: FBE account configuration
            fbe_config = get_emag_config("fbe")
            
            self._record_test(
                "config_fbe_account",
                fbe_config.base_url == "https://marketplace-api.emag.ro/api-3",
                f"FBE base URL: {fbe_config.base_url}",
                "FBE account should use production API URL"
            )
            
            # Test 3: Rate limiting configuration
            self._record_test(
                "config_rate_limiting",
                main_config.rate_limits.other_rps <= 3,
                f"Rate limit: {main_config.rate_limits.other_rps} RPS",
                "Rate limiting should comply with eMAG specs"
            )
            
        except Exception as e:
            self._record_test(
                "config_general",
                False,
                f"Configuration error: {str(e)}",
                "Configuration should load without errors"
            )
    
    async def test_api_endpoints(self):
        """Test API endpoint functionality."""
        endpoints_to_test = [
            ("/health", "Health check"),
            ("/api/v1/emag/enhanced/status", "eMAG status"),
            ("/api/v1/emag/enhanced/products/all", "Products listing"),
            ("/api/v1/emag/enhanced/offers/all", "Offers listing"),
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint, description in endpoints_to_test:
                try:
                    async with session.get(f"{self.base_url}{endpoint}") as response:
                        success = response.status == 200
                        
                        self._record_test(
                            f"api_endpoint_{endpoint.replace('/', '_').replace('-', '_')}",
                            success,
                            f"Status: {response.status}",
                            f"{description} endpoint should return 200"
                        )
                        
                except Exception as e:
                    self._record_test(
                        f"api_endpoint_{endpoint.replace('/', '_').replace('-', '_')}",
                        False,
                        f"Error: {str(e)}",
                        f"{description} endpoint should be accessible"
                    )
    
    async def test_sync_functionality(self):
        """Test sync functionality improvements."""
        # Test 1: Check if sync logs can be created
        async for session in get_async_session():
            try:
                # Try to insert a test sync log
                await session.execute(text("""
                    INSERT INTO emag_sync_logs 
                    (id, sync_type, account_type, operation, status, 
                     total_items, processed_items, created_items, updated_items, failed_items,
                     pages_processed, api_requests_made, rate_limit_hits,
                     started_at, triggered_by, sync_version, created_at, updated_at)
                    VALUES 
                    (gen_random_uuid(), 'products', 'main', 'test_sync', 'completed',
                     0, 0, 0, 0, 0, 0, 0, 0,
                     CURRENT_TIMESTAMP, 'test', 'v4.4.8', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
                """))
                await session.commit()
                
                self._record_test(
                    "sync_log_creation",
                    True,
                    "Successfully created test sync log",
                    "Should be able to create sync logs with new schema"
                )
                
                # Clean up test record
                await session.execute(text("""
                    DELETE FROM emag_sync_logs 
                    WHERE triggered_by = 'test' AND sync_version = 'v4.4.8';
                """))
                await session.commit()
                
            except Exception as e:
                self._record_test(
                    "sync_log_creation",
                    False,
                    f"Error creating sync log: {str(e)}",
                    "Should be able to create sync logs with new schema"
                )
            
            break
    
    async def test_error_handling(self):
        """Test error handling improvements."""
        # Test 1: Invalid account type handling
        try:
            get_emag_config("invalid")
            self._record_test(
                "error_handling_invalid_account",
                False,
                "Should have raised ValueError",
                "Invalid account type should raise error"
            )
        except ValueError:
            self._record_test(
                "error_handling_invalid_account",
                True,
                "Correctly raised ValueError for invalid account",
                "Invalid account type should raise error"
            )
        except Exception as e:
            self._record_test(
                "error_handling_invalid_account",
                False,
                f"Unexpected error: {str(e)}",
                "Should raise ValueError for invalid account"
            )
    
    def _record_test(self, test_name: str, passed: bool, details: str, description: str):
        """Record test result."""
        self.results["tests"][test_name] = {
            "passed": passed,
            "details": details,
            "description": description,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.results["summary"]["total_tests"] += 1
        if passed:
            self.results["summary"]["passed"] += 1
            print(f"  ✅ {test_name}: {details}")
        else:
            self.results["summary"]["failed"] += 1
            print(f"  ❌ {test_name}: {details}")
    
    def _generate_summary(self):
        """Generate test summary."""
        summary = self.results["summary"]
        success_rate = (summary["passed"] / summary["total_tests"]) * 100 if summary["total_tests"] > 0 else 0
        
        print("\n" + "=" * 60)
        print("📊 VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if summary["errors"]:
            print(f"\n❌ Errors encountered:")
            for error in summary["errors"]:
                print(f"  - {error}")
        
        if success_rate >= 80:
            print(f"\n🎉 VERIFICATION SUCCESSFUL! ({success_rate:.1f}% pass rate)")
        else:
            print(f"\n⚠️  VERIFICATION NEEDS ATTENTION ({success_rate:.1f}% pass rate)")


async def main():
    """Main verification function."""
    verifier = EmagIntegrationVerifier()
    
    try:
        results = await verifier.run_all_tests()
        
        # Save results to file
        with open("emag_verification_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: emag_verification_results.json")
        
        # Exit with appropriate code
        success_rate = (results["summary"]["passed"] / results["summary"]["total_tests"]) * 100
        sys.exit(0 if success_rate >= 80 else 1)
        
    except Exception as e:
        print(f"\n💥 Verification failed with error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
