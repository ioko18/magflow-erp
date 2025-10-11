"""
Tests for Inventory Management API Filters.

Tests account_type filtering and normalization across inventory endpoints.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.emag_models import EmagProductV2


@pytest.mark.asyncio
async def test_low_stock_filter_by_account_uppercase(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
):
    """Test filtering by account type with uppercase value (MAIN, FBE)."""
    # Test with MAIN (uppercase)
    response = await client.get(
        "/api/v1/emag-inventory/low-stock",
        params={"account_type": "MAIN", "limit": 10},
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    
    # Verify all products are from MAIN account
    products = data["data"]["products"]
    for product in products:
        # In grouped mode, account_type might be "MULTI"
        if product.get("account_type") != "MULTI":
            assert product["account_type"] in ["MAIN", "main"]


@pytest.mark.asyncio
async def test_low_stock_filter_by_account_lowercase(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
):
    """Test filtering by account type with lowercase value (main, fbe)."""
    # Test with fbe (lowercase)
    response = await client.get(
        "/api/v1/emag-inventory/low-stock",
        params={"account_type": "fbe", "limit": 10},
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


@pytest.mark.asyncio
async def test_statistics_filter_by_account(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
):
    """Test statistics endpoint with account filter."""
    # Test with MAIN account
    response = await client.get(
        "/api/v1/emag-inventory/statistics",
        params={"account_type": "MAIN"},
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data
    
    # Test with FBE account
    response = await client.get(
        "/api/v1/emag-inventory/statistics",
        params={"account_type": "FBE"},
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


@pytest.mark.asyncio
async def test_stock_alerts_filter_by_account(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
):
    """Test stock alerts endpoint with account filter."""
    response = await client.get(
        "/api/v1/emag-inventory/stock-alerts",
        params={"account_type": "MAIN", "severity": "critical"},
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


@pytest.mark.asyncio
async def test_invalid_account_type(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
):
    """Test that invalid account type raises error."""
    response = await client.get(
        "/api/v1/emag-inventory/low-stock",
        params={"account_type": "INVALID", "limit": 10},
        headers=auth_headers,
    )
    
    # Should return 500 or 400 error
    assert response.status_code in [400, 500]


@pytest.mark.asyncio
async def test_grouped_by_sku_with_account_filter(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
):
    """Test grouped by SKU mode with account filter."""
    response = await client.get(
        "/api/v1/emag-inventory/low-stock",
        params={
            "account_type": "MAIN",
            "group_by_sku": True,
            "limit": 10
        },
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["grouped_by_sku"] is True


@pytest.mark.asyncio
async def test_non_grouped_with_account_filter(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
):
    """Test non-grouped mode with account filter."""
    response = await client.get(
        "/api/v1/emag-inventory/low-stock",
        params={
            "account_type": "FBE",
            "group_by_sku": False,
            "limit": 10
        },
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["grouped_by_sku"] is False
    
    # Verify all products are from FBE account
    products = data["data"]["products"]
    for product in products:
        assert product["account_type"] in ["FBE", "fbe"]
