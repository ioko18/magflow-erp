"""
eMAG Light Offer API Service - v4.4.9

Provides simplified offer updates using the new Light Offer API endpoint.
This is faster and more efficient than the traditional product_offer/save endpoint.
"""

import asyncio
from typing import Any

from app.config.emag_config import get_emag_config
from app.core.emag_validator import validate_emag_response
from app.core.exceptions import ServiceError
from app.core.logging import get_logger
from app.services.emag.emag_api_client import EmagApiClient, EmagApiError

logger = get_logger(__name__)


class EmagLightOfferService:
    """
    Service for quick offer updates using Light Offer API (v4.4.9).

    This service provides simplified methods for updating existing offers
    without needing to send full product documentation.

    Advantages over traditional API:
    - Faster processing
    - Simpler payload (only changed fields)
    - Recommended for price and stock updates
    """

    def __init__(self, account_type: str = "main"):
        """
        Initialize Light Offer Service.

        Args:
            account_type: Type of eMAG account ('main' or 'fbe')
        """
        self.account_type = account_type
        self.config = get_emag_config(account_type)
        self.client = EmagApiClient(
            username=self.config.api_username,
            password=self.config.api_password,
            base_url=self.config.base_url or "https://marketplace-api.emag.ro/api-3",
        )

        logger.info("Initialized EmagLightOfferService for %s account", account_type)

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

    async def update_offer_price(
        self,
        product_id: int,
        sale_price: float,
        recommended_price: float | None = None,
        min_sale_price: float | None = None,
        max_sale_price: float | None = None,
        current_stock: int = 0,
        vat_id: int = 9,
    ) -> dict[str, Any]:
        """
        Update offer price using Light API (offer/save).

        For FBE (Fulfilled by eMAG) products, this API allows updating ONLY price fields
        without touching stock, which is managed by eMAG fulfillment.

        Args:
            product_id: Seller internal product ID
            sale_price: New sale price without VAT
            recommended_price: Optional recommended retail price
            min_sale_price: Optional minimum sale price
            max_sale_price: Optional maximum sale price
            current_stock: NOT USED (kept for compatibility)
            vat_id: NOT USED (kept for compatibility)

        Returns:
            API response dictionary

        Raises:
            ServiceError: If update fails
        """
        logger.info(
            "Updating price for product %d: sale_price=%.2f", product_id, sale_price
        )

        try:
            # IMPORTANT: Use offer/save (Light API) for FBE products
            # For FBE (Fulfilled by eMAG), we CANNOT modify stock - it's managed by eMAG
            # Light API allows us to update ONLY price fields without touching stock
            # Traditional API (product_offer/save) requires stock field which causes errors for FBE
            response = await self.client.update_offer_light(
                product_id=product_id,
                sale_price=sale_price,
                recommended_price=recommended_price,
                min_sale_price=min_sale_price,
                max_sale_price=max_sale_price,
                # DO NOT send stock, handling_time, status, or vat_id for FBE products
                # These are managed by eMAG fulfillment
            )
            return self._validate_response(response, "price update")
        except EmagApiError as e:
            logger.error(
                "Failed to update price for product %d: %s", product_id, str(e)
            )
            raise ServiceError(f"Failed to update offer price: {str(e)}") from e

    async def update_offer_stock(
        self, product_id: int, stock: int, warehouse_id: int = 1
    ) -> dict[str, Any]:
        """
        Update offer stock using Light Offer API.

        Args:
            product_id: Seller internal product ID
            stock: New stock quantity
            warehouse_id: Warehouse ID (default: 1)

        Returns:
            API response dictionary

        Raises:
            ServiceError: If update fails
        """
        logger.info(
            "Updating stock for product %d: stock=%d (warehouse %d)",
            product_id,
            stock,
            warehouse_id,
        )

        try:
            response = await self.client.update_offer_light(
                product_id=product_id,
                stock=[{"warehouse_id": warehouse_id, "value": stock}],
            )
            return self._validate_response(response, "stock update")
        except EmagApiError as e:
            logger.error(
                "Failed to update stock for product %d: %s", product_id, str(e)
            )
            raise ServiceError(f"Failed to update offer stock: {str(e)}") from e

    async def update_offer_price_and_stock(
        self,
        product_id: int,
        sale_price: float | None = None,
        stock: int | None = None,
        warehouse_id: int = 1,
    ) -> dict[str, Any]:
        """
        Update both price and stock in a single request.

        Args:
            product_id: Seller internal product ID
            sale_price: Optional new sale price
            stock: Optional new stock quantity
            warehouse_id: Warehouse ID (default: 1)

        Returns:
            API response dictionary

        Raises:
            ServiceError: If update fails
        """
        if sale_price is None and stock is None:
            raise ValueError("At least one of sale_price or stock must be provided")

        logger.info(
            "Updating offer for product %d: price=%s, stock=%s",
            product_id,
            f"{sale_price:.2f}" if sale_price else "unchanged",
            f"{stock}" if stock else "unchanged",
        )

        stock_data = [{"warehouse_id": warehouse_id, "value": stock}] if stock is not None else None

        try:
            response = await self.client.update_offer_light(
                product_id=product_id,
                sale_price=sale_price,
                stock=stock_data,
            )
            return self._validate_response(response, "offer update")
        except EmagApiError as e:
            logger.error(
                "Failed to update offer for product %d: %s", product_id, str(e)
            )
            raise ServiceError(f"Failed to update offer: {str(e)}") from e

    async def update_offer_status(self, product_id: int, status: int) -> dict[str, Any]:
        """
        Update offer status (activate/deactivate).

        Args:
            product_id: Seller internal product ID
            status: Offer status (0=inactive, 1=active, 2=deleted)

        Returns:
            API response dictionary

        Raises:
            ServiceError: If update fails
        """
        if status not in [0, 1, 2]:
            raise ValueError("Status must be 0 (inactive), 1 (active), or 2 (deleted)")

        status_text = {0: "inactive", 1: "active", 2: "deleted"}[status]
        logger.info(
            "Updating status for product %d: status=%s", product_id, status_text
        )

        try:
            response = await self.client.update_offer_light(
                product_id=product_id,
                status=status,
            )
            return self._validate_response(response, "status update")
        except EmagApiError as e:
            logger.error(
                "Failed to update status for product %d: %s", product_id, str(e)
            )
            raise ServiceError(f"Failed to update offer status: {str(e)}") from e

    async def bulk_update_prices(
        self, updates: list[dict[str, Any]], batch_size: int = 25
    ) -> dict[str, Any]:
        """
        Bulk update prices for multiple offers.

        Args:
            updates: List of dicts with 'id' and 'sale_price' keys
            batch_size: Number of updates per batch (default: 25, optimal)

        Returns:
            Summary of results
        """
        results = {"total": len(updates), "successful": 0, "failed": 0, "errors": []}

        for i in range(0, len(updates), batch_size):
            batch = updates[i : i + batch_size]

            for update in batch:
                try:
                    await self.update_offer_price(
                        product_id=update["id"], sale_price=update["sale_price"]
                    )
                    results["successful"] += 1
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(
                        {"product_id": update["id"], "error": str(e)}
                    )

                # Small delay between requests
                await asyncio.sleep(0.4)  # ~3 RPS

        logger.info(
            "Bulk price update completed: %d successful, %d failed",
            results["successful"],
            results["failed"],
        )

        return results

    async def bulk_update_stock(
        self, updates: list[dict[str, Any]], batch_size: int = 25
    ) -> dict[str, Any]:
        """
        Bulk update stock for multiple offers.

        Args:
            updates: List of dicts with 'id' and 'stock' keys
            batch_size: Number of updates per batch (default: 25, optimal)

        Returns:
            Summary of results
        """
        results = {"total": len(updates), "successful": 0, "failed": 0, "errors": []}

        for i in range(0, len(updates), batch_size):
            batch = updates[i : i + batch_size]

            for update in batch:
                try:
                    await self.update_offer_stock(
                        product_id=update["id"],
                        stock=update["stock"],
                        warehouse_id=update.get("warehouse_id", 1),
                    )
                    results["successful"] += 1
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(
                        {"product_id": update["id"], "error": str(e)}
                    )

                # Small delay between requests
                await asyncio.sleep(0.4)  # ~3 RPS

        logger.info(
            "Bulk stock update completed: %d successful, %d failed",
            results["successful"],
            results["failed"],
        )

        return results

    def _validate_response(
        self, response: dict[str, Any], operation: str
    ) -> dict[str, Any]:
        """
        Validate eMAG API response using centralized validator.

        Args:
            response: API response dictionary
            operation: Operation description for logging

        Returns:
            Validated response

        Raises:
            ServiceError: If response is invalid or contains errors
        """
        # Use centralized validator with logging and alerting
        return validate_emag_response(response, "/offer/save", operation)
