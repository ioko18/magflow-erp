"""Direct test script for VAT models without pytest.
This test runs in isolation without loading application settings.
"""

import os
import sys

# Set minimal environment to avoid loading .env file
os.environ.clear()
os.environ["PYTHONPATH"] = "/app"

# Add the app directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(
    os.path.dirname(current_dir)
)  # Go up two levels from tests/unit/
app_path = os.path.join(project_root, "app")
sys.path.insert(0, app_path)

# Import only the models we need for testing
try:
    from integrations.emag.models.responses.vat import VatRate, VatResponse

    print("✅ Successfully imported VAT models")
except ImportError as e:
    print(f"❌ Error importing VAT models: {e}")
    sys.exit(1)


def test_vat_rate_creation():
    """Test creating a VatRate instance."""
    try:
        vat_rate = VatRate(
            id=1,
            name="TVA 19%",
            value=19.0,
            is_default=True,
            country_code="RO",
            is_active=True,
        )
        assert vat_rate.id == 1
        assert vat_rate.name == "TVA 19%"
        assert vat_rate.value == 19.0
        print("✅ VatRate creation test passed")
    except Exception as e:
        print(f"❌ VatRate creation test failed: {e}")
        return False


def test_vat_response_creation():
    """Test creating a VatResponse instance."""
    try:
        vat_rates = [
            VatRate(
                id=1,
                name="TVA 19%",
                value=19.0,
                is_default=True,
                country_code="RO",
            ),
            VatRate(
                id=2,
                name="TVA 9%",
                value=9.0,
                is_default=False,
                country_code="RO",
            ),
        ]

        response = VatResponse(
            is_error=False,
            messages=[],
            results=vat_rates,
            next_cursor="vat_2",
            prev_cursor=None,
            total_count=2,
        )
        assert not response.is_error
        assert len(response.results) == 2
        print("✅ VatResponse creation test passed")
    except Exception as e:
        print(f"❌ VatResponse creation test failed: {e}")
        return False


def test_vat_response_from_emag():
    """Test creating VatResponse from eMAG API response."""
    try:
        emag_response = {
            "isError": False,
            "messages": [],
            "results": [
                {
                    "id": 1,
                    "name": "TVA 19%",
                    "value": 19.0,
                    "isDefault": True,
                    "countryCode": "RO",
                    "isActive": True,
                },
            ],
        }

        response = VatResponse.from_emag_response(emag_response)
        assert not response.is_error
        assert len(response.results) == 1
        print("✅ VatResponse from_emag_response test passed")
    except Exception as e:
        print(f"❌ VatResponse from_emag_response test failed: {e}")
        return False


if __name__ == "__main__":
    print("\n🔍 Running VAT model tests...\n")

    tests = [
        ("VatRate Creation", test_vat_rate_creation),
        ("VatResponse Creation", test_vat_response_creation),
        ("VatResponse from eMAG", test_vat_response_from_emag),
    ]

    results = []
    for name, test_func in tests:
        print(f"\n🧪 Running test: {name}")
        try:
            test_func()
            results.append(True)
        except Exception as e:
            print(f"❌ Test {name} failed: {e}")
            results.append(False)

    print("\n📊 Test Results:")
    print("-" * 40)
    for (name, _), result in zip(tests, results):
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {name}")

    if all(results):
        print("\n🎉 All tests passed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. See above for details.")
        sys.exit(1)
