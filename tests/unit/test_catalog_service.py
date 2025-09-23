"""Test script for the eMAG Catalog Service."""

import asyncio
import os
import sys
from typing import Any, Dict, Optional

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the catalog service after setting up the path
from app.integrations.emag.services.catalog_service import CatalogService


# Mock HTTP client for testing
class MockHttpClient:
    """Mock HTTP client for testing the catalog service."""

    def __init__(self):
        """Initialize the mock HTTP client with test data."""
        self.test_data = {
            "category/read": {
                "isError": False,
                "messages": [],
                "results": [
                    {"id": 1, "name": "Electronice", "parentId": None, "isLeaf": False},
                    {
                        "id": 2,
                        "name": "Telefoane mobile",
                        "parentId": 1,
                        "isLeaf": True,
                    },
                    {"id": 3, "name": "Laptopuri", "parentId": 1, "isLeaf": True},
                    {"id": 4, "name": "Fashion", "parentId": None, "isLeaf": False},
                ],
            },
            "category/read_characteristics": {
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
                ],
            },
            "vat/read": {
                "isError": False,
                "messages": [],
                "results": [
                    {"id": 1, "name": "Standard", "value": 19.0, "isDefault": True},
                    {"id": 2, "name": "Redus", "value": 9.0, "isDefault": False},
                ],
            },
            "handling_time/read": {
                "isError": False,
                "messages": [],
                "defaultHandlingTime": 2,
                "maxHandlingTime": 5,
                "minHandlingTime": 1,
            },
        }

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        response_model: Any = None,
    ) -> Any:
        """Mock GET request."""
        # Simulate network delay
        await asyncio.sleep(0.1)

        # Get the test data for this endpoint
        data = self.test_data.get(endpoint)

        # If we have a parent_id filter, filter the results
        if endpoint == "category/read" and params and "parent_id" in params:
            parent_id = params["parent_id"]
            if parent_id is None:
                data["results"] = [
                    cat for cat in data["results"] if cat.get("parentId") is None
                ]
            else:
                data["results"] = [
                    cat for cat in data["results"] if cat.get("parentId") == parent_id
                ]

        # Convert to the response model if provided
        if response_model:
            return response_model(**data)
        return data


async def test_catalog_service():
    """Test the catalog service with mock data."""
    print("=== Testing eMAG Catalog Service ===\n")

    # Create a mock HTTP client and catalog service
    http_client = MockHttpClient()
    catalog_service = CatalogService(http_client)

    try:
        # Test 1: Get all categories
        print("1. Testing get_categories()...")
        categories = await catalog_service.get_categories()
        print(f"   Found {len(categories)} top-level categories")
        for category in categories:
            print(f"   - {category.name} (ID: {category.id}, Leaf: {category.is_leaf})")

        # Test 2: Get category characteristics
        print("\n2. Testing get_category_characteristics()...")
        if categories:
            category_id = categories[0].id
            characteristics = await catalog_service.get_category_characteristics(
                category_id,
            )
            print(
                f"   Found {len(characteristics)} characteristics for category {category_id}",
            )
            for char in characteristics:
                print(f"   - {char.name} ({char.code}, Required: {char.is_required})")
                if char.values:
                    values = ", ".join([f"{v.value}" for v in char.values[:3]])
                    if len(char.values) > 3:
                        values += f"... and {len(char.values) - 3} more"
                    print(f"     Values: {values}")

        # Test 3: Get VAT rates
        print("\n3. Testing get_vat_rates()...")
        vat_rates = await catalog_service.get_vat_rates()
        print("   VAT Rates:")
        for name, rate in vat_rates.items():
            print(f"   - {name}: {rate * 100:.1f}%")

        # Test 4: Get handling times
        print("\n4. Testing get_handling_times()...")
        handling_times = await catalog_service.get_handling_times()
        print("   Handling Times:")
        for name, days in handling_times.items():
            print(f"   - {name}: {days} days")

        # Test 5: Get category tree
        print("\n5. Testing get_category_tree()...")
        category_tree = await catalog_service.get_category_tree()
        print("   Category Tree:")

        def print_category(category: Dict[str, Any], level: int = 0):
            """Recursively print category tree."""
            indent = "  " * level
            print(f"{indent}- {category['name']} (ID: {category['id']})")
            for child in category.get("children", []):
                print_category(child, level + 1)

        for category in category_tree:
            print_category(category)

        print("\n✅ All tests completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e!s}")
        raise


if __name__ == "__main__":
    asyncio.run(test_catalog_service())
