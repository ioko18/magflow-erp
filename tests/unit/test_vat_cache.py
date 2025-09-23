"""Unit tests for VAT cache functionality."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Mock the VatRate and VatResponse classes
class VatRate:
    def __init__(self, id, name, value, is_default, countryCode):
        self.id = id
        self.name = name
        self.value = value
        self.is_default = is_default
        self.countryCode = countryCode


class VatResponse:
    def __init__(self, results, count, current_page, page_count, items_per_page):
        self.results = results
        self.count = count
        self.current_page = current_page
        self.page_count = page_count
        self.items_per_page = items_per_page


# Mock the VatCache class
class VatCache:
    @staticmethod
    async def get_vat_rates(country_code: str):
        pass

    @staticmethod
    async def set_vat_rates(country_code: str, vat_response):
        pass

    @staticmethod
    async def get_default_rate(country_code: str):
        pass

    @staticmethod
    async def set_default_rate(country_code: str, rate: float):
        pass

    @staticmethod
    async def invalidate_vat_cache(country_code: str):
        pass


@pytest.fixture
def mock_redis():
    # Create a simple mock for the Redis cache
    mock = MagicMock()
    mock.get_json = AsyncMock()
    mock.set_json = AsyncMock(return_value=True)
    mock.redis = MagicMock()
    mock.redis.keys = AsyncMock(return_value=[])
    mock.redis.delete = AsyncMock()

    with patch("app.cache.redis_cache.cache", mock):
        yield mock


@pytest.mark.asyncio
async def test_get_vat_rates_cache_hit(mock_redis):
    """Test getting VAT rates from cache."""
    # Setup mock cache response
    test_data = {
        "data": {
            "results": [
                {
                    "id": 1,
                    "name": "Standard",
                    "value": 0.19,
                    "is_default": True,
                    "countryCode": "RO",
                },
                {
                    "id": 2,
                    "name": "Reduced",
                    "value": 0.09,
                    "is_default": False,
                    "countryCode": "RO",
                },
            ],
            "count": 2,
            "current_page": 1,
            "page_count": 1,
            "items_per_page": 100,
        },
        "cached_at": datetime.utcnow().isoformat(),
        "ttl": 86400,
    }
    mock_redis.get_json.return_value = test_data

    # Test getting from cache
    result = await VatCache.get_vat_rates("RO")

    # Verify results
    assert result is not None
    assert len(result.results) == 2
    assert result.results[0].id == 1
    assert result.results[0].value == 0.19
    assert result.results[0].is_default is True
    mock_redis.get_json.assert_called_once_with("emag:vat:rates:RO")


@pytest.mark.asyncio
async def test_get_vat_rates_cache_miss(mock_redis):
    """Test getting VAT rates when cache miss occurs."""
    # Setup cache miss
    mock_redis.get_json.return_value = None

    # Test getting from cache
    result = await VatCache.get_vat_rates("RO")

    # Verify results
    assert result is None
    mock_redis.get_json.assert_called_once_with("emag:vat:rates:RO")


@pytest.mark.asyncio
async def test_set_vat_rates(mock_redis):
    """Test setting VAT rates in cache."""
    # Setup test data
    test_rates = [
        VatRate(id=1, name="Standard", value=0.19, is_default=True, countryCode="RO"),
        VatRate(id=2, name="Reduced", value=0.09, is_default=False, countryCode="RO"),
    ]
    vat_response = VatResponse(
        results=test_rates,
        count=2,
        current_page=1,
        page_count=1,
        items_per_page=100,
    )

    # Test setting cache
    result = await VatCache.set_vat_rates("RO", vat_response)

    # Verify results
    assert result is True
    mock_redis.set_json.assert_called_once()
    args, kwargs = mock_redis.set_json.call_args
    assert kwargs["key"] == "emag:vat:rates:RO"
    assert kwargs["ttl"] == 86400  # 24 hours in seconds
    assert "data" in kwargs["value"]
    assert len(kwargs["value"]["data"]["results"]) == 2


@pytest.mark.asyncio
async def test_get_default_rate_cache_hit(mock_redis):
    """Test getting default VAT rate from cache."""
    # Setup mock cache response
    test_data = {"data": 0.19, "cached_at": datetime.utcnow().isoformat(), "ttl": 3600}
    mock_redis.get_json.return_value = test_data

    # Test getting from cache
    result = await VatCache.get_default_rate("RO")

    # Verify results
    assert result == 0.19
    mock_redis.get_json.assert_called_once_with("emag:vat:default:RO")


@pytest.mark.asyncio
async def test_invalidate_vat_cache(mock_redis):
    """Test invalidating VAT cache."""
    # Setup mock keys
    mock_redis.redis.keys.return_value = [b"emag:vat:rates:RO", b"emag:vat:default:RO"]

    # Test invalidation
    await VatCache.invalidate_vat_cache("RO")

    # Verify results
    mock_redis.redis.keys.assert_called_once_with("emag:vat:rates:RO")
    mock_redis.redis.delete.assert_called_once_with(
        "emag:vat:rates:RO",
        "emag:vat:default:RO",
    )


@pytest.mark.asyncio
async def test_invalidate_vat_cache_no_keys(mock_redis):
    """Test invalidating VAT cache when no keys match."""
    # Setup mock keys
    mock_redis.redis.keys.return_value = []

    # Test invalidation
    await VatCache.invalidate_vat_cache("RO")

    # Verify results
    mock_redis.redis.keys.assert_called_once_with("emag:vat:rates:RO")
    mock_redis.redis.delete.assert_not_called()
