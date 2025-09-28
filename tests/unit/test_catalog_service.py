import os
import sys
from unittest.mock import AsyncMock

import pytest

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the catalog service after setting up the path
from app.integrations.emag.services.catalog_service import CatalogService

# Test data
TEST_CATEGORIES = {
    "isError": False,
    "messages": [],
    "results": [
        {"id": 1, "name": "Electronice", "parentId": None, "isLeaf": False},
        {"id": 2, "name": "Telefoane mobile", "parentId": 1, "isLeaf": True},
        {"id": 3, "name": "Laptopuri", "parentId": 1, "isLeaf": True},
        {"id": 4, "name": "Fashion", "parentId": None, "isLeaf": False},
    ]
}

TEST_CHARACTERISTICS = {
    "isError": False,
    "messages": [],
    "results": [
        {
            "id": 101,
            "code": "brand",
            "name": "Brand",
            "type": "TEXT",
            "isRequired": True,
            "isFilter": True,
            "isVariant": True,
            "values": [
                {"id": 1001, "value": "Apple", "isDefault": False},
                {"id": 1002, "value": "Samsung", "isDefault": False},
            ],
        },
        {
            "id": 102,
            "code": "color",
            "name": "Culoare",
            "type": "TEXT",
            "isRequired": False,
            "isFilter": True,
            "isVariant": True,
            "values": [
                {"id": 1003, "value": "Negru", "isDefault": True},
                {"id": 1004, "value": "Alb", "isDefault": False},
            ],
        },
    ]
}

TEST_VAT_RATES = {
    "isError": False,
    "messages": [],
    "results": [
        {"id": 1, "name": "Standard", "value": 19.0, "isDefault": True},
        {"id": 2, "name": "Redus", "value": 9.0, "isDefault": False},
    ]
}

TEST_HANDLING_TIMES = {
    "isError": False,
    "messages": [],
    "defaultHandlingTime": 2,
    "maxHandlingTime": 5,
    "minHandlingTime": 1,
}

@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client with test data."""
    client = AsyncMock()
    
    # Configure the get method to return appropriate test data
    async def mock_get(endpoint, params=None, response_model=None):
        data = None
        if endpoint == "category/read":
            if params and "parent_id" in params:
                parent_id = params["parent_id"]
                results = [cat for cat in TEST_CATEGORIES["results"]]
                data = {
                    "isError": False, 
                    "messages": [], 
                    "results": [r for r in results if r.get("parentId") == parent_id]
                }
            else:
                data = TEST_CATEGORIES
        elif endpoint == "category/read_characteristics":
            data = TEST_CHARACTERISTICS
        elif endpoint == "vat/read":
            data = TEST_VAT_RATES
        elif endpoint == "handling_time/read":
            data = TEST_HANDLING_TIMES
            
        if response_model and data:
            return response_model(**data)
        return data
    
    client.get.side_effect = mock_get
    return client

@pytest.fixture
def catalog_service(mock_http_client):
    """Create a catalog service with a mocked HTTP client."""
    return CatalogService(mock_http_client)

@pytest.mark.asyncio
async def test_get_categories(catalog_service):
    """Test getting all categories."""
    categories = await catalog_service.get_categories()
    assert len(categories) == 4  # Should return all categories
    assert {c.name for c in categories} == {"Electronice", "Telefoane mobile", "Laptopuri", "Fashion"}

@pytest.mark.asyncio
async def test_get_category_characteristics(catalog_service):
    """Test getting category characteristics."""
    characteristics = await catalog_service.get_category_characteristics(1)
    assert len(characteristics) == 2
    assert {c.name for c in characteristics} == {"Brand", "Culoare"}
    assert all(hasattr(c, 'values') for c in characteristics)

@pytest.mark.asyncio
async def test_get_vat_rates(catalog_service):
    """Test getting VAT rates."""
    vat_rates = await catalog_service.get_vat_rates()
    assert len(vat_rates) == 2
    # Check that the VAT rates are correctly formatted
    assert any("Standard (19.0%)" in k for k in vat_rates.keys())
    assert any("Redus (9.0%)" in k for k in vat_rates.keys())
    assert 0.19 in vat_rates.values()
    assert 0.09 in vat_rates.values()

@pytest.mark.asyncio
async def test_get_handling_times(catalog_service):
    """Test getting handling times."""
    handling_times = await catalog_service.get_handling_times()
    assert handling_times["default_handling_time"] == 2
    assert handling_times["min_handling_time"] == 1
    assert handling_times["max_handling_time"] == 5

@pytest.mark.asyncio
async def test_get_category_tree(catalog_service):
    """Test getting the full category tree."""
    category_tree = await catalog_service.get_category_tree()
    # Should have 2 top-level categories
    assert len(category_tree) == 2
    
    # Find Electronics and check its children
    electronics = next((c for c in category_tree if c["id"] == 1), None)
    assert electronics is not None
    assert len(electronics["children"]) == 2
    assert {c["name"] for c in electronics["children"]} == {"Telefoane mobile", "Laptopuri"}
    
    # Check Fashion has no children
    fashion = next((c for c in category_tree if c["id"] == 4), None)
    assert fashion is not None
    assert "children" not in fashion or not fashion["children"]
