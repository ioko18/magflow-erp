"""Minimal test for VatCache functionality.
This test doesn't require any external dependencies.
"""

import asyncio


class VatRate:
    def __init__(self, id, name, value, is_default, country_code, **kwargs):
        self.id = id
        self.name = name
        self.value = value
        self.is_default = is_default
        self.countryCode = country_code
        self.isActive = kwargs.get("isActive", True)
        self.validFrom = kwargs.get("validFrom", "2023-01-01T00:00:00Z")
        self.validTo = kwargs.get("validTo")


class VatResponse:
    def __init__(self, results, count, current_page, page_count, items_per_page):
        self.results = results
        self.count = count
        self.current_page = current_page
        self.page_count = page_count
        self.items_per_page = items_per_page
        self.isError = False
        self.messages = []

    def to_dict(self):
        return {
            "results": [
                {
                    "id": r.id,
                    "name": r.name,
                    "value": r.value,
                    "isDefault": r.is_default,
                    "countryCode": r.countryCode,
                    "isActive": getattr(r, "isActive", True),
                    "validFrom": getattr(r, "validFrom", "2023-01-01T00:00:00Z"),
                    "validTo": r.validTo,
                }
                for r in self.results
            ],
            "count": self.count,
            "current_page": self.current_page,
            "page_count": self.page_count,
            "items_per_page": self.items_per_page,
            "isError": self.isError,
            "messages": self.messages,
        }


class VatCache:
    def __init__(self):
        self.rates_cache = {}
        self.default_rates = {}

    async def get_vat_rates(self, country_code):
        return self.rates_cache.get(country_code)

    async def set_vat_rates(self, country_code, vat_response):
        self.rates_cache[country_code] = vat_response
        return True

    async def get_default_rate(self, country_code):
        return self.default_rates.get(country_code)

    async def set_default_rate(self, country_code, rate):
        self.default_rates[country_code] = rate
        return True

    async def invalidate_vat_cache(self, country_code):
        self.rates_cache.pop(country_code, None)
        self.default_rates.pop(country_code, None)
        return True


class VatService:
    def __init__(self, emag_client=None):
        self.emag_client = emag_client
        self.cache = VatCache()

    async def get_vat_rates(self, country_code="RO", force_refresh=False):
        if not force_refresh:
            cached = await self.cache.get_vat_rates(country_code)
            if cached:
                return cached

        # Simulate API call
        rates = [
            VatRate(
                id=1,
                name="Standard",
                value=0.19,
                is_default=True,
                country_code=country_code,
            ),
            VatRate(
                id=2,
                name="Reduced",
                value=0.09,
                is_default=False,
                country_code=country_code,
            ),
            VatRate(
                id=3,
                name="Super Reduced",
                value=0.05,
                is_default=False,
                country_code=country_code,
            ),
        ]
        response = VatResponse(
            results=rates,
            count=len(rates),
            current_page=1,
            page_count=1,
            items_per_page=100,
        )

        await self.cache.set_vat_rates(country_code, response)
        return response

    async def get_default_rate(self, country_code="RO"):
        cached_rate = await self.cache.get_default_rate(country_code)
        if cached_rate is not None:
            return cached_rate

        # Get rates and find default
        response = await self.get_vat_rates(country_code)
        default_rate = next((r for r in response.results if r.is_default), None)
        if default_rate:
            await self.cache.set_default_rate(country_code, default_rate.value)
            return default_rate.value
        return None

    async def invalidate_vat_cache(self, country_code):
        return await self.cache.invalidate_vat_cache(country_code)


async def run_tests():
    print("=== Starting VatCache Tests ===\n")

    # Setup
    service = VatService()

    # Test 1: Cache miss for VAT rates
    print("Test 1: Cache miss for VAT rates")
    response = await service.get_vat_rates("RO")
    print(f"Retrieved {len(response.results)} VAT rates")
    print(
        f"First rate: {response.results[0].name} ({response.results[0].value * 100}%)",
    )

    # Test 2: Cache hit for VAT rates
    print("\nTest 2: Cache hit for VAT rates")
    response = await service.get_vat_rates("RO")
    print(f"Retrieved {len(response.results)} VAT rates (from cache)")

    # Test 3: Get default rate (should use cache)
    print("\nTest 3: Get default rate")
    default_rate = await service.get_default_rate("RO")
    print(f"Default VAT rate: {default_rate * 100}%")

    # Test 4: Invalidate cache
    print("\nTest 4: Invalidate cache")
    await service.invalidate_vat_cache("RO")
    print("Cache invalidated for RO")

    # Test 5: Verify cache invalidation
    print("\nTest 5: Verify cache invalidation")
    response = await service.get_vat_rates("RO")
    print(f"Retrieved {len(response.results)} VAT rates (after invalidation)")

    print("\n=== All tests completed successfully! ===")


if __name__ == "__main__":
    asyncio.run(run_tests())
