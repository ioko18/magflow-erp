"""Service for handling eMAG catalog operations."""

from typing import Any, Dict, List, Optional

from ..exceptions import EmagAPIError
from ..models.responses.category import (
    Category,
    CategoryCharacteristic,
    CategoryCharacteristicsResponse,
    CategoryListResponse,
)
from ..models.responses.handling_time import HandlingTimeResponse
from ..models.responses.vat import VatResponse


class CatalogService:
    """Service for handling eMAG catalog operations."""

    def __init__(self, http_client):
        """Initialize the catalog service.

        Args:
            http_client: An HTTP client instance for making requests to the eMAG API.

        """
        self.http_client = http_client

    async def get_categories(self, parent_id: Optional[int] = None) -> List[Category]:
        """Get a list of categories from eMAG.

        Args:
            parent_id: Optional parent category ID to filter by.

        Returns:
            List of Category objects.

        Raises:
            EmagAPIError: If there's an error with the API request.

        """
        params = {}
        if parent_id is not None:
            params["parent_id"] = parent_id

        response = await self.http_client.get(
            endpoint="category/read",
            params=params,
            response_model=CategoryListResponse,
        )

        if response.is_error:
            raise EmagAPIError(
                f"Failed to fetch categories: {response.messages}",
                status_code=400,
            )

        return response.results

    async def get_category_characteristics(
        self,
        category_id: int,
    ) -> List[CategoryCharacteristic]:
        """Get characteristics for a specific category.

        Args:
            category_id: The ID of the category to get characteristics for.

        Returns:
            List of CategoryCharacteristic objects.

        Raises:
            EmagAPIError: If there's an error with the API request.

        """
        response = await self.http_client.get(
            endpoint="category/read_characteristics",
            params={"category_id": category_id},
            response_model=CategoryCharacteristicsResponse,
        )

        if response.is_error:
            raise EmagAPIError(
                f"Failed to fetch category characteristics: {response.messages}",
                status_code=400,
            )

        return response.results

    async def get_vat_rates(self) -> Dict[str, float]:
        """Get VAT rates from eMAG.

        Returns:
            Dictionary mapping VAT rate names to their values.

        Raises:
            EmagAPIError: If there's an error with the API request.

        """
        response = await self.http_client.get(
            endpoint="vat/read",
            response_model=VatResponse,
        )

        if response.is_error:
            raise EmagAPIError(
                f"Failed to fetch VAT rates: {response.messages}",
                status_code=400,
            )

        return {
            f"{item.name} ({item.value}%)": item.value / 100
            for item in response.results
        }

    async def get_handling_times(self) -> Dict[str, int]:
        """Get handling time settings from eMAG.

        Returns:
            Dictionary containing handling time settings.

        Raises:
            EmagAPIError: If there's an error with the API request.

        """
        response = await self.http_client.get(
            endpoint="handling_time/read",
            response_model=HandlingTimeResponse,
        )

        if response.is_error:
            raise EmagAPIError(
                f"Failed to fetch handling times: {response.messages}",
                status_code=400,
            )

        return {
            "default_handling_time": response.default_handling_time,
            "max_handling_time": response.max_handling_time,
            "min_handling_time": response.min_handling_time,
        }

    async def get_category_tree(self) -> List[Dict[str, Any]]:
        """Get a hierarchical tree of categories.

        Returns:
            List of categories with nested children.

        Raises:
            EmagAPIError: If there's an error with the API request.

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
