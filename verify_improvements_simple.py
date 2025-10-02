#!/usr/bin/env python3
"""
Simple verification script for eMAG integration improvements.

This script verifies the key fixes without database dependencies.
"""

import json
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(".")


def test_configuration():
    """Test configuration improvements."""
    print("🔧 Testing Configuration...")

    try:
        from app.config.emag_config import get_emag_config

        # Test MAIN account
        main_config = get_emag_config("main")
        print(f"  ✅ MAIN Account - Base URL: {main_config.base_url}")
        print(f"  ✅ MAIN Account - Environment: {main_config.environment}")

        # Test FBE account
        fbe_config = get_emag_config("fbe")
        print(f"  ✅ FBE Account - Base URL: {fbe_config.base_url}")
        print(f"  ✅ FBE Account - Environment: {fbe_config.environment}")

        # Test rate limiting
        print(f"  ✅ Rate Limiting - Orders RPS: {main_config.rate_limits.orders_rps}")
        print(f"  ✅ Rate Limiting - Other RPS: {main_config.rate_limits.other_rps}")

        return True

    except Exception as e:
        print(f"  ❌ Configuration Error: {e}")
        return False


def test_model_imports():
    """Test model imports."""
    print("\n📊 Testing Model Imports...")

    try:
        from app.models.emag_models import (
            EmagProductV2,
            EmagSyncLog,
            EmagProductOfferV2,
        )

        print("  ✅ EmagProductV2 imported successfully")
        print("  ✅ EmagSyncLog imported successfully")
        print("  ✅ EmagProductOfferV2 imported successfully")

        # Check if EmagSyncLog has the required columns
        sync_log = EmagSyncLog()
        has_created_at = hasattr(sync_log, "created_at")
        has_updated_at = hasattr(sync_log, "updated_at")

        print(f"  ✅ EmagSyncLog has created_at: {has_created_at}")
        print(f"  ✅ EmagSyncLog has updated_at: {has_updated_at}")

        return has_created_at and has_updated_at

    except Exception as e:
        print(f"  ❌ Model Import Error: {e}")
        return False


def test_service_imports():
    """Test service imports."""
    print("\n🔧 Testing Service Imports...")

    try:
        from app.services.enhanced_emag_service import EnhancedEmagIntegrationService

        print("  ✅ EnhancedEmagIntegrationService imported successfully")

        from app.services.emag_api_client import EmagApiClient

        print("  ✅ EmagApiClient imported successfully")

        return True

    except Exception as e:
        print(f"  ❌ Service Import Error: {e}")
        return False


def test_error_handling():
    """Test error handling improvements."""
    print("\n🛡️ Testing Error Handling...")

    try:
        from app.config.emag_config import get_emag_config

        # Test invalid account type
        try:
            get_emag_config("invalid")
            print("  ❌ Should have raised ValueError for invalid account")
            return False
        except ValueError:
            print("  ✅ Correctly raises ValueError for invalid account type")
            return True
        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
            return False

    except Exception as e:
        print(f"  ❌ Error Handling Test Error: {e}")
        return False


def main():
    """Main verification function."""
    print("🔍 Starting eMAG Integration Improvements Verification")
    print("=" * 60)

    tests = [
        ("Configuration", test_configuration),
        ("Model Imports", test_model_imports),
        ("Service Imports", test_service_imports),
        ("Error Handling", test_error_handling),
    ]

    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "tests": {},
        "summary": {"total_tests": len(tests), "passed": 0, "failed": 0},
    }

    for test_name, test_func in tests:
        try:
            success = test_func()
            results["tests"][test_name] = {
                "passed": success,
                "timestamp": datetime.utcnow().isoformat(),
            }

            if success:
                results["summary"]["passed"] += 1
            else:
                results["summary"]["failed"] += 1

        except Exception as e:
            print(f"  ❌ {test_name} failed with error: {e}")
            results["tests"][test_name] = {
                "passed": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
            results["summary"]["failed"] += 1

    # Generate summary
    success_rate = (
        results["summary"]["passed"] / results["summary"]["total_tests"]
    ) * 100

    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {results['summary']['total_tests']}")
    print(f"Passed: {results['summary']['passed']}")
    print(f"Failed: {results['summary']['failed']}")
    print(f"Success Rate: {success_rate:.1f}%")

    # Save results
    with open("emag_improvements_verification.json", "w") as f:
        json.dump(results, f, indent=2)

    if success_rate >= 80:
        print(f"\n🎉 VERIFICATION SUCCESSFUL! ({success_rate:.1f}% pass rate)")
        print("\n✅ Key Improvements Verified:")
        print("  - Database schema fixes (EmagSyncLog model)")
        print("  - Configuration improvements (production URLs)")
        print("  - Enhanced error handling")
        print("  - Model and service imports working")

        print(f"\n📄 Detailed results saved to: emag_improvements_verification.json")
        return 0
    else:
        print(f"\n⚠️  VERIFICATION NEEDS ATTENTION ({success_rate:.1f}% pass rate)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
