"""Service for importing offers from eMAG Marketplace."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any, Callable

from ..client import EmagAPIClient
from ..exceptions import EmagAPIError
from ..models.responses.offer import ProductOfferListResponse, ProductOfferResponse
from ..rate_limiting import RateLimiter

logger = logging.getLogger(__name__)


class EmagImportService:
    """Service for importing product offers from eMAG Marketplace."""

    def __init__(
        self,
        http_client: EmagAPIClient | None = None,
        rate_limiter: RateLimiter | None = None,
    ):
        """Initialize the import service.

        Args:
            http_client: eMAG API client instance
            rate_limiter: Rate limiter instance

        """
        self.http_client = http_client or EmagAPIClient()
        self.rate_limiter = rate_limiter
        self.batch_size = 100  # Maximum items per page for eMAG API

    async def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: dict[str, Any] | None = None,
        response_model: Any | None = None,
        retries: int = 3,
    ) -> Any:
        """Make an HTTP request with rate limiting and retry logic.

        Args:
            endpoint: The API endpoint to call.
            method: The HTTP method to use (GET, POST, PUT, DELETE).
            data: The request payload.
            response_model: The Pydantic model to parse the response into.
            retries: Number of retry attempts.

        Returns:
            The parsed response.

        Raises:
            EmagAPIError: If the request fails after all retries.

        """
        last_error = None

        for attempt in range(retries):
            try:
                # Apply rate limiting for reading operations
                if self.rate_limiter:
                    await self.rate_limiter.wait_for_capacity(is_order_endpoint=False)

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

    async def get_offer_by_id(self, offer_id: int) -> ProductOfferResponse | None:
        """Get a single offer by ID from eMAG.

        Args:
            offer_id: The eMAG offer ID

        Returns:
            ProductOfferResponse if found, None otherwise

        """
        try:
            endpoint = "product_offer/read"
            response = await self._make_request(
                endpoint=endpoint,
                method="GET",
                data={"id": offer_id},
                response_model=ProductOfferListResponse,
            )

            if response.results and len(response.results) > 0:
                return response.results[0]

            return None

        except EmagAPIError as e:
            if e.status_code == 404:
                logger.info(f"Offer {offer_id} not found in eMAG")
                return None
            raise

    async def get_offers_by_product(
        self,
        product_id: str,
    ) -> list[ProductOfferResponse]:
        """Get all offers for a specific product from eMAG.

        Args:
            product_id: The eMAG product ID

        Returns:
            List of ProductOfferResponse objects

        """
        endpoint = "product_offer/read"
        response = await self._make_request(
            endpoint=endpoint,
            method="GET",
            data={"product_id": product_id},
            response_model=ProductOfferListResponse,
        )

        return response.results or []

    async def list_offers(
        self,
        page: int = 1,
        per_page: int = 100,
        filters: dict[str, Any] | None = None,
        account_type: str = "main",
    ) -> ProductOfferListResponse:
        """List offers from eMAG with optional filtering and pagination.

        Args:
            page: Page number (1-based)
            per_page: Number of items per page (max 100)
            filters: Optional filters to apply
            account_type: Account type ('main' or 'fbe')

        Returns:
            ProductOfferListResponse with paginated results

        """
        # Validate parameters
        per_page = min(per_page, 100)
        per_page = max(per_page, 1)
        page = max(page, 1)

        # Prepare request data
        data = {
            "page": page,
            "per_page": per_page,
        }

        # Add filters if provided
        if filters:
            data.update(filters)

        # Add account type filter
        if account_type and account_type != "main":
            data["account_type"] = account_type

        endpoint = "product_offer/read"
        response = await self._make_request(
            endpoint=endpoint,
            method="GET",
            data=data,
            response_model=ProductOfferListResponse,
        )

        return response

    async def get_all_offers(
        self,
        filters: dict[str, Any] | None = None,
        account_type: str = "main",
        max_pages: int | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[ProductOfferResponse]:
        """Get all offers from eMAG, handling pagination automatically.

        Args:
            filters: Optional filters to apply
            account_type: Account type ('main' or 'fbe')
            max_pages: Maximum number of pages to fetch (None for all)
            progress_callback: Optional callback for progress reporting

        Returns:
            List of all ProductOfferResponse objects

        """
        all_offers = []
        page = 1

        while True:
            try:
                # Get one page of offers
                response = await self.list_offers(
                    page=page,
                    per_page=self.batch_size,
                    filters=filters,
                    account_type=account_type,
                )

                # Add offers to our collection
                if response.results:
                    all_offers.extend(response.results)

                    # Report progress if callback provided
                    if progress_callback:
                        progress_callback(page, len(response.results), len(all_offers))

                # Check if we've reached the last page
                if not response.results or len(response.results) < self.batch_size:
                    break

                # Check max pages limit
                if max_pages and page >= max_pages:
                    logger.info(f"Reached maximum page limit: {max_pages}")
                    break

                page += 1

            except Exception as e:
                logger.error(f"Error fetching page {page}: {e!s}")
                # Continue with next page or break depending on error type
                if isinstance(e, EmagAPIError) and e.status_code in [
                    429,
                    500,
                    502,
                    503,
                    504,
                ]:
                    # Retryable errors - wait and continue
                    await asyncio.sleep(5)
                    continue
                # Non-retryable error - break
                break

        logger.info(f"Fetched {len(all_offers)} offers from eMAG")
        return all_offers

    async def get_offers_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime | None = None,
        account_type: str = "main",
        max_pages: int | None = None,
    ) -> list[ProductOfferResponse]:
        """Get offers modified within a date range.

        Args:
            start_date: Start date for the range
            end_date: End date for the range (defaults to now)
            account_type: Account type ('main' or 'fbe')
            max_pages: Maximum number of pages to fetch

        Returns:
            List of ProductOfferResponse objects modified in the date range

        """
        if end_date is None:
            end_date = datetime.now(UTC)

        # Convert to timestamps
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())

        filters = {
            "updated_after": start_timestamp,
            "updated_before": end_timestamp,
        }

        return await self.get_all_offers(
            filters=filters,
            account_type=account_type,
            max_pages=max_pages,
        )

    async def get_recent_offers(
        self,
        hours: int = 24,
        account_type: str = "main",
    ) -> list[ProductOfferResponse]:
        """Get offers modified in the last N hours.

        Args:
            hours: Number of hours to look back
            account_type: Account type ('main' or 'fbe')

        Returns:
            List of recently modified ProductOfferResponse objects

        """
        from datetime import timedelta

        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(hours=hours)

        return await self.get_offers_by_date_range(
            start_date=start_date,
            end_date=end_date,
            account_type=account_type,
        )

    async def get_recently_modified_offers(
        self,
        since_timestamp: int,
        account_type: str = "main",
        max_pages: int | None = None,
    ) -> list[ProductOfferResponse]:
        """Get offers modified since a specific timestamp.

        Args:
            since_timestamp: Unix timestamp to get offers modified after
            account_type: Account type ('main' or 'fbe')
            max_pages: Maximum number of pages to fetch

        Returns:
            List of recently modified ProductOfferResponse objects

        """
        filters = {
            "updated_after": since_timestamp,
        }

        return await self.get_all_offers(
            filters=filters,
            max_pages=max_pages,
            progress_callback=self._log_progress,
        )

    async def get_offers_with_filters(
        self,
        filters: dict[str, Any],
        account_type: str = "main",
        max_pages: int | None = None,
    ) -> list[ProductOfferResponse]:
        """Get offers with advanced filters according to API v4.4.8.

        Args:
            filters: Advanced filters dictionary
            account_type: Account type ('main' or 'fbe')
            max_pages: Maximum number of pages to fetch

        Returns:
            List of ProductOfferResponse objects with applied filters

        """
        # Build query parameters according to API v4.4.8
        params = {}

        # Basic filters
        if "id" in filters:
            params["id"] = filters["id"]
        if "status" in filters:
            params["status"] = filters["status"]
        if "part_number" in filters:
            params["part_number"] = filters["part_number"]
        if "part_number_key" in filters:
            params["part_number_key"] = filters["part_number_key"]

        # Stock filters
        if "general_stock" in filters:
            params["general_stock"] = filters["general_stock"]
        if "estimated_stock" in filters:
            params["estimated_stock"] = filters["estimated_stock"]

        # Validation status filters (critical for API v4.4.8)
        if "offer_validation_status" in filters:
            params["offer_validation_status"] = filters["offer_validation_status"]
        if "validation_status" in filters:
            params["validation_status"] = filters["validation_status"]
        if "translation_validation_status" in filters:
            params["translation_validation_status"] = filters[
                "translation_validation_status"
            ]

        # Date filters for incremental sync
        if "modified_after" in filters:
            params["modified_after"] = filters["modified_after"]
        if "created_after" in filters:
            params["created_after"] = filters["created_after"]

        # Saleable offers filter (most important for production)
        if filters.get("only_saleable", False):
            # Only get offers that are actually saleable
            params.update(
                {
                    "status": 1,  # Active
                    "offer_validation_status": 1,  # Saleable
                    "validation_status": [9, 11, 12],  # Approved statuses
                    "general_stock": {"gt": 0},  # Stock > 0
                },
            )

        return await self.get_all_offers(
            filters={"query": params} if params else {},
            account_type=account_type,
            max_pages=max_pages,
            progress_callback=self._log_progress,
        )

    async def get_offers_by_price_range(
        self,
        min_price: float | None = None,
        max_price: float | None = None,
        account_type: str = "main",
        max_pages: int | None = None,
    ) -> list[ProductOfferResponse]:
        """Get offers within a price range.

        Args:
            min_price: Minimum price (optional)
            max_price: Maximum price (optional)
            account_type: Account type ('main' or 'fbe')
            max_pages: Maximum number of pages to fetch

        Returns:
            List of ProductOfferResponse objects within price range

        """
        filters = {}

        if min_price is not None:
            filters["min_price"] = min_price
        if max_price is not None:
            filters["max_price"] = max_price

        return await self.get_all_offers(
            filters=filters,
            account_type=account_type,
            max_pages=max_pages,
            progress_callback=self._log_progress,
        )

    async def get_offers_by_availability(
        self,
        available: bool = True,
        account_type: str = "main",
        max_pages: int | None = None,
    ) -> list[ProductOfferResponse]:
        """Get offers by availability status.

        Args:
            available: Whether to get available (True) or unavailable (False) offers
            account_type: Account type ('main' or 'fbe')
            max_pages: Maximum number of pages to fetch

        Returns:
            List of ProductOfferResponse objects with specified availability

        """
        filters = {
            "is_available": "1" if available else "0",
        }

        return await self.get_all_offers(
            filters=filters,
            account_type=account_type,
            max_pages=max_pages,
            progress_callback=self._log_progress,
        )

    def _log_progress(self, page: int, offers_count: int, total_offers: int) -> None:
        """Log progress during data fetching.

        Args:
            page: Current page number
            offers_count: Number of offers in current page
            total_offers: Total offers fetched so far

        """
        logger.info(
            f"Fetched page {page}: {offers_count} offers (total: {total_offers})",
        )

    async def get_changed_offers_since(
        self,
        last_sync_timestamp: int,
        account_type: str = "main",
        change_types: list[str] | None = None,
    ) -> dict[str, list[ProductOfferResponse]]:
        """Get offers that have changed since last sync, categorized by change type.

        Args:
            last_sync_timestamp: Timestamp of last successful sync
            account_type: Account type ('main' or 'fbe')
            change_types: Types of changes to look for (if None, gets all changes)

        Returns:
            Dictionary with change types as keys and lists of offers as values

        """
        # Get recently modified offers
        modified_offers = await self.get_recently_modified_offers(
            since_timestamp=last_sync_timestamp,
            account_type=account_type,
        )

        if not change_types:
            return {"all_changes": modified_offers}

        # For more sophisticated change detection, we would need to compare
        # with previously stored data. For now, return all modified offers.
        changes = {}
        for change_type in change_types:
            if change_type == "price_changes":
                # This would require comparing with stored prices
                changes[change_type] = modified_offers
            elif change_type == "stock_changes":
                # This would require comparing with stored stock levels
                changes[change_type] = modified_offers
            elif change_type == "status_changes":
                # This would require comparing with stored status
                changes[change_type] = modified_offers
            else:
                changes[change_type] = modified_offers

        return changes

    async def get_sync_summary(
        self,
        account_type: str = "main",
    ) -> dict[str, Any]:
        """Get a summary of current offer data for sync planning.

        Args:
            account_type: Account type ('main' or 'fbe')

        Returns:
            Dictionary with sync summary information

        """
        # Get a sample of offers to analyze
        sample_offers = await self.list_offers(
            page=1,
            per_page=100,
            account_type=account_type,
        )

        summary = {
            "account_type": account_type,
            "sample_size": len(sample_offers.results) if sample_offers.results else 0,
            "total_pages": getattr(sample_offers, "total_pages", None),
            "total_offers": getattr(sample_offers, "total_count", None),
            "last_updated": None,
            "status_distribution": {},
            "price_distribution": {
                "min": None,
                "max": None,
                "avg": None,
            },
        }

        if sample_offers.results:
            # Calculate status distribution
            status_counts = {}
            prices = []

            for offer in sample_offers.results:
                # Status distribution
                status = getattr(offer, "status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1

                # Price collection
                if hasattr(offer, "price") and offer.price is not None:
                    prices.append(offer.price)

                # Track last updated
                if hasattr(offer, "updated_at") and offer.updated_at:
                    if (
                        summary["last_updated"] is None
                        or offer.updated_at > summary["last_updated"]
                    ):
                        summary["last_updated"] = offer.updated_at

            summary["status_distribution"] = status_counts

            # Calculate price statistics
            if prices:
                summary["price_distribution"] = {
                    "min": min(prices),
                    "max": max(prices),
                    "avg": sum(prices) / len(prices),
                }

        return summary
