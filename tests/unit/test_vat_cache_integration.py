"""Integration tests for VatCache with VatService.

These tests verify the interaction between VatService and VatCache.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Mock the VatRate and VatResponse classes
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


# Mock the VatCache class
class MockVatCache:
    def __init__(self):
        self.rates_cache = {}
        self.default_rates = {}

    async def get(self, key):
        if key.startswith("vat_rates:"):
            country = key.split(":")[1]
            return self.rates_cache.get(country)
        if key.startswith("default_vat_rate:"):
            country = key.split(":")[1]
            return self.default_rates.get(country)
        return None

    async def set(self, key, value, ttl=None):
        if key.startswith("vat_rates:"):
            country = key.split(":")[1]
            self.rates_cache[country] = value
        elif key.startswith("default_vat_rate:"):
            country = key.split(":")[1]
            self.default_rates[country] = value
        return True

    async def delete(self, key):
        if key.startswith("vat_rates:"):
            country = key.split(":")[1]
            self.rates_cache.pop(country, None)
        elif key.startswith("default_vat_rate:"):
            country = key.split(":")[1]
            self.default_rates.pop(country, None)
        return True

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


# Import the VatService after mocks are defined
from app.integrations.emag.services.vat_service import VatService  # noqa: E402


@pytest.fixture
def mock_emag_client():
    client = MagicMock()
    client.get_paginated = AsyncMock()
    return client


@pytest.fixture
def vat_cache():
    return MockVatCache()


@pytest.fixture
def vat_service(mock_emag_client, vat_cache):
    with patch(
        "app.integrations.emag.services.vat_service.VatCache",
        return_value=vat_cache,
    ):
        return VatService(emag_client=mock_emag_client)


@pytest.fixture
def sample_vat_rates():
    return [
        VatRate(id=1, name="Standard", value=0.19, is_default=True, country_code="RO"),
        VatRate(id=2, name="Reduced", value=0.09, is_default=False, country_code="RO"),
        VatRate(
            id=3,
            name="Super Reduced",
            value=0.05,
            is_default=False,
            country_code="RO",
        ),
    ]


@pytest.mark.asyncio
async def test_get_vat_rates_cache_hit(
    vat_service,
    vat_cache,
    sample_vat_rates,
    mock_emag_client,
):
    # Setup cache with test data
    expected_response = VatResponse(
        results=sample_vat_rates,
        count=len(sample_vat_rates),
        current_page=1,
        page_count=1,
        items_per_page=100,
    )
    await vat_cache.set_vat_rates("RO", expected_response)

    # Test getting from cache
    result = await vat_service.get_vat_rates("RO")

    # Verify results
    assert result == expected_response
    assert len(result.results) == 3
    assert result.results[0].name == "Standard"
    # Verify API was not called
    mock_emag_client.get_paginated.assert_not_called()


@pytest.mark.asyncio
async def test_get_vat_rates_cache_miss(
    vat_service,
    vat_cache,
    sample_vat_rates,
    mock_emag_client,
):
    # Setup API response
    expected_response = VatResponse(
        results=sample_vat_rates,
        count=len(sample_vat_rates),
        current_page=1,
        page_count=1,
        items_per_page=100,
    )
    mock_emag_client.get_paginated.return_value = expected_response

    # Test getting from API (cache miss)
    result = await vat_service.get_vat_rates("RO")

    # Verify results
    assert result == expected_response
    assert len(result.results) == 3
    # Verify API was called
    mock_emag_client.get_paginated.assert_called_once()
    # Verify cache was updated
    cached = await vat_cache.get_vat_rates("RO")
    assert cached is not None
    assert len(cached.results) == 3


@pytest.mark.skip(reason="Mocking issue with VatCache")
@pytest.mark.asyncio
async def test_get_default_rate_cache_hit(vat_service, vat_cache):
    # Setup cache with test data
    await vat_cache.set_default_rate("RO", 0.19)

    # Test getting from cache
    result = await vat_service.get_default_rate("RO")

    # Verify results
    assert result.value == 0.19
    assert result.is_default
    assert result.country_code == "RO"
    # Verify API was not called
    vat_service.emag_client.get_paginated.assert_not_called()


@pytest.mark.asyncio
async def test_invalidate_vat_cache(vat_service, vat_cache, sample_vat_rates):
    # Setup cache with test data
    response = VatResponse(
        results=sample_vat_rates,
        count=len(sample_vat_rates),
        current_page=1,
        page_count=1,
        items_per_page=100,
    )
    await vat_cache.set_vat_rates("RO", response)
    await vat_cache.set_default_rate("RO", 0.19)

    # Test cache invalidation
    await vat_service.invalidate_vat_cache("RO")

    # Verify cache is empty
    assert await vat_cache.get_vat_rates("RO") is None
    assert await vat_cache.get_default_rate("RO") is None
