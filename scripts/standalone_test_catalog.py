"""Standalone test script for the eMAG Catalog Service."""

import asyncio
from typing import Any


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
        params: dict[str, Any] | None = None,
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


# Define the response models
class BaseResponse:
    """Base response model."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class Category:
    """Category model."""

    def __init__(
        self,
        id: int,
        name: str,
        parentId: int | None = None,
        isLeaf: bool = False,
        **kwargs,
    ):
        self.id = id
        self.name = name
        self.parent_id = parentId
        self.is_leaf = isLeaf

    def dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "parentId": self.parent_id,
            "isLeaf": self.is_leaf,
        }


class CategoryListResponse(BaseResponse):
    """Category list response model."""

    def __init__(
        self,
        isError: bool = False,
        messages: list = None,
        results: list = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.is_error = isError
        self.messages = messages or []
        self.results = [Category(**cat) for cat in (results or [])]


class CategoryCharacteristicValue:
    """Category characteristic value model."""

    def __init__(self, id: int, value: str, isDefault: bool = False, **kwargs):
        self.id = id
        self.value = value
        self.is_default = isDefault


class CategoryCharacteristic:
    """Category characteristic model."""

    def __init__(
        self,
        id: int,
        code: str,
        name: str,
        type: str,
        isRequired: bool = False,
        isFilter: bool = False,
        isVariant: bool = False,
        values: list = None,
        **kwargs,
    ):
        self.id = id
        self.code = code
        self.name = name
        self.type = type
        self.is_required = isRequired
        self.is_filter = isFilter
        self.is_variant = isVariant
        self.values = [CategoryCharacteristicValue(**val) for val in (values or [])]


class CategoryCharacteristicsResponse(BaseResponse):
    """Category characteristics response model."""

    def __init__(
        self,
        isError: bool = False,
        messages: list = None,
        results: list = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.is_error = isError
        self.messages = messages or []
        self.results = [CategoryCharacteristic(**char) for char in (results or [])]


class VatRate:
    """VAT rate model."""

    def __init__(
        self, id: int, name: str, value: float, isDefault: bool = False, **kwargs
    ):
        self.id = id
        self.name = name
        self.value = value
        self.is_default = isDefault


class VatResponse(BaseResponse):
    """VAT response model."""

    def __init__(
        self,
        isError: bool = False,
        messages: list = None,
        results: list = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.is_error = isError
        self.messages = messages or []
        self.results = [VatRate(**rate) for rate in (results or [])]


class HandlingTimeResponse(BaseResponse):
    """Handling time response model."""

    def __init__(
        self,
        defaultHandlingTime: int,
        maxHandlingTime: int,
        minHandlingTime: int,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.default_handling_time = defaultHandlingTime
        self.max_handling_time = maxHandlingTime
        self.min_handling_time = minHandlingTime


class CatalogService:
    """Service for handling eMAG catalog operations."""

    def __init__(self, http_client):
        """Initialize the catalog service.

        Args:
            http_client: An HTTP client instance for making requests to the eMAG API.
        """
        self.http_client = http_client

    async def get_categories(self, parent_id: int | None = None) -> list:
        """Get a list of categories from eMAG.

        Args:
            parent_id: Optional parent category ID to filter by.

        Returns:
            List of Category objects.

        Raises:
            Exception: If there's an error with the API request.
        """
        params = {}
        if parent_id is not None:
            params["parent_id"] = parent_id

        response = await self.http_client.get(
            endpoint="category/read", params=params, response_model=CategoryListResponse
        )

        if hasattr(response, "is_error") and response.is_error:
            raise Exception(
                f"Failed to fetch categories: {getattr(response, 'messages', 'Unknown error')}"
            )

        return response.results

    async def get_category_characteristics(self, category_id: int) -> list:
        """Get characteristics for a specific category.

        Args:
            category_id: The ID of the category to get characteristics for.

        Returns:
            List of CategoryCharacteristic objects.

        Raises:
            Exception: If there's an error with the API request.
        """
        response = await self.http_client.get(
            endpoint="category/read_characteristics",
            params={"category_id": category_id},
            response_model=CategoryCharacteristicsResponse,
        )

        if hasattr(response, "is_error") and response.is_error:
            raise Exception(
                f"Failed to fetch category characteristics: {getattr(response, 'messages', 'Unknown error')}"
            )

        return response.results

    async def get_vat_rates(self) -> dict[str, float]:
        """Get VAT rates from eMAG.

        Returns:
            Dictionary mapping VAT rate names to their values.

        Raises:
            Exception: If there's an error with the API request.
        """
        response = await self.http_client.get(
            endpoint="vat/read", response_model=VatResponse
        )

        if hasattr(response, "is_error") and response.is_error:
            raise Exception(
                f"Failed to fetch VAT rates: {getattr(response, 'messages', 'Unknown error')}"
            )

        return {
            f"{item.name} ({item.value}%)": item.value / 100
            for item in response.results
        }

    async def get_handling_times(self) -> dict[str, int]:
        """Get handling time settings from eMAG.

        Returns:
            Dictionary containing handling time settings.

        Raises:
            Exception: If there's an error with the API request.
        """
        response = await self.http_client.get(
            endpoint="handling_time/read", response_model=HandlingTimeResponse
        )

        if hasattr(response, "is_error") and response.is_error:
            raise Exception(
                f"Failed to fetch handling times: {getattr(response, 'messages', 'Unknown error')}"
            )

        return {
            "default_handling_time": response.default_handling_time,
            "max_handling_time": response.max_handling_time,
            "min_handling_time": response.min_handling_time,
        }

    async def get_category_tree(self) -> list:
        """Get a hierarchical tree of categories.

        Returns:
            List of categories with nested children.

        Raises:
            Exception: If there's an error with the API request.
        """
        # First, get all categories
        all_categories = await self.get_categories()

        # Build a dictionary of categories by ID
        categories_by_id = {cat.id: cat.dict() for cat in all_categories}

        # Build the tree
        tree = []

        for category in all_categories:
            category_dict = categories_by_id[category.id]

            # If this is a top-level category, add it to the tree
            if category.parent_id is None:
                category_dict["children"] = []
                tree.append(category_dict)
            # Otherwise, find its parent and add it as a child
            else:
                parent_id = category.parent_id
                if parent_id in categories_by_id:
                    if "children" not in categories_by_id[parent_id]:
                        categories_by_id[parent_id]["children"] = []
                    categories_by_id[parent_id]["children"].append(category_dict)

        return tree


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
                category_id
            )
            print(
                f"   Found {len(characteristics)} characteristics for category {category_id}"
            )
            for char in characteristics:
                print(f"   - {char.name} ({char.code}, Required: {char.is_required})")
                if hasattr(char, "values") and char.values:
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

        def print_category(category: dict[str, Any], level: int = 0):
            """Recursively print category tree."""
            indent = "  " * level
            print(f"{indent}- {category['name']} (ID: {category['id']})")
            for child in category.get("children", []):
                print_category(child, level + 1)

        for category in category_tree:
            print_category(category)

        print("\n✅ All tests completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(test_catalog_service())
