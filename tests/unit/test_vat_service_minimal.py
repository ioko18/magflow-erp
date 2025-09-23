"""Minimal test for VatService with mocks."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest


# Mock VatRate and VatResponse
class VatRate:
    def __init__(
        self,
        id,
        name,
        value,
        isDefault,
        countryCode,
        isActive,
        validFrom=None,
        validTo=None,
    ):
        self.id = id
        self.name = name
        self.value = value
        self.isDefault = isDefault
        self.countryCode = countryCode
        self.isActive = isActive
        self.validFrom = validFrom or "2023-01-01T00:00:00"
        self.validTo = validTo


class VatResponse:
    def __init__(self, isError=False, messages=None, results=None):
        self.isError = isError
        self.messages = messages or []
        self.results = results or []
        self.timestamp = datetime.now(timezone.utc).isoformat()


# Mock the VatService with minimal implementation
class VatService:
    def __init__(self, emag_client=None):
        self.emag_client = emag_client or AsyncMock()

    async def _is_rate_active(self, rate, as_of=None):
        """Check if a rate is active as of the given date."""
        if not rate.isActive:
            return False

        as_of = as_of or datetime.now(timezone.utc)

        # Check valid from
        valid_from = datetime.fromisoformat(
            rate.validFrom.replace("Z", "+00:00"),
        ).replace(tzinfo=timezone.utc)
        if as_of < valid_from:
            return False

        # Check valid to if set
        if rate.validTo:
            valid_to = datetime.fromisoformat(
                rate.validTo.replace("Z", "+00:00"),
            ).replace(tzinfo=timezone.utc)
            if as_of > valid_to:
                return False

        return True

    async def get_vat_rates(self, country_code, force_refresh=False):
        """Get VAT rates for a specific country."""
        return await self.emag_client.get_paginated(
            endpoint="/api/vat",
            country_code=country_code,
            force_refresh=force_refresh,
        )


@pytest.mark.asyncio
async def test_vat_service_basic():
    """Test basic VAT service functionality with mocks."""
    # Create a mock client
    mock_client = AsyncMock()

    # Create test data
    now = datetime.now(timezone.utc)
    future = (now + timedelta(days=30)).isoformat()
    past = (now - timedelta(days=30)).isoformat()

    test_rates = [
        VatRate(1, "TVA 19%", 19.0, True, "RO", True, past, future),
        VatRate(2, "TVA 9%", 9.0, False, "RO", True, past, future),
        VatRate(3, "TVA 5%", 5.0, False, "RO", False, past, future),
    ]

    # Set up the mock to return our test data
    mock_client.get_paginated.return_value = VatResponse(results=test_rates)

    # Create the service with our mock client
    service = VatService(emag_client=mock_client)

    # Test _is_rate_active method
    active_rate = VatRate(1, "Test", 19.0, True, "RO", True, past, future)
    assert await service._is_rate_active(active_rate) is True

    inactive_rate = VatRate(2, "Test", 9.0, False, "RO", False, past, future)
    assert await service._is_rate_active(inactive_rate) is False

    future_rate = VatRate(3, "Test", 5.0, False, "RO", True, future, None)
    assert await service._is_rate_active(future_rate) is False

    print("Basic tests passed!")


@pytest.mark.asyncio
async def test_vat_service_edge_cases():
    """Test VAT service with edge cases and error scenarios."""
    # Create a mock client
    mock_client = AsyncMock()

    # Current time in UTC
    now = datetime.now(timezone.utc)
    future = (now + timedelta(days=30)).isoformat()
    past = (now - timedelta(days=30)).isoformat()

    # Test case 1: Rate with no end date (should be valid indefinitely)
    rate_no_end = VatRate(1, "TVA 19%", 19.0, True, "RO", True, past, None)

    # Test case 2: Future rate (not yet active)
    future_start = (now + timedelta(days=10)).isoformat()
    future_rate = VatRate(2, "Future Rate", 21.0, False, "RO", True, future_start, None)

    # Test case 3: Expired rate
    past_end = (now - timedelta(days=10)).isoformat()
    expired_rate = VatRate(3, "Expired Rate", 9.0, False, "RO", True, past, past_end)

    # Test case 4: Inactive rate
    inactive_rate = VatRate(4, "Inactive Rate", 5.0, False, "RO", False, past, future)

    # Create service with mock client
    service = VatService(emag_client=mock_client)

    # Test rate with no end date
    assert await service._is_rate_active(rate_no_end) is True

    # Test future rate
    assert await service._is_rate_active(future_rate) is False

    # Test expired rate
    assert await service._is_rate_active(expired_rate) is False

    # Test inactive rate
    assert await service._is_rate_active(inactive_rate) is False

    # Test with explicit timestamp
    future_timestamp = now + timedelta(days=35)
    assert await service._is_rate_active(rate_no_end, future_timestamp) is True

    # Test with past timestamp
    past_timestamp = now - timedelta(days=35)
    assert await service._is_rate_active(rate_no_end, past_timestamp) is False

    print("Edge case tests passed!")


@pytest.mark.asyncio
async def test_vat_service_error_handling():
    """Test error handling in VAT service."""
    # Create a mock client that raises an exception
    mock_client = AsyncMock()
    mock_client.get_paginated.side_effect = Exception("API Error")

    # Create service with the error-raising client
    service = VatService(emag_client=mock_client)

    # Test that the error is properly propagated
    with pytest.raises(Exception, match="API Error"):
        await service.get_vat_rates("RO")

    print("Error handling tests passed!")


if __name__ == "__main__":
    import asyncio

    async def run_tests():
        print("Running VAT service tests...")
        await test_vat_service_basic()
        await test_vat_service_edge_cases()
        await test_vat_service_error_handling()
        print("All tests completed successfully!")

    asyncio.run(run_tests())
