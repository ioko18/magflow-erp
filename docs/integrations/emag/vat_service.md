# VatService API Documentation

## Overview

The `VatService` class provides a high-level interface for working with VAT rates in the eMAG Marketplace API. It handles caching, rate limiting, error handling, and provides convenient methods for common VAT-related operations.

## Table of Contents

- [Installation](#installation)
- [Initialization](#initialization)
- [API Reference](#api-reference)
  - [get_vat_rates](#get_vat_rates)
  - [get_default_rate](#get_default_rate)
  - [get_rate_by_id](#get_rate_by_id)
  - [get_rates_by_country](#get_rates_by_country)
  - [refresh_vat_rates](#refresh_vat_rates)
- [Error Handling](#error-handling)
- [Examples](#examples)
- [Caching](#caching)
- [Best Practices](#best-practices)

## Installation

```python
from app.integrations.emag.services.vat_service import VatService
```

## Initialization

```python
# Basic initialization
vat_service = VatService()

# Or with a custom client
from app.integrations.emag.client import EmagAPIClient
client = EmagAPIClient()
vat_service = VatService(emag_client=client)

# Use as a context manager (recommended)
async with VatService() as vat_service:
    # Use the service
    pass
```

## API Reference

### get_vat_rates

Retrieves VAT rates for a specific country with optional pagination and caching.

```python
async def get_vat_rates(
    self,
    country_code: str = "RO",
    cursor: Optional[str] = None,
    limit: int = 100,
    force_refresh: bool = False,
    include_inactive: bool = False
) -> VatResponse:
    """Get VAT rates for a specific country with caching and fallback.
    
    Args:
        country_code: ISO 2-letter country code (default: "RO")
        cursor: Pagination cursor for large result sets
        limit: Maximum number of results per page (default: 100, max: 500)
        force_refresh: If True, bypass cache and fetch fresh data
        include_inactive: If True, include inactive VAT rates
            
    Returns:
        VatResponse: Response containing VAT rates and pagination info
            
    Raises:
        ValueError: If country_code is invalid
        EmagAPIError: If there's an error fetching from the API
    """
```

### get_default_rate

Gets the default VAT rate for a specific country and optional date.

```python
async def get_default_rate(
    self,
    country_code: str = "RO",
    force_refresh: bool = False,
    effective_date: Optional[datetime] = None
) -> VatRate:
    """Get the default VAT rate for a specific country and optional date.
    
    Args:
        country_code: ISO 2-letter country code (default: "RO")
        force_refresh: If True, bypass cache and fetch fresh data
        effective_date: Optional date to get the default rate for.
                      If None, uses current date.
                      
    Returns:
        VatRate: The default VAT rate for the country and date
            
    Raises:
        ValueError: If no default rate is found for the country/date
        EmagAPIError: If there's an error fetching from the API
    """
```

### get_rate_by_id

Gets a specific VAT rate by ID, optionally filtered by country.

```python
async def get_rate_by_id(
    self,
    rate_id: int,
    country_code: Optional[str] = None,
    force_refresh: bool = False
) -> Optional[VatRate]:
    """Get a specific VAT rate by ID, optionally filtered by country.
    
    Args:
        rate_id: The ID of the VAT rate to retrieve
        country_code: Optional country code to filter by
        force_refresh: If True, bypass cache and fetch fresh data
            
    Returns:
        Optional[VatRate]: The VAT rate if found, None otherwise
            
    Raises:
        EmagAPIError: If there's an error fetching from the API
    """
```

### get_rates_by_country

Gets all VAT rates for a country, optionally filtered by date.

```python
async def get_rates_by_country(
    self,
    country_code: str,
    active_only: bool = True,
    effective_date: Optional[datetime] = None,
    force_refresh: bool = False
) -> List[VatRate]:
    """Get all VAT rates for a country, optionally filtered by date.
    
    Args:
        country_code: ISO 2-letter country code
        active_only: If True, only return rates active on the effective date
        effective_date: Optional date to check for active rates.
                      If None, uses current date.
        force_refresh: If True, bypass cache and fetch fresh data
            
    Returns:
        List[VatRate]: List of VAT rates matching the criteria
            
    Raises:
        ValueError: If country_code is invalid
        EmagAPIError: If there's an error fetching from the API
    """
```

### refresh_vat_rates

Force refresh the cached VAT rates for specific countries or rates.

```python
async def refresh_vat_rates(
    self,
    country_code: Optional[Union[str, List[str]]] = None,
    rate_ids: Optional[List[int]] = None
) -> None:
    """Force refresh the cached VAT rates for specific countries or rates.
    
    Args:
        country_code: Optional country code or list of country codes to refresh.
                    If None, refreshes all cached VAT rates.
        rate_ids: Optional list of rate IDs to refresh. Takes precedence over country_code.
    """
```

## Error Handling

The `VatService` raises the following exceptions:

- `ValueError`: For invalid input parameters
- `TypeError`: For incorrect parameter types
- `EmagAPIError`: For errors returned by the eMAG API
- `aiohttp.ClientError`: For network-related errors

## Examples

### Basic Usage

```python
from datetime import datetime, timezone
from app.integrations.emag.services.vat_service import VatService

async def example():
    async with VatService() as vat_service:
        # Get VAT rates for Romania
        response = await vat_service.get_vat_rates(country_code="RO")
        for rate in response.results:
            print(f"{rate.name}: {rate.value}%")
        
        # Get the default VAT rate
        default_rate = await vat_service.get_default_rate(country_code="RO")
        print(f"Default VAT rate: {default_rate.value}%")
        
        # Get VAT rate by ID
        rate = await vat_service.get_rate_by_id(rate_id=1, country_code="RO")
        if rate:
            print(f"Found rate: {rate.name} ({rate.value}%)")
        
        # Get rates for a specific date
        date = datetime(2023, 6, 1, tzinfo=timezone.utc)
        rates = await vat_service.get_rates_by_country(
            country_code="RO",
            effective_date=date
        )
        print(f"Found {len(rates)} rates active on {date}")
```

### Error Handling

```python
from app.integrations.emag.client import EmagAPIError

try:
    rate = await vat_service.get_default_rate(country_code="INVALID")
except ValueError as e:
    print(f"Invalid input: {e}")
except EmagAPIError as e:
    print(f"API error: {e}")
    
    # Check if we have cached data we can use
    try:
        rate = await vat_service.get_default_rate(country_code="RO", force_refresh=False)
        print(f"Using cached rate: {rate.value}%")
    except Exception as fallback_error:
        print(f"No cached data available: {fallback_error}")
```

## Caching

The `VatService` uses Redis for caching with the following default TTLs:

- VAT rates: 1 hour
- Default rates: 1 hour
- Individual rates: 1 hour

You can force a refresh of the cache by setting `force_refresh=True` on any method.

## Best Practices

1. **Use context managers**: Always use `VatService` as a context manager to ensure proper cleanup of resources.

1. **Handle errors gracefully**: Always catch and handle potential exceptions, especially `EmagAPIError` and `aiohttp.ClientError`.

1. **Use caching effectively**: Take advantage of the built-in caching to reduce API calls. Only use `force_refresh` when you need the most up-to-date data.

1. **Batch operations**: When possible, use batch methods like `get_vat_rates` instead of multiple `get_rate_by_id` calls.

1. **Monitor rate limits**: The eMAG API has rate limits. The `VatService` includes rate limiting, but be mindful of your usage patterns.

1. **Logging**: The service logs important events and errors. Make sure your logging configuration is set up to capture these logs.

1. **Testing**: Use the provided test fixtures to write integration tests for your code that uses `VatService`.
