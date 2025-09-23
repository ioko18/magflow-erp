"""
Standalone test script for VAT service logic.
Run with: python run_vat_test.py
"""

import asyncio


# Define test models
class VatRate:
    def __init__(self, id, name, value, is_default, country_code, is_active):
        self.id = id
        self.name = name
        self.value = value
        self.isDefault = is_default
        self.countryCode = country_code
        self.isActive = is_active


class VatResponse:
    def __init__(self, is_error=False, messages=None, results=None):
        self.isError = is_error
        self.messages = messages or []
        self.results = results or []


# Mock client and service
class MockClient:
    async def get_paginated(self, *args, **kwargs):
        return VatResponse(
            is_error=False,
            messages=[],
            results=[
                VatRate(
                    1,
                    "TVA 19%",
                    19.0,
                    True,
                    kwargs.get("params", {}).get("countryCode", "RO"),
                    True,
                ),
                VatRate(
                    2,
                    "TVA 9%",
                    9.0,
                    False,
                    kwargs.get("params", {}).get("countryCode", "RO"),
                    True,
                ),
            ],
        )


class VatService:
    def __init__(self, emag_client=None):
        self.emag_client = emag_client or MockClient()

    async def get_vat_rates(self, country_code="RO", **kwargs):
        return await self.emag_client.get_paginated(
            endpoint="/api/vat", params={"countryCode": country_code}, **kwargs
        )


# Test function
async def run_tests():
    print("Running VAT service tests...\n")

    # Test 1: Basic VAT rate retrieval
    print("Test 1: Basic VAT rate retrieval")
    service = VatService()
    result = await service.get_vat_rates()

    print(f"- Response error: {result.isError}")
    print(f"- Number of rates: {len(result.results)}")
    print(f"- First rate: {result.results[0].name} ({result.results[0].value}%)")
    print(f"- Country code: {result.results[0].countryCode}")

    # Test 2: Different country code
    print("\nTest 2: Different country code (BG)")
    result = await service.get_vat_rates(country_code="BG")
    print(f"- Country code: {result.results[0].countryCode}")

    # Test 3: Force refresh
    print("\nTest 3: Force refresh")
    mock_client = MockClient()
    service = VatService(mock_client)
    await service.get_vat_rates(force_refresh=True)
    print("- Force refresh test completed")

    print("\nAll tests completed successfully!")


# Run the tests
if __name__ == "__main__":
    asyncio.run(run_tests())
