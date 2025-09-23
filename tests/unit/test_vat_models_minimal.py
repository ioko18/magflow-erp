"""Minimal test script for VAT models with no external dependencies."""


class VatRate:
    """Minimal VatRate model for testing."""

    def __init__(
        self,
        id: int,
        name: str,
        value: float,
        is_default: bool = False,
        country_code: str = "RO",
        is_active: bool = True,
    ):
        self.id = id
        self.name = name
        self.value = value
        self.is_default = is_default
        self.country_code = country_code
        self.is_active = is_active


class VatResponse:
    """Minimal VatResponse model for testing."""

    def __init__(
        self,
        results,
        is_error=False,
        messages=None,
        next_cursor=None,
        prev_cursor=None,
        total_count=0,
    ):
        self.results = results
        self.is_error = is_error
        self.messages = messages or []
        self.next_cursor = next_cursor
        self.prev_cursor = prev_cursor
        self.total_count = total_count

    @classmethod
    def from_emag_response(cls, data):
        """Create from eMAG API response."""
        results = [
            VatRate(
                id=item["id"],
                name=item["name"],
                value=item["value"],
                is_default=item.get("isDefault", False),
                country_code=item.get("countryCode", "RO"),
                is_active=item.get("isActive", True),
            )
            for item in data.get("results", [])
        ]
        return cls(
            results=results,
            is_error=data.get("isError", False),
            messages=data.get("messages", []),
        )


def test_vat_rate_creation():
    """Test creating a VatRate instance."""
    try:
        VatRate(
            id=1,
            name="TVA 19%",
            value=19.0,
            is_default=True,
            country_code="RO",
        )
        print("✅ VatRate creation test passed")
        return True
    except Exception as e:
        print(f"❌ VatRate creation test failed: {e}")
        return False


def test_vat_response_creation():
    """Test creating a VatResponse instance."""
    try:
        vat_rates = [
            VatRate(id=1, name="TVA 19%", value=19.0, is_default=True),
            VatRate(id=2, name="TVA 9%", value=9.0, is_default=False),
        ]

        VatResponse(results=vat_rates, next_cursor="vat_2", total_count=2)
        print("✅ VatResponse creation test passed")
        return True
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

        VatResponse.from_emag_response(emag_response)
        print("✅ VatResponse from_emag_response test passed")
        return True
    except Exception as e:
        print(f"❌ VatResponse from_emag_response test failed: {e}")
        return False


if __name__ == "__main__":
    print("\n🔍 Running minimal VAT model tests...\n")

    tests = [
        ("VatRate Creation", test_vat_rate_creation),
        ("VatResponse Creation", test_vat_response_creation),
        ("VatResponse from eMAG", test_vat_response_from_emag),
    ]

    results = []
    for name, test_func in tests:
        print(f"\n🧪 Running test: {name}")
        results.append(test_func())

    print("\n📊 Test Results:")
    print("-" * 40)
    for (name, _), result in zip(tests, results):
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {name}")

    if all(results):
        print("\n🎉 All tests passed successfully!")
        exit(0)
    else:
        print("\n❌ Some tests failed. See above for details.")
        exit(1)
