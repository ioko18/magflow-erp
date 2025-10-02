"""
eMAG Category Service - v4.4.9

Handles fetching and caching eMAG categories, characteristics, and family types.
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from app.core.logging import get_logger
from app.core.exceptions import ServiceError
from app.services.emag_api_client import EmagApiClient, EmagApiError
from app.config.emag_config import get_emag_config
from app.core.emag_validator import validate_emag_response

logger = get_logger(__name__)


class EmagCategoryService:
    """
    Service for managing eMAG categories, characteristics, and family types.
    
    Provides:
    - Category listing with pagination
    - Category details with characteristics
    - Characteristic values pagination
    - Family types information
    - Multi-language support
    """

    def __init__(self, account_type: str = "main"):
        """
        Initialize Category Service.
        
        Args:
            account_type: Type of eMAG account ('main' or 'fbe')
        """
        self.account_type = account_type
        self.config = get_emag_config(account_type)
        self.client = EmagApiClient(
            username=self.config.api_username,
            password=self.config.api_password,
            base_url=self.config.base_url,
            timeout=self.config.api_timeout,
            max_retries=self.config.max_retries
        )
        self._category_cache: Dict[int, Dict[str, Any]] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(hours=24)  # Cache categories for 24 hours

        logger.info(
            "Initialized EmagCategoryService for %s account",
            account_type
        )

    async def initialize(self):
        """Initialize the service."""
        await self.client.start()

    async def close(self):
        """Close the service and cleanup resources."""
        await self.client.close()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def _is_cache_valid(self) -> bool:
        """Check if category cache is still valid."""
        if not self._cache_timestamp:
            return False
        return datetime.now() - self._cache_timestamp < self._cache_ttl

    async def get_categories(
        self,
        current_page: int = 1,
        items_per_page: int = 100,
        language: str = "ro",
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get list of eMAG categories with pagination.
        
        Args:
            current_page: Page number (default: 1)
            items_per_page: Items per page (max 100, default: 100)
            language: Language code (en, ro, hu, bg, pl, gr, de)
            use_cache: Whether to use cached data
            
        Returns:
            API response with categories list
            
        Raises:
            ServiceError: If fetching fails
        """
        try:
            logger.info(
                "Fetching categories page %d (language: %s)",
                current_page,
                language
            )

            payload = {
                "currentPage": current_page,
                "itemsPerPage": min(items_per_page, 100)
            }

            endpoint = f"category/read?language={language}"
            response = await self.client._request("POST", endpoint, json=payload)

            validate_emag_response(response, "category/read", "get_categories")

            # Cache categories
            if use_cache and "results" in response:
                for category in response["results"]:
                    if "id" in category:
                        self._category_cache[category["id"]] = category

                if not self._cache_timestamp:
                    self._cache_timestamp = datetime.now()

            logger.info(
                "Fetched %d categories",
                len(response.get("results", []))
            )

            return response

        except EmagApiError as e:
            logger.error("Failed to fetch categories: %s", str(e))
            raise ServiceError(f"Category fetch failed: {str(e)}")

    async def get_category_by_id(
        self,
        category_id: int,
        language: str = "ro",
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get detailed category information including characteristics and family types.
        
        Args:
            category_id: eMAG category ID
            language: Language code
            use_cache: Whether to use cached data
            
        Returns:
            Category details with characteristics and family types
            
        Raises:
            ServiceError: If fetching fails
        """
        # Check cache first
        if use_cache and self._is_cache_valid() and category_id in self._category_cache:
            cached = self._category_cache[category_id]
            if "characteristics" in cached:  # Full details cached
                logger.debug("Returning cached category %d", category_id)
                return {"results": [cached]}

        try:
            logger.info("Fetching category %d details", category_id)

            payload = {"id": category_id}

            endpoint = f"category/read?language={language}"
            response = await self.client._request("POST", endpoint, json=payload)

            validate_emag_response(response, "category/read", "get_categories")

            # Cache full category details
            if use_cache and "results" in response and response["results"]:
                self._category_cache[category_id] = response["results"][0]
                self._cache_timestamp = datetime.now()

            logger.info("Fetched category %d details", category_id)
            return response

        except EmagApiError as e:
            logger.error("Failed to fetch category %d: %s", category_id, str(e))
            raise ServiceError(f"Category fetch failed: {str(e)}")

    async def get_characteristic_values(
        self,
        category_id: int,
        characteristic_id: int,
        current_page: int = 1,
        items_per_page: int = 256,
        language: str = "ro"
    ) -> Dict[str, Any]:
        """
        Get paginated characteristic values for a specific characteristic.
        
        New in v4.4.8: Allows pagination through characteristic values.
        
        Args:
            category_id: eMAG category ID
            characteristic_id: Characteristic ID
            current_page: Page number for values
            items_per_page: Items per page (max 256)
            language: Language code
            
        Returns:
            API response with characteristic values
            
        Raises:
            ServiceError: If fetching fails
        """
        try:
            logger.info(
                "Fetching characteristic %d values for category %d (page %d)",
                characteristic_id,
                category_id,
                current_page
            )

            payload = {
                "id": category_id,
                "valuesCurrentPage": current_page,
                "valuesPerPage": min(items_per_page, 256)
            }

            endpoint = f"category/read?language={language}"
            response = await self.client._request("POST", endpoint, json=payload)

            validate_emag_response(response, "category/read", "get_categories")

            # Extract values for the specific characteristic
            if "results" in response and response["results"]:
                category = response["results"][0]
                if "characteristics" in category:
                    for char in category["characteristics"]:
                        if char.get("id") == characteristic_id:
                            return {
                                "characteristic_id": characteristic_id,
                                "values": char.get("values", []),
                                "total_values": len(char.get("values", []))
                            }

            return {
                "characteristic_id": characteristic_id,
                "values": [],
                "total_values": 0
            }

        except EmagApiError as e:
            logger.error(
                "Failed to fetch characteristic %d values: %s",
                characteristic_id,
                str(e)
            )
            raise ServiceError(f"Characteristic values fetch failed: {str(e)}")

    async def count_categories(self) -> int:
        """
        Get total count of categories.
        
        Returns:
            Total number of categories
            
        Raises:
            ServiceError: If counting fails
        """
        try:
            logger.info("Counting categories")

            response = await self.client._request("POST", "category/count", json={})

            validate_emag_response(response, "category/read", "get_categories")

            count = response.get("results", {}).get("count", 0)
            logger.info("Total categories: %d", count)

            return count

        except EmagApiError as e:
            logger.error("Failed to count categories: %s", str(e))
            raise ServiceError(f"Category count failed: {str(e)}")

    async def get_all_categories(
        self,
        language: str = "ro",
        max_pages: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch all categories with pagination.
        
        Args:
            language: Language code
            max_pages: Maximum pages to fetch (safety limit)
            
        Returns:
            List of all categories
            
        Raises:
            ServiceError: If fetching fails
        """
        all_categories = []
        current_page = 1

        try:
            while current_page <= max_pages:
                response = await self.get_categories(
                    current_page=current_page,
                    items_per_page=100,
                    language=language
                )

                results = response.get("results", [])
                if not results:
                    break

                all_categories.extend(results)

                # Check if there are more pages
                if len(results) < 100:
                    break

                current_page += 1

                # Small delay to respect rate limits
                await asyncio.sleep(0.5)

            logger.info("Fetched total of %d categories", len(all_categories))
            return all_categories

        except Exception as e:
            logger.error("Failed to fetch all categories: %s", str(e))
            raise ServiceError(f"Fetch all categories failed: {str(e)}")

    async def get_allowed_categories(
        self,
        language: str = "ro"
    ) -> List[Dict[str, Any]]:
        """
        Get only categories where seller is allowed to post (is_allowed = 1).
        
        Args:
            language: Language code
            
        Returns:
            List of allowed categories
            
        Raises:
            ServiceError: If fetching fails
        """
        all_categories = await self.get_all_categories(language=language)

        allowed = [
            cat for cat in all_categories
            if cat.get("is_allowed") == 1
        ]

        logger.info(
            "Found %d allowed categories out of %d total",
            len(allowed),
            len(all_categories)
        )

        return allowed

    def clear_cache(self):
        """Clear the category cache."""
        self._category_cache.clear()
        self._cache_timestamp = None
        logger.info("Category cache cleared")
