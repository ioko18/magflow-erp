"""Example eMAG Service using BaseEmagService.

This is an example showing how to refactor existing eMAG services
to use the new BaseEmagService for common functionality.

BEFORE (old approach):
    - Manual rate limiting
    - Repetitive error handling
    - Duplicate logging code
    - No retry logic

AFTER (new approach with BaseEmagService):
    - Automatic rate limiting
    - Built-in retry logic
    - Consistent error handling
    - Structured logging
"""

from typing import Any

from app.services.base import BaseEmagService
from app.services.base.emag_base_service import with_rate_limit, with_retry


class EmagProductServiceRefactored(BaseEmagService):
    """Refactored eMAG Product Service using BaseEmagService.

    This service demonstrates best practices for eMAG integration:
    - Inherits from BaseEmagService for common functionality
    - Uses decorators for rate limiting and retries
    - Clean, focused methods
    - Proper error handling
    """

    def __init__(self, account_type: str = "main"):
        """Initialize the product service.

        Args:
            account_type: Account type ("main" or "fbe")
        """
        super().__init__(
            account_type=account_type,
            service_name="emag_product_service_refactored",
            rate_limit=10,  # 10 requests per second for product endpoints
        )

    async def get_product(self, product_id: int) -> dict[str, Any] | None:
        """Get a single product by ID.

        Args:
            product_id: eMAG product ID

        Returns:
            Product data or None if not found
        """
        self.logger.info(f"Fetching product {product_id}")

        response = await self.make_request(
            endpoint="product_offer/read", data={"id": product_id}
        )

        if self.validate_response(response, required_fields=["id", "name"]):
            return response.get("results")

        return None

    @with_rate_limit(rate_limit=5)  # Override rate limit for this method
    async def get_products_batch(self, product_ids: list[int]) -> list[dict[str, Any]]:
        """Get multiple products in batch (rate limited to 5/s).

        Args:
            product_ids: List of eMAG product IDs

        Returns:
            List of product data
        """
        self.logger.info(f"Fetching {len(product_ids)} products in batch")

        products = []
        for product_id in product_ids:
            try:
                product = await self.get_product(product_id)
                if product:
                    products.append(product)
            except Exception as e:
                self.logger.error(f"Failed to fetch product {product_id}", error=str(e))
                continue

        self.logger.info(f"Successfully fetched {len(products)} products")
        return products

    @with_retry(max_attempts=5, backoff=3.0)  # Retry up to 5 times
    async def update_product_stock(self, product_id: int, stock: int) -> bool:
        """Update product stock with automatic retries.

        Args:
            product_id: eMAG product ID
            stock: New stock quantity

        Returns:
            True if successful, False otherwise
        """
        self.logger.info(
            f"Updating stock for product {product_id}",
            product_id=product_id,
            new_stock=stock,
        )

        response = await self.make_request(
            endpoint="product_offer/save", data={"id": product_id, "stock": stock}
        )

        if self.validate_response(response):
            self.logger.info(
                f"Stock updated successfully for product {product_id}",
                product_id=product_id,
                new_stock=stock,
            )
            return True

        return False

    async def search_products(
        self, query: str, page: int = 1, items_per_page: int = 100
    ) -> dict[str, Any]:
        """Search products by query.

        Args:
            query: Search query
            page: Page number (default: 1)
            items_per_page: Items per page (default: 100)

        Returns:
            Search results with pagination info
        """
        self.logger.info("Searching products", query=query, page=page)

        response = await self.make_request(
            endpoint="product_offer/read",
            data={
                "currentPage": page,
                "itemsPerPage": items_per_page,
                "filters": {"name": query},
            },
        )

        if self.validate_response(response):
            results = response.get("results", [])
            total = response.get("noOfItems", 0)

            self.logger.info(
                f"Found {total} products",
                query=query,
                page=page,
                results_count=len(results),
            )

            return {
                "products": results,
                "total": total,
                "page": page,
                "items_per_page": items_per_page,
                "total_pages": (total + items_per_page - 1) // items_per_page,
            }

        return {
            "products": [],
            "total": 0,
            "page": page,
            "items_per_page": items_per_page,
            "total_pages": 0,
        }


# Example usage:
"""
async def main():
    # Initialize service
    service = EmagProductServiceRefactored(account_type="main")

    try:
        # Get a single product
        product = await service.get_product(12345)
        print(f"Product: {product}")

        # Get multiple products (automatically rate limited)
        products = await service.get_products_batch([12345, 67890, 11111])
        print(f"Fetched {len(products)} products")

        # Update stock (with automatic retries)
        success = await service.update_product_stock(12345, stock=100)
        print(f"Stock update: {'success' if success else 'failed'}")

        # Search products
        results = await service.search_products("laptop")
        print(f"Found {results['total']} products")

    finally:
        # Always close the service
        await service.close()
"""
