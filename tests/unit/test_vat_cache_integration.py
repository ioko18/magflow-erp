"""Integration tests for VatCache with VatService.

These tests verify the interaction between VatService and VatCache.
"""

from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.integrations.emag.models.responses.vat import VatRate, VatResponse
from app.integrations.emag.services.vat_service import VatService


class MockVatCache:
    """Mock VatCache for testing."""

    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.vat_rates_key = "emag:vat:rates:{country_code}"
        self.default_rate_key = "emag:vat:default_rate:{country_code}"

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a value from the cache."""
        return self.cache.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in the cache."""
        self.cache[key] = value
        return True

    async def delete(self, key: str) -> bool:
        """Delete a value from the cache."""
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    async def get_vat_rates(self, country_code: str) -> Optional[VatResponse]:
        """Get VAT rates from the cache."""
        key = self.vat_rates_key.format(country_code=country_code)
        return await self.get(key)

    async def set_vat_rates(
        self, country_code: str, vat_rates: VatResponse, ttl: Optional[int] = None
    ) -> bool:
        """Set VAT rates in the cache."""
        key = self.vat_rates_key.format(country_code=country_code)
        return await self.set(key, vat_rates, ttl)

    async def get_default_rate(self, country_code: str) -> Optional[float]:
        """Get the default VAT rate from the cache."""
        key = self.default_rate_key.format(country_code=country_code)
        return await self.get(key)

    async def set_default_rate(
        self, country_code: str, rate: float, ttl: Optional[int] = None
    ) -> bool:
        """Set the default VAT rate in the cache."""
        key = self.default_rate_key.format(country_code=country_code)
        return await self.set(key, rate, ttl)


def create_vat_rate(id_: int, name: str, value: float, is_default: bool, country_code: str = "RO") -> VatRate:
    """Create a VatRate instance for testing."""
    return VatRate(
        id=id_,
        name=name,
        value=value,
        is_default=is_default,
        country_code=country_code,
    )


@pytest.fixture
def sample_vat_rates() -> list[VatRate]:
    """Fixture that returns a list of sample VAT rates for testing."""
    return [
        create_vat_rate(1, "Standard", 19.0, True),
        create_vat_rate(2, "Reduced", 9.0, False),
        create_vat_rate(3, "Super Reduced", 5.0, False),
    ]


@pytest.fixture
def vat_cache() -> MockVatCache:
    """Fixture that provides a MockVatCache instance for testing."""
    return MockVatCache()


@pytest.fixture
def mock_emag_client() -> MagicMock:
    """Fixture that provides a mock EMAG client."""
    client = MagicMock()
    client.get_paginated = AsyncMock()
    return client


@pytest.fixture
def vat_service(mock_emag_client: MagicMock, monkeypatch) -> VatService:
    """Fixture that provides a VatService instance with a mocked cache."""
    # Create a mock cache
    mock_cache = MockVatCache()
    
    # Create the service with the mock client
    service = VatService(emag_client=mock_emag_client)
    
    # Replace the service's _cache with our mock
    service._cache = mock_cache
    
    return service


@pytest.fixture
def expected_response(sample_vat_rates: list[VatRate]) -> VatResponse:
    """Fixture that returns the expected VatResponse for testing."""
    return VatResponse(
        results=sample_vat_rates,
        total_count=len(sample_vat_rates),
        is_error=False,
        messages=[],
    )


@pytest.mark.asyncio
async def test_get_vat_rates_cache_hit(
    vat_service: VatService,
    vat_cache: MockVatCache,
    expected_response: VatResponse,
    capsys,
):
    # Set the cache directly with the expected VatResponse object
    cache_key = "vat_rates:RO"
    await vat_service._cache.set(cache_key, expected_response)
    
    # Call the method under test
    result = await vat_service.get_vat_rates('RO')
    
    # Assertions
    assert result is not None, "Result should not be None"
    assert hasattr(result, 'results'), "Result should have 'results' attribute"
    assert len(result.results) == 3, f"Expected 3 results, got {len(result.results) if result.results else 0}"
    assert result.total_count == 3, f"Total count should be 3, got {result.total_count}"
    assert result.is_error is False, f"is_error should be False, got {result.is_error}"
    assert isinstance(result.messages, list), f"messages should be a list, got {type(result.messages).__name__}"
    
    # Verify API was not called
    vat_service.emag_client.get_paginated.assert_not_called()


@pytest.mark.asyncio
async def test_get_vat_rates_cache_miss(
    vat_service: VatService,
    vat_cache: MockVatCache,
    sample_vat_rates: list[VatRate],
    mock_emag_client: MagicMock,
):
    # Mock the API response
    mock_response = VatResponse(
        results=sample_vat_rates,
        total_count=len(sample_vat_rates),
        is_error=False,
        messages=[],
    )
    mock_emag_client.get_paginated.return_value = mock_response
    
    # Call the method under test
    result = await vat_service.get_vat_rates('RO')
    
    # Verify the result
    assert result is not None
    assert result.total_count == 3
    assert len(result.results) == 3
    
    # Verify the API was called
    mock_emag_client.get_paginated.assert_called_once()
    
    # Verify the result was cached
    cached_result = await vat_service._cache.get("vat_rates:RO")
    assert cached_result is not None, "Result was not cached"
    assert cached_result.total_count == 3, f"Expected cached total_count to be 3, got {cached_result.total_count}"
