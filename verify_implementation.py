#!/usr/bin/env python3
"""
Verification script for eMAG integration enhancements.

Verifies that all new modules can be imported and basic functionality works.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def verify_imports():
    """Verify all new modules can be imported."""
    print("🔍 Verifying module imports...")

    try:
        from app.core import emag_constants, emag_errors, emag_rate_limiter
        from app.services import backup_service, emag_monitoring, order_validation
        _ = (
            emag_constants,
            emag_errors,
            emag_rate_limiter,
            backup_service,
            emag_monitoring,
            order_validation,
        )
        print("✅ All modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def verify_constants():
    """Verify cancellation reasons are defined."""
    print("\n🔍 Verifying cancellation reasons...")

    from app.core.emag_constants import CANCELLATION_REASONS, get_cancellation_reason_text

    expected_codes = [
        1,
        2,
        3,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
        29,
        30,
        31,
        32,
        33,
        34,
        35,
        36,
        37,
        38,
        39,
    ]

    for code in expected_codes:
        if code not in CANCELLATION_REASONS:
            print(f"❌ Missing cancellation reason: {code}")
            return False

    # Test helper function
    text = get_cancellation_reason_text(1)
    if not text:
        print("❌ Helper function not working")
        return False

    print(f"✅ All {len(CANCELLATION_REASONS)} cancellation reasons defined")
    print(f"   Example: Code 1 = '{text}'")
    return True


def verify_validation():
    """Verify order validation works."""
    print("\n🔍 Verifying order validation...")

    from app.services.order_validation import validate_order_data

    # Valid order
    valid_order = {
        "id": 12345,
        "status": 1,
        "payment_mode_id": 1,
        "products": [{"id": 1, "quantity": 2, "sale_price": 99.99, "status": 1}],
        "customer": {"name": "Test", "phone1": "123", "email": "test@test.com"}
    }

    errors = validate_order_data(valid_order)
    if errors:
        print(f"❌ Valid order has errors: {errors}")
        return False

    # Invalid order
    invalid_order = {"id": 12345}
    errors = validate_order_data(invalid_order)
    if not errors:
        print("❌ Invalid order should have errors")
        return False

    print("✅ Order validation working correctly")
    print(f"   Detected {len(errors)} validation errors in invalid order")
    return True


def verify_error_classes():
    """Verify error classes are defined."""
    print("\n🔍 Verifying error classes...")

    from app.core.emag_errors import (
        AuthenticationError,
        RateLimitError,
    )

    # Test error creation
    try:
        error = RateLimitError(remaining_seconds=60)
        if error.status_code != 429:
            print("❌ RateLimitError status code incorrect")
            return False

        error = AuthenticationError()
        if error.status_code != 401:
            print("❌ AuthenticationError status code incorrect")
            return False

        print("✅ All error classes working correctly")
        return True
    except Exception as e:
        print(f"❌ Error class test failed: {e}")
        return False


def verify_rate_limiter():
    """Verify rate limiter is defined."""
    print("\n🔍 Verifying rate limiter...")

    from app.core.emag_rate_limiter import EmagRateLimiter, get_rate_limiter

    try:
        limiter = get_rate_limiter()
        if not isinstance(limiter, EmagRateLimiter):
            print("❌ Rate limiter instance incorrect")
            return False

        # Check usage percentage
        usage = limiter.get_usage_percentage("orders")
        if not (0.0 <= usage <= 1.0):
            print("❌ Usage percentage out of range")
            return False

        print("✅ Rate limiter working correctly")
        print(f"   Current orders usage: {usage:.1%}")
        return True
    except Exception as e:
        print(f"❌ Rate limiter test failed: {e}")
        return False


def verify_database_model():
    """Verify database model has new field."""
    print("\n🔍 Verifying database model...")

    from app.models.emag_models import EmagOrder

    # Check if shipping_tax_voucher_split field exists
    if not hasattr(EmagOrder, 'shipping_tax_voucher_split'):
        print("❌ Missing shipping_tax_voucher_split field")
        return False

    print("✅ Database model updated correctly")
    print("   Field 'shipping_tax_voucher_split' exists")
    return True


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("eMAG Integration Enhancements - Verification")
    print("=" * 60)

    checks = [
        ("Module Imports", verify_imports),
        ("Cancellation Reasons", verify_constants),
        ("Order Validation", verify_validation),
        ("Error Classes", verify_error_classes),
        ("Rate Limiter", verify_rate_limiter),
        ("Database Model", verify_database_model),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} check failed with exception: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print(f"\nTotal: {passed}/{total} checks passed")

    if passed == total:
        print("\n🎉 ALL VERIFICATIONS PASSED!")
        print("The eMAG integration enhancements are ready to use.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} verification(s) failed.")
        print("Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
