"""Service for handling eMAG product offer operations."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any, TypeVar
from uuid import uuid4

from ..exceptions import EmagAPIError
from ..models.requests.offer import (
    ProductOfferBulkUpdate,
    ProductOfferCreate,
    ProductOfferFilter,
    ProductOfferUpdate,
)
from ..models.responses.offer import (
    ProductOfferBulkResponse,
    ProductOfferListResponse,
    ProductOfferResponse,
    ProductOfferSyncResponse,
    ProductOfferSyncStatus,
)

logger = logging.getLogger(__name__)
T = TypeVar("T")


class OfferService:
    """Service for handling eMAG product offer operations."""

    def __init__(self, http_client, rate_limiter):
        """Initialize the offer service.

        Args:
            http_client: An HTTP client instance for making requests to the eMAG API.
            rate_limiter: A rate limiter instance for controlling request rates.

        """
        self.http_client = http_client
        self.rate_limiter = rate_limiter
        self.batch_size = 50  # eMAG's maximum batch size for bulk operations

    async def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: dict[str, Any] | None = None,
        response_model: type[T] | None = None,
        is_order_endpoint: bool = False,
        retries: int = 3,
    ) -> Any:
        """Make an HTTP request with rate limiting and retry logic.

        Args:
            endpoint: The API endpoint to call.
            method: The HTTP method to use (GET, POST, PUT, DELETE).
            data: The request payload.
            response_model: The Pydantic model to parse the response into.
            is_order_endpoint: Whether this is an order-related endpoint (different rate limits).
            retries: Number of retry attempts.

        Returns:
            The parsed response.

        Raises:
            EmagAPIError: If the request fails after all retries.

        """
        last_error = None

        for attempt in range(retries):
            try:
                # Apply rate limiting
                await self.rate_limiter.wait_for_capacity(
                    is_order_endpoint=is_order_endpoint,
                )

                # Make the request
                if method.upper() == "GET":
                    response = await self.http_client.get(
                        endpoint=endpoint,
                        params=data,
                        response_model=response_model,
                    )
                elif method.upper() == "POST":
                    response = await self.http_client.post(
                        endpoint=endpoint,
                        data=data,
                        response_model=response_model,
                    )
                elif method.upper() == "PUT":
                    response = await self.http_client.put(
                        endpoint=endpoint,
                        data=data,
                        response_model=response_model,
                    )
                elif method.upper() == "DELETE":
                    response = await self.http_client.delete(
                        endpoint=endpoint,
                        data=data,
                        response_model=response_model,
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Check for API-level errors
                if hasattr(response, "is_error") and response.is_error:
                    error_msg = getattr(response, "messages", "Unknown error")
                    raise EmagAPIError(
                        f"API error in {endpoint}: {error_msg}",
                        status_code=400,
                    )

                return response

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Attempt {attempt + 1}/{retries} failed for {method} {endpoint}: {e!s}",
                )

                # Exponential backoff
                if attempt < retries - 1:
                    wait_time = (2**attempt) * 0.5  # 0.5s, 1s, 2s, etc.
                    await asyncio.sleep(wait_time)

        # If we get here, all retries failed
        raise EmagAPIError(
            f"Failed to execute {method} {endpoint} after {retries} attempts: {last_error!s}",
            status_code=(
                getattr(last_error, "status_code", 500)
                if hasattr(last_error, "status_code")
                else 500
            ),
        )

    async def create_offer(
        self,
        offer_data: ProductOfferCreate,
    ) -> ProductOfferResponse:
        """Create a new product offer.

        Args:
            offer_data: The product offer data.

        Returns:
            The created product offer.

        Raises:
            EmagAPIError: If the creation fails.

        """
        endpoint = "product_offer/save"
        response = await self._make_request(
            endpoint=endpoint,
            method="POST",
            data=offer_data.model_dump(exclude_none=True),
            response_model=ProductOfferListResponse,
        )

        if not response.results:
            raise EmagAPIError("No offer was created", status_code=400)

        return response.results[0]

    async def update_offer(
        self,
        product_id: str,
        update_data: ProductOfferUpdate,
    ) -> ProductOfferResponse:
        """Update an existing product offer.

        Args:
            product_id: The ID of the product to update.
            update_data: The fields to update.

        Returns:
            The updated product offer.
        Raises:
            EmagAPIError: If the update fails.

        """
        endpoint = "product_offer/save"
        data = {"product_id": product_id, **update_data.model_dump(exclude_none=True)}

        response = await self._make_request(
            endpoint=endpoint,
            method="PUT",
            data=data,
            response_model=ProductOfferListResponse,
        )

        if not response.results:
            raise EmagAPIError("No offer was updated", status_code=400)

        return response.results[0]

    async def get_offer(self, product_id: str) -> ProductOfferResponse:
        """Get a product offer by ID.

        Args:
            product_id: The ID of the product to retrieve.

        Returns:
            The product offer.

        Raises:
            EmagAPIError: If the offer is not found or another error occurs.

        """
        endpoint = "product_offer/read"
        response = await self._make_request(
            endpoint=endpoint,
            method="GET",
            data={"product_id": product_id},
            response_model=ProductOfferListResponse,
        )

        if not response.results:
            raise EmagAPIError(f"Product offer {product_id} not found", status_code=404)

        return response.results[0]

    async def list_offers(
        self,
        page: int = 1,
        per_page: int = 50,
        filters: ProductOfferFilter | None = None,
    ) -> ProductOfferListResponse:
        """List product offers with optional filtering and pagination.

        Args:
            page: The page number (1-based).
            per_page: Number of items per page (max 100).
            filters: Optional filters to apply.

        Returns:
            A paginated list of product offers.

        """
        endpoint = "product_offer/read"
        params = {
            "page": max(1, page),
            "per_page": min(100, max(1, per_page)),
        }

        if filters:
            params.update(filters.model_dump(exclude_none=True))

        return await self._make_request(
            endpoint=endpoint,
            method="GET",
            data=params,
            response_model=ProductOfferListResponse,
        )

    async def bulk_update_offers(
        self,
        updates: ProductOfferBulkUpdate,
    ) -> ProductOfferBulkResponse:
        """Update multiple product offers in a single batch.

        Args:
            updates: The bulk update data.

        Returns:
            The result of the bulk operation.

        """
        endpoint = "product_offer/save"
        payload_offers: list[dict[str, Any]] = []

        for offer in updates.offers:
            if hasattr(offer, "dict"):
                payload = offer.dict(exclude_none=True)
            else:
                payload = {k: v for k, v in offer.items() if v is not None}

            payload_offers.append(payload)

        return await self._make_request(
            endpoint=endpoint,
            method="POST",
            data={"offers": payload_offers},
            response_model=ProductOfferBulkResponse,
        )

    async def sync_offers(
        self,
        offers: list[dict[str, Any]],
        batch_size: int = 50,
    ) -> ProductOfferSyncResponse:
        """Synchronize multiple offers with eMAG's system.

        This method handles batching, rate limiting, and error handling.

        Args:
            offers: List of offer dictionaries to sync.
            batch_size: Number of offers to process in each batch.

        Returns:
            A sync status object with results.

        """
        sync_id = str(uuid4())
        total_offers = len(offers)
        processed = 0
        results = []

        # Process in batches
        for i in range(0, total_offers, batch_size):
            batch = offers[i : i + batch_size]

            try:
                # Apply rate limiting for bulk operations
                await self.rate_limiter.wait_for_capacity(is_order_endpoint=False)

                # Process the batch
                batch_result = await self.bulk_update_offers(
                    ProductOfferBulkUpdate(offers=batch),
                )
                results.extend(batch_result.results)
                processed += len(batch)

                logger.info(
                    f"Processed batch {i // batch_size + 1}/{(total_offers + batch_size - 1) // batch_size} "
                    f"({processed}/{total_offers} offers)",
                )

            except Exception as e:
                logger.error(f"Error processing batch {i // batch_size + 1}: {e!s}")
                # Add error for each offer in the failed batch
                for offer in batch:
                    results.append(
                        {
                            "product_id": offer.get("product_id", "unknown"),
                            "success": False,
                            "message": f"Batch processing failed: {e!s}",
                            "errors": [{"code": "batch_error", "message": str(e)}],
                        },
                    )

        # Count successes and failures
        success_count = sum(1 for r in results if r.get("success", False))
        failure_count = len(results) - success_count

        return ProductOfferSyncResponse(
            sync_id=sync_id,
            status=(
                ProductOfferSyncStatus.COMPLETED
                if failure_count == 0
                else ProductOfferSyncStatus.FAILED
            ),
            processed_items=processed,
            total_items=total_offers,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            errors=[r for r in results if not r.get("success", False)],
        )

    async def get_sync_status(self, sync_id: str) -> ProductOfferSyncResponse:
        """Get the status of a previously started sync operation.

        Note: This is a placeholder. In a real implementation, you would store
        sync status in a database or cache.

        Args:
            sync_id: The sync operation ID.

        Returns:
            The sync status.

        """
        # Return a basic sync status
        # In production, this should query from database/cache
        return ProductOfferSyncStatus(
            total_offers=0,
            synced_offers=0,
            failed_offers=0,
            last_sync_time=None,
            is_syncing=False,
        )

    async def delete_offer(self, product_id: str) -> bool:
        """Delete a product offer.

        Args:
            product_id: The ID of the product to delete.

        Returns:
            True if the deletion was successful.

        Raises:
            EmagAPIError: If the deletion fails.

        """
        endpoint = "product_offer/delete"
        try:
            await self._make_request(
                endpoint=endpoint,
                method="DELETE",
                data={"product_id": product_id},
                response_model=dict,
            )
            return True
        except EmagAPIError as e:
            if e.status_code == 404:
                logger.warning(
                    f"Product offer {product_id} not found, may have been already deleted",
                )
                return True
            raise
