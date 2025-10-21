"""
eMAG Batch Processing Service

Handles batch operations for optimal performance (10x improvement).
Implements rate limiting and optimal batch sizes according to eMAG API guidelines.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.config.emag_config import get_emag_config
from app.core.emag_monitoring import get_monitor
from app.core.emag_validator import validate_emag_response
from app.core.exceptions import ServiceError
from app.core.logging import get_logger
from app.services.emag.emag_api_client import EmagApiClient, EmagApiError

logger = get_logger(__name__)
monitor = get_monitor()


class EmagBatchService:
    """
    Service for batch processing of eMAG operations.

    Features:
    - Optimal batch sizing (100 items per batch)
    - Rate limiting (3 requests/second)
    - Progress tracking
    - Error handling per batch
    - Performance monitoring
    """

    # Optimal batch size according to eMAG API guidelines
    OPTIMAL_BATCH_SIZE = 100

    # Rate limiting: 3 requests per second for batch operations
    RATE_LIMIT_DELAY = 0.4  # seconds between requests

    def __init__(self, account_type: str = "main"):
        """
        Initialize Batch Processing Service.

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
            max_retries=self.config.max_retries,
        )

        logger.info("Initialized EmagBatchService for %s account", account_type)

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

    def _create_batches(
        self, items: list[Any], batch_size: int = None
    ) -> list[list[Any]]:
        """
        Split items into optimal batches.

        Args:
            items: List of items to batch
            batch_size: Optional custom batch size (default: OPTIMAL_BATCH_SIZE)

        Returns:
            List of batches
        """
        if batch_size is None:
            batch_size = self.OPTIMAL_BATCH_SIZE

        batches = []
        for i in range(0, len(items), batch_size):
            batches.append(items[i : i + batch_size])

        logger.info(
            "Created %d batches from %d items (batch_size=%d)",
            len(batches),
            len(items),
            batch_size,
        )

        return batches

    async def batch_update_offers(
        self,
        offers: list[dict[str, Any]],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> dict[str, Any]:
        """
        Update multiple offers in batches.

        Args:
            offers: List of offer data dictionaries
            progress_callback: Optional callback for progress updates

        Returns:
            Summary of batch operation results

        Raises:
            ServiceError: If batch operation fails
        """
        if not offers:
            raise ServiceError("No offers provided for batch update")

        batches = self._create_batches(offers)
        results = {
            "total_items": len(offers),
            "total_batches": len(batches),
            "successful_batches": 0,
            "failed_batches": 0,
            "errors": [],
            "start_time": datetime.now(UTC).isoformat(),
        }

        logger.info(
            "Starting batch update of %d offers in %d batches",
            len(offers),
            len(batches),
        )

        # Start monitoring
        monitor.start_sync("batch_offer_update")

        try:
            for batch_idx, batch in enumerate(batches, 1):
                try:
                    logger.info(
                        "Processing batch %d/%d (%d items)",
                        batch_idx,
                        len(batches),
                        len(batch),
                    )

                    # Make API request
                    import time

                    start_time = time.time()

                    response = await self.client._request(
                        "POST", "product_offer/save", json=batch
                    )

                    response_time_ms = (time.time() - start_time) * 1000

                    # Record monitoring metrics
                    monitor.record_request(
                        endpoint="product_offer/save",
                        method="POST",
                        status_code=200,
                        response_time_ms=response_time_ms,
                        account_type=self.account_type,
                        success=not response.get("isError", False),
                        error_message=str(response.get("messages"))
                        if response.get("isError")
                        else None,
                        error_code=response.get("error_code"),
                    )

                    # Validate response
                    validate_emag_response(
                        response, "product_offer/save", "batch_update_offers"
                    )

                    if response.get("isError"):
                        results["failed_batches"] += 1
                        error_msg = (
                            f"Batch {batch_idx} failed: {response.get('messages')}"
                        )
                        results["errors"].append(error_msg)
                        logger.error(error_msg)
                    else:
                        results["successful_batches"] += 1
                        logger.info("Batch %d completed successfully", batch_idx)

                    # Progress callback
                    if progress_callback:
                        progress_callback(batch_idx, len(batches))

                    # Rate limiting: wait between requests
                    if batch_idx < len(batches):
                        await asyncio.sleep(self.RATE_LIMIT_DELAY)

                except EmagApiError as e:
                    results["failed_batches"] += 1
                    error_msg = f"Batch {batch_idx} API error: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)

                    # Continue with next batch
                    continue

            results["end_time"] = datetime.now(UTC).isoformat()
            results["success_rate"] = (
                results["successful_batches"] / results["total_batches"] * 100
                if results["total_batches"] > 0
                else 0
            )

            logger.info(
                "Batch update completed: %d/%d batches successful (%.1f%%)",
                results["successful_batches"],
                results["total_batches"],
                results["success_rate"],
            )

            return results

        finally:
            # End monitoring
            monitor.end_sync()

    async def batch_update_prices(
        self,
        price_updates: list[dict[str, Any]],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> dict[str, Any]:
        """
        Update prices for multiple products in batches.

        Optimized for price-only updates using Light Offer API.

        Args:
            price_updates: List of price update dictionaries
            progress_callback: Optional callback for progress updates

        Returns:
            Summary of batch operation results
        """
        if not price_updates:
            raise ServiceError("No price updates provided")

        # Transform to offer format
        offers = []
        for update in price_updates:
            offers.append(
                {
                    "id": update["product_id"],
                    "sale_price": update["sale_price"],
                    "vat_id": update.get("vat_id", 1),
                }
            )

        return await self.batch_update_offers(offers, progress_callback)

    async def batch_update_stock(
        self,
        stock_updates: list[dict[str, Any]],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> dict[str, Any]:
        """
        Update stock for multiple products in batches.

        Optimized for stock-only updates using Light Offer API.

        Args:
            stock_updates: List of stock update dictionaries
            progress_callback: Optional callback for progress updates

        Returns:
            Summary of batch operation results
        """
        if not stock_updates:
            raise ServiceError("No stock updates provided")

        # Transform to offer format
        offers = []
        for update in stock_updates:
            offers.append(
                {
                    "id": update["product_id"],
                    "stock": update["stock"],
                }
            )

        return await self.batch_update_offers(offers, progress_callback)

    async def get_batch_status(self) -> dict[str, Any]:
        """
        Get current batch processing status and metrics.

        Returns:
            Dictionary with batch processing metrics
        """
        metrics = monitor.get_metrics()
        health = monitor.get_health_status()

        return {
            "account_type": self.account_type,
            "batch_size": self.OPTIMAL_BATCH_SIZE,
            "rate_limit_delay": self.RATE_LIMIT_DELAY,
            "metrics": {
                "total_requests": metrics.total_requests,
                "successful_requests": metrics.successful_requests,
                "failed_requests": metrics.failed_requests,
                "success_rate": metrics.success_rate,
                "average_response_time_ms": metrics.average_response_time_ms,
            },
            "health": health,
        }
