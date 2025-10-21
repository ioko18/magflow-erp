"""
eMAG EAN Product Matching Service for MagFlow ERP.

This service handles intelligent product matching and creation using EAN codes:
- Search existing products by EAN
- Smart product creation workflow
- Avoid duplicate products
- Faster product onboarding
"""

import asyncio
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.emag_config import get_emag_config
from app.core.database import async_session_factory
from app.core.exceptions import ServiceError
from app.core.logging import get_logger
from app.models.emag_models import EmagProductV2
from app.services.emag.emag_api_client import EmagApiClient, EmagApiError

logger = get_logger(__name__)


class EmagEANMatchingService:
    """Smart EAN-based product matching service for eMAG integration."""

    def __init__(
        self, account_type: str = "main", db_session: AsyncSession | None = None
    ):
        """Initialize the eMAG EAN matching service.

        Args:
            account_type: Type of eMAG account ('main' or 'fbe')
            db_session: Optional database session
        """
        self.account_type = account_type.lower()
        self.config = get_emag_config(self.account_type)
        self.client: EmagApiClient | None = None
        self.db_session = db_session
        self._metrics = {
            "eans_searched": 0,
            "products_found": 0,
            "products_matched": 0,
            "new_products_suggested": 0,
            "errors": 0,
        }

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def initialize(self):
        """Initialize the eMAG API client."""
        if not self.client:
            self.client = EmagApiClient(
                username=self.config.api_username,
                password=self.config.api_password,
                base_url=self.config.base_url,
                timeout=self.config.api_timeout,
                max_retries=self.config.max_retries,
            )
            await self.client.start()

        logger.info(
            "Initialized eMAG EAN matching service for %s account", self.account_type
        )

    async def close(self):
        """Close the eMAG API client."""
        if self.client:
            await self.client.close()
            self.client = None

    async def find_products_by_ean(self, ean: str) -> dict[str, Any]:
        """Find products on eMAG by EAN code.

        Args:
            ean: EAN barcode to search

        Returns:
            Dictionary with matching products
        """
        logger.info("Searching eMAG for EAN: %s", ean)

        try:
            result = await self.client.find_products_by_eans([ean])

            products = result.get("results", [])
            self._metrics["eans_searched"] += 1
            self._metrics["products_found"] += len(products)

            return {
                "success": True,
                "ean": ean,
                "products": products,
                "count": len(products),
                "account_type": self.account_type,
            }

        except EmagApiError as e:
            logger.error("Failed to search EAN %s: %s", ean, str(e))
            self._metrics["errors"] += 1
            raise ServiceError(f"Failed to search EAN: {str(e)}") from e

    async def bulk_find_products_by_eans(self, eans: list[str]) -> dict[str, Any]:
        """Find multiple products by EAN codes (max 100 per request).

        Args:
            eans: List of EAN codes to search

        Returns:
            Dictionary with matching products for all EANs
        """
        logger.info("Bulk searching %d EANs on eMAG", len(eans))

        # Split into batches of 100
        batches = [eans[i : i + 100] for i in range(0, len(eans), 100)]

        all_products = []

        for batch in batches:
            try:
                result = await self.client.find_products_by_eans(batch)
                products = result.get("results", [])
                all_products.extend(products)

                self._metrics["eans_searched"] += len(batch)
                self._metrics["products_found"] += len(products)

                # Small delay between batches
                if len(batches) > 1:
                    await asyncio.sleep(0.5)

            except EmagApiError as e:
                logger.error("Failed to search EAN batch: %s", str(e))
                self._metrics["errors"] += 1

        return {
            "success": True,
            "eans_searched": len(eans),
            "products_found": len(all_products),
            "products": all_products,
            "account_type": self.account_type,
        }

    async def match_or_suggest_product(
        self, ean: str, product_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Smart product matching: find existing or suggest new product creation.

        Args:
            ean: EAN barcode
            product_data: Optional local product data for matching

        Returns:
            Dictionary with match result and recommendation
        """
        logger.info("Smart matching for EAN: %s", ean)

        try:
            # Search on eMAG
            emag_result = await self.find_products_by_ean(ean)
            emag_products = emag_result.get("products", [])

            # Check local database
            local_product = await self._find_local_product_by_ean(ean)

            # Decision logic
            if emag_products:
                # Product exists on eMAG
                best_match = emag_products[0]

                can_add_offer = best_match.get("allow_to_add_offer", False)
                has_offer = best_match.get("vendor_has_offer", False)

                if has_offer:
                    recommendation = "already_have_offer"
                    action = "update_existing_offer"
                elif can_add_offer:
                    recommendation = "can_add_offer"
                    action = "create_new_offer"
                else:
                    recommendation = "cannot_add_offer"
                    action = "contact_emag_support"

                self._metrics["products_matched"] += 1

                return {
                    "success": True,
                    "ean": ean,
                    "match_found": True,
                    "recommendation": recommendation,
                    "action": action,
                    "emag_product": best_match,
                    "local_product": local_product,
                    "details": {
                        "part_number_key": best_match.get("part_number_key"),
                        "product_name": best_match.get("product_name"),
                        "brand_name": best_match.get("brand_name"),
                        "category_name": best_match.get("category_name"),
                        "site_url": best_match.get("site_url"),
                        "hotness": best_match.get("hotness"),
                        "product_image": best_match.get("product_image"),
                    },
                }
            else:
                # Product not found on eMAG - suggest new product
                self._metrics["new_products_suggested"] += 1

                return {
                    "success": True,
                    "ean": ean,
                    "match_found": False,
                    "recommendation": "create_new_product",
                    "action": "submit_new_product_to_emag",
                    "local_product": local_product,
                    "details": {
                        "message": (
                            "Product not found on eMAG. You can create a new product "
                            "listing."
                        ),
                        "required_fields": [
                            "product_name",
                            "brand",
                            "category_id",
                            "description",
                            "images",
                            "characteristics",
                        ],
                    },
                }

        except Exception as e:
            logger.error("Failed to match product for EAN %s: %s", ean, str(e))
            self._metrics["errors"] += 1
            raise ServiceError(f"Failed to match product: {str(e)}") from e

    async def _find_local_product_by_ean(self, ean: str) -> dict[str, Any] | None:
        """Find product in local database by EAN.

        Args:
            ean: EAN barcode

        Returns:
            Product dictionary or None
        """
        async with async_session_factory() as session:
            # Search in attributes JSONB field
            stmt = (
                select(EmagProductV2)
                .where(EmagProductV2.attributes.contains({"ean": ean}))
                .limit(1)
            )

            result = await session.execute(stmt)
            product = result.scalar_one_or_none()

            if product:
                return {
                    "id": str(product.id),
                    "sku": product.sku,
                    "name": product.name,
                    "brand": product.brand,
                    "price": product.price,
                    "stock_quantity": product.stock_quantity,
                    "account_type": product.account_type,
                }

            return None

    async def validate_ean_format(self, ean: str) -> dict[str, Any]:
        """Validate EAN format and checksum.

        Args:
            ean: EAN barcode to validate

        Returns:
            Dictionary with validation result
        """
        # Remove spaces and dashes
        ean = ean.replace(" ", "").replace("-", "")

        # Check length (EAN-8, EAN-13, UPC-A)
        valid_lengths = [8, 12, 13, 14]

        if len(ean) not in valid_lengths:
            return {
                "valid": False,
                "ean": ean,
                "error": f"Invalid EAN length: {len(ean)}. Must be 8, 12, 13, or 14 digits.",
            }

        # Check if all digits
        if not ean.isdigit():
            return {"valid": False, "ean": ean, "error": "EAN must contain only digits"}

        # Validate checksum for EAN-13
        if len(ean) == 13:
            checksum = self._calculate_ean13_checksum(ean[:-1])
            if checksum != int(ean[-1]):
                return {
                    "valid": False,
                    "ean": ean,
                    "error": f"Invalid EAN-13 checksum. Expected {checksum}, got {ean[-1]}",
                }

        return {"valid": True, "ean": ean, "format": f"EAN-{len(ean)}"}

    def _calculate_ean13_checksum(self, ean_without_check: str) -> int:
        """Calculate EAN-13 checksum digit.

        Args:
            ean_without_check: First 12 digits of EAN-13

        Returns:
            Checksum digit (0-9)
        """
        odd_sum = sum(int(ean_without_check[i]) for i in range(0, 12, 2))
        even_sum = sum(int(ean_without_check[i]) for i in range(1, 12, 2))

        total = odd_sum + (even_sum * 3)
        checksum = (10 - (total % 10)) % 10

        return checksum

    def get_metrics(self) -> dict[str, Any]:
        """Get service metrics."""
        return {"account_type": self.account_type, "metrics": self._metrics.copy()}
