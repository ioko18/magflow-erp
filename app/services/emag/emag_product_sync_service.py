"""
Comprehensive eMAG Product Synchronization Service.

This service provides robust product synchronization from eMAG marketplace
(both MAIN and FBE accounts) to the local database with the following features:

- Dual-account synchronization (MAIN and FBE)
- Conflict resolution with configurable priority
- Incremental and full sync modes
- Performance optimization with batch processing
- Comprehensive error handling and retry logic
- Detailed sync logging and monitoring
- Historical tracking and audit trail
"""

import asyncio
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ServiceError
from app.core.logging import get_logger
from app.models.emag_models import (
    EmagProductV2,
    EmagSyncLog,
    EmagSyncProgress,
)
from app.services.emag.emag_api_client import EmagApiClient, EmagApiError
from app.telemetry.emag_metrics import (
    record_sync_duration,
    record_sync_error,
    record_sync_products,
    record_sync_timeout,
    set_products_count,
    set_sync_in_progress,
)

logger = get_logger(__name__)


class ConflictResolutionStrategy:
    """Strategies for resolving conflicts between eMAG and local data."""

    EMAG_PRIORITY = "emag_priority"  # eMAG data always wins
    LOCAL_PRIORITY = "local_priority"  # Local data always wins
    NEWEST_WINS = "newest_wins"  # Most recently modified wins
    MANUAL = "manual"  # Requires manual intervention


class SyncMode:
    """Synchronization modes."""

    FULL = "full"  # Sync all products
    INCREMENTAL = "incremental"  # Sync only changed products
    SELECTIVE = "selective"  # Sync specific products


class EmagProductSyncService:
    """Service for synchronizing eMAG products to local database."""

    def __init__(
        self,
        db: AsyncSession,
        account_type: str = "main",
        conflict_strategy: str = ConflictResolutionStrategy.EMAG_PRIORITY,
    ):
        """Initialize the product sync service.

        Args:
            db: Database session
            account_type: 'main', 'fbe', or 'both'
            conflict_strategy: Strategy for resolving conflicts
        """
        self.db = db
        self.account_type = account_type.lower()
        self.conflict_strategy = conflict_strategy
        self._clients: dict[str, EmagApiClient] = {}
        self._sync_log_id: UUID | None = None
        self._sync_stats = {
            "total_processed": 0,
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "failed": 0,
            "errors": [],
        }

    async def __aenter__(self):
        """Async context manager entry."""
        await self._initialize_clients()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_clients()

    async def _initialize_clients(self):
        """Initialize eMAG API clients for required accounts."""
        import os

        accounts = []
        if self.account_type == "both":
            accounts = ["main", "fbe"]
        else:
            accounts = [self.account_type]

        for account in accounts:
            prefix = f"EMAG_{account.upper()}_"
            username = os.getenv(f"{prefix}USERNAME")
            password = os.getenv(f"{prefix}PASSWORD")
            base_url = os.getenv(
                f"{prefix}BASE_URL", "https://marketplace-api.emag.ro/api-3"
            )

            if not username or not password:
                logger.warning(f"Missing credentials for {account} account, skipping")
                continue

            client = EmagApiClient(
                username=username,
                password=password,
                base_url=base_url,
                timeout=90,  # Increased to 90s for large product lists
                max_retries=5,  # Increased retries for better resilience
            )
            await client.start()
            self._clients[account] = client
            logger.info(f"Initialized eMAG API client for {account} account")

    async def _close_clients(self):
        """Close all API clients."""
        for account, client in self._clients.items():
            await client.close()
            logger.info(f"Closed eMAG API client for {account} account")

    async def _fetch_products_with_retry(
        self,
        client: EmagApiClient,
        page: int,
        items_per_page: int,
        filters: dict[str, Any],
        account: str,
        max_retries: int = 5,
    ) -> dict[str, Any] | None:
        """Fetch products with exponential backoff retry logic.

        Returns:
            Response dict on success, None if page should be skipped after max retries
        """
        for attempt in range(max_retries):
            try:
                response = await client.get_products(
                    page=page,
                    items_per_page=items_per_page,
                    filters=filters,
                )
                # Success - reset any error tracking
                if attempt > 0:
                    logger.info(
                        f"Successfully fetched {account} page {page} after {attempt + 1} attempts"
                    )
                return response
            except EmagApiError as e:
                is_last_attempt = attempt >= max_retries - 1

                # Retry on rate limit or server errors
                if e.status_code in [429, 500, 502, 503, 504]:
                    if not is_last_attempt:
                        wait_time = min(2 ** (attempt + 1), 30)
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for {account} page {page} "
                            f"after {wait_time}s (status: {e.status_code})"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        # Last attempt failed - log and return None to skip page
                        logger.error(
                            f"Failed to fetch {account} page {page} after {max_retries} attempts "
                            f"(status: {e.status_code}). Skipping this page."
                        )
                        self._sync_stats["errors"].append(
                            f"{account} page {page}: Failed after {max_retries} retries (HTTP {e.status_code})"
                        )
                        return None
                # Re-raise on non-retryable errors
                raise
            except Exception as e:
                is_last_attempt = attempt >= max_retries - 1
                if not is_last_attempt:
                    wait_time = min(2 ** (attempt + 1), 30)
                    logger.warning(
                        f"Retry {attempt + 1}/{max_retries} for {account} page {page} "
                        f"after error: {type(e).__name__}: {e}"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # Last attempt failed - log and return None to skip page
                    logger.error(
                        f"Failed to fetch {account} page {page} after {max_retries} attempts: {e}. "
                        f"Skipping this page."
                    )
                    self._sync_stats["errors"].append(
                        f"{account} page {page}: {type(e).__name__}: {str(e)[:100]}"
                    )
                    return None

        # Should not reach here, but just in case
        return None

    async def sync_all_products(
        self,
        mode: str = SyncMode.INCREMENTAL,
        max_pages: int | None = None,
        items_per_page: int = 100,
        include_inactive: bool = False,
        timeout_seconds: int = 600,  # 10 minutes default timeout
    ) -> dict[str, Any]:
        """Synchronize all products from eMAG to local database.

        Args:
            mode: Sync mode (full, incremental, selective)
            max_pages: Maximum pages to fetch (None = all)
            items_per_page: Items per page (max 100)
            include_inactive: Whether to include inactive products
            timeout_seconds: Maximum time for sync operation (default 10 minutes)

        Returns:
            Dictionary with sync statistics
        """
        logger.info(
            "Starting product sync: mode=%s, account=%s, max_pages=%s, "
            "include_inactive=%s, timeout=%ss",
            mode,
            self.account_type,
            max_pages,
            include_inactive,
            timeout_seconds,
        )

        # Create sync log
        sync_log = await self._create_sync_log(mode)
        self._sync_log_id = sync_log.id

        # Mark sync as in progress
        set_sync_in_progress(self.account_type, "products", 1)

        start_time = time.time()

        try:
            # Wrap sync in timeout
            await asyncio.wait_for(
                self._sync_all_accounts(
                    mode=mode,
                    max_pages=max_pages,
                    items_per_page=items_per_page,
                    include_inactive=include_inactive,
                ),
                timeout=timeout_seconds,
            )

            # Mark sync as completed
            await self._complete_sync_log(sync_log, "completed")

            # Record metrics
            duration = time.time() - start_time
            record_sync_duration(
                self.account_type, "products", mode, "completed", duration
            )
            record_sync_products(
                self.account_type, "created", self._sync_stats["created"]
            )
            record_sync_products(
                self.account_type, "updated", self._sync_stats["updated"]
            )
            record_sync_products(
                self.account_type, "failed", self._sync_stats["failed"]
            )

            logger.info(f"Product sync completed: {self._sync_stats}")
            return self._sync_stats

        except TimeoutError as timeout_err:
            error_msg = f"Product sync timed out after {timeout_seconds} seconds"
            logger.error(error_msg)
            await self._complete_sync_log(sync_log, "failed", error_msg)

            # Record timeout metrics
            duration = time.time() - start_time
            record_sync_duration(
                self.account_type, "products", mode, "timeout", duration
            )
            record_sync_timeout(self.account_type, "products")

            raise ServiceError(error_msg) from timeout_err
        except Exception as e:
            logger.error(f"Product sync failed: {e}", exc_info=True)
            await self._complete_sync_log(sync_log, "failed", str(e))

            # Record error metrics
            duration = time.time() - start_time
            record_sync_duration(
                self.account_type, "products", mode, "failed", duration
            )
            record_sync_error(self.account_type, "products", type(e).__name__)

            raise ServiceError(f"Product sync failed: {e}") from e
        finally:
            # Mark sync as no longer in progress
            set_sync_in_progress(self.account_type, "products", 0)

    async def _sync_all_accounts(
        self,
        mode: str,
        max_pages: int | None,
        items_per_page: int,
        include_inactive: bool,
    ):
        """Sync products for all configured accounts."""
        for account, client in self._clients.items():
            logger.info(f"Syncing products for {account} account")

            await self._sync_account_products(
                account=account,
                client=client,
                mode=mode,
                max_pages=max_pages,
                items_per_page=items_per_page,
                include_inactive=include_inactive,
            )

    async def _sync_account_products(
        self,
        account: str,
        client: EmagApiClient,
        mode: str,
        max_pages: int | None,
        items_per_page: int,
        include_inactive: bool,
    ):
        """Sync products for a specific account."""
        page = 1
        has_more = True
        skipped_pages = 0
        max_skipped_pages = 3  # Allow skipping up to 3 pages before stopping

        while has_more and (max_pages is None or page <= max_pages):
            try:
                logger.info(f"Fetching page {page} for {account} account")

                # Prepare filters
                filters = {}
                if not include_inactive:
                    filters["status"] = "active"

                # Fetch products from eMAG with retry logic
                response = await self._fetch_products_with_retry(
                    client=client,
                    page=page,
                    items_per_page=items_per_page,
                    filters=filters,
                    account=account,
                    max_retries=5,
                )

                # If response is None, the page was skipped after max retries
                if response is None:
                    skipped_pages += 1
                    logger.warning(
                        f"Skipped page {page} for {account} after retries "
                        f"({skipped_pages}/{max_skipped_pages} pages skipped)"
                    )

                    if skipped_pages >= max_skipped_pages:
                        logger.error(
                            f"Too many skipped pages ({skipped_pages}), stopping sync for {account}"
                        )
                        break

                    # Move to next page
                    page += 1
                    await asyncio.sleep(1)  # Brief pause before next page
                    continue

                # Reset skipped pages counter on success
                skipped_pages = 0

                # Process products
                products = response.get("results", [])
                if not products:
                    logger.info(f"No more products found on page {page} for {account}")
                    break

                # Log progress
                logger.info(
                    f"Processing {len(products)} products from page {page} for {account}"
                )

                await self._process_products_batch(products, account)

                # Check if there are more pages
                # eMAG API doesn't return total_pages, so we continue until we get empty results
                # If we got less than items_per_page, this is likely the last page
                if len(products) < items_per_page:
                    logger.info(
                        f"Last page reached for {account} (got {len(products)} < {items_per_page})"
                    )
                    has_more = False
                else:
                    has_more = True
                    page += 1

                # Small delay to respect rate limits
                await asyncio.sleep(0.2)

            except EmagApiError as e:
                # This should rarely happen now since _fetch_products_with_retry handles most errors
                logger.error(
                    f"Unhandled API error on page {page} for {account}: {e}",
                    exc_info=True,
                )
                self._sync_stats["errors"].append(
                    f"{account} page {page}: Unhandled API error - {str(e)}"
                )
                # Skip to next page
                skipped_pages += 1
                if skipped_pages >= max_skipped_pages:
                    logger.error(
                        f"Too many errors ({skipped_pages}), aborting sync for {account}"
                    )
                    raise
                page += 1
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(
                    f"Unexpected error on page {page} for {account}: {e}",
                    exc_info=True,
                )
                self._sync_stats["errors"].append(
                    f"{account} page {page}: {type(e).__name__}: {str(e)[:100]}"
                )
                # Skip to next page
                skipped_pages += 1
                if skipped_pages >= max_skipped_pages:
                    logger.error(
                        f"Too many errors ({skipped_pages}), aborting sync for {account}"
                    )
                    raise
                page += 1
                await asyncio.sleep(2)

    async def _process_products_batch(
        self,
        products: list[dict[str, Any]],
        account: str,
    ):
        """Process a batch of products from eMAG."""
        for product_data in products:
            try:
                # Use a nested transaction (savepoint) for each product
                async with self.db.begin_nested():
                    await self._sync_single_product(product_data, account)
                    self._sync_stats["total_processed"] += 1

            except Exception as e:
                logger.error(
                    f"Failed to sync product {product_data.get('part_number')}: {e}",
                    exc_info=False,  # Don't log full traceback for each product
                )
                self._sync_stats["failed"] += 1
                error_msg = (
                    f"Product {product_data.get('part_number')}: {str(e)[:200]}"
                )  # Truncate error
                self._sync_stats["errors"].append(error_msg)
                # Continue with next product

        # Flush batch (don't commit yet, endpoint will handle final commit)
        try:
            await self.db.flush()
        except Exception as e:
            logger.error(f"Failed to flush batch: {e}")
            # If flush fails, we need to rollback and continue
            try:
                await self.db.rollback()
            except Exception as rollback_error:
                logger.error(f"Failed to rollback after flush error: {rollback_error}")

    async def _sync_single_product(
        self,
        product_data: dict[str, Any],
        account: str,
    ):
        """Sync a single product to the database."""
        # Extract SKU (part_number in eMAG)
        sku = product_data.get("part_number")
        if not sku:
            logger.warning("Product missing part_number, skipping")
            return

        # Check if product exists
        existing_product = await self._get_existing_product(sku, account)

        product_instance = None
        if existing_product:
            # Update existing product
            should_update = await self._should_update_product(
                existing_product, product_data
            )

            if should_update:
                await self._update_product(existing_product, product_data, account)
                self._sync_stats["updated"] += 1
            else:
                self._sync_stats["unchanged"] += 1
            product_instance = existing_product
        else:
            # Create new product
            product_instance = await self._create_product(product_data, account)
            self._sync_stats["created"] += 1

        # Create/update offer for this product
        if product_instance:
            await self._upsert_offer_from_product_data(
                product_instance, product_data
            )

    async def _get_existing_product(
        self,
        sku: str,
        account: str,
    ) -> EmagProductV2 | None:
        """Get existing product from database."""
        stmt = select(EmagProductV2).where(
            and_(
                EmagProductV2.sku == sku,
                EmagProductV2.account_type == account,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _should_update_product(
        self,
        existing: EmagProductV2,
        new_data: dict[str, Any],
    ) -> bool:
        """Determine if product should be updated based on conflict strategy."""
        if self.conflict_strategy == ConflictResolutionStrategy.EMAG_PRIORITY:
            # Always update with eMAG data
            return True

        elif self.conflict_strategy == ConflictResolutionStrategy.LOCAL_PRIORITY:
            # Never update, keep local data
            return False

        elif self.conflict_strategy == ConflictResolutionStrategy.NEWEST_WINS:
            # Update if eMAG data is newer
            emag_modified = new_data.get("modified")
            if emag_modified and existing.emag_modified_at:
                emag_dt = datetime.fromisoformat(emag_modified.replace("Z", "+00:00"))
                return emag_dt > existing.emag_modified_at
            return True

        else:
            # Default: update
            return True

    async def _create_product(
        self,
        product_data: dict[str, Any],
        account: str,
    ):
        """Create a new product in the database."""
        product = EmagProductV2(
            id=uuid4(),
            emag_id=str(product_data.get("id")),
            sku=product_data.get("part_number"),
            name=product_data.get("name", ""),
            account_type=account,
            source_account=account,
            # Basic information
            description=product_data.get("description"),
            brand=product_data.get("brand"),
            manufacturer=self._safe_string(product_data.get("manufacturer")),
            # Pricing
            price=self._extract_price(product_data),
            currency=product_data.get("currency", "RON"),
            # Inventory - stock is an array of warehouse objects
            stock_quantity=self._extract_stock_quantity(product_data),
            # Categories
            category_id=str(product_data.get("category_id"))
            if product_data.get("category_id")
            else None,
            emag_category_id=str(product_data.get("category", {}).get("id"))
            if product_data.get("category")
            else None,
            emag_category_name=product_data.get("category", {}).get("name"),
            # Status
            is_active=product_data.get("status") == 1,
            status=self._map_status(product_data.get("status")),
            # Images
            images=self._extract_images(product_data),
            images_overwrite=product_data.get("images_overwrite", False),
            main_image_url=self._extract_main_image(product_data),
            # eMAG specific fields
            green_tax=product_data.get("green_tax"),
            supply_lead_time=product_data.get("supply_lead_time"),
            # GPSR fields
            safety_information=product_data.get("safety_information"),
            manufacturer_info=product_data.get("manufacturer"),
            eu_representative=product_data.get("eu_representative"),
            has_manufacturer_info=bool(product_data.get("manufacturer")),
            has_eu_representative=bool(product_data.get("eu_representative")),
            # Characteristics
            emag_characteristics=product_data.get("characteristics"),
            attributes=product_data.get("attributes"),
            specifications=product_data.get("specifications"),
            # Validation - extract status code from array if needed
            validation_status=self._extract_validation_status(product_data),
            validation_status_description=product_data.get(
                "validation_status_description"
            ),
            ownership=product_data.get("ownership"),
            # Competition
            number_of_offers=product_data.get("number_of_offers"),
            buy_button_rank=product_data.get("buy_button_rank"),
            best_offer_sale_price=product_data.get("best_offer_sale_price"),
            # Stock
            general_stock=product_data.get("general_stock"),
            estimated_stock=product_data.get("estimated_stock"),
            # Measurements
            length_mm=product_data.get("length"),
            width_mm=product_data.get("width"),
            height_mm=product_data.get("height"),
            weight_g=product_data.get("weight"),
            # Genius
            genius_eligibility=product_data.get("genius_eligibility"),
            genius_eligibility_type=product_data.get("genius_eligibility_type"),
            genius_computed=product_data.get("genius_computed"),
            # Family
            family_id=product_data.get("family_id"),
            family_name=product_data.get("family_name"),
            family_type_id=product_data.get("family_type_id"),
            # Additional fields
            part_number_key=product_data.get("part_number_key"),
            url=product_data.get("url"),
            warranty=product_data.get("warranty"),
            vat_id=product_data.get("vat_id"),
            ean=product_data.get("ean"),
            # Sync tracking
            sync_status="synced",
            last_synced_at=datetime.now(UTC).replace(tzinfo=None),
            sync_attempts=0,
            # Timestamps
            created_at=datetime.now(UTC).replace(tzinfo=None),
            updated_at=datetime.now(UTC).replace(tzinfo=None),
            emag_created_at=self._parse_datetime(product_data.get("created")),
            emag_modified_at=self._parse_datetime(product_data.get("modified")),
            # Raw data for debugging
            raw_emag_data=product_data,
        )

        self.db.add(product)
        logger.debug(f"Created product: {product.sku}")
        return product

    async def _update_product(
        self,
        product: EmagProductV2,
        product_data: dict[str, Any],
        account: str,
    ):
        """Update an existing product in the database."""
        # Update fields
        product.emag_id = str(product_data.get("id"))
        product.name = product_data.get("name", product.name)
        product.description = product_data.get("description") or product.description
        product.brand = product_data.get("brand") or product.brand
        manufacturer = self._safe_string(product_data.get("manufacturer"))
        if manufacturer:
            product.manufacturer = manufacturer

        # Pricing
        product.price = self._extract_price(product_data) or product.price
        product.currency = product_data.get("currency", product.currency)

        # Inventory - stock is an array of warehouse objects
        stock_quantity = self._extract_stock_quantity(product_data)
        if stock_quantity is not None:
            product.stock_quantity = stock_quantity

        # Categories
        if product_data.get("category_id"):
            product.category_id = str(product_data["category_id"])
        if product_data.get("category"):
            product.emag_category_id = str(product_data["category"].get("id"))
            product.emag_category_name = product_data["category"].get("name")

        # Status
        product.is_active = product_data.get("status") == 1
        product.status = self._map_status(product_data.get("status"))

        # Images
        images = self._extract_images(product_data)
        if images:
            product.images = images
            product.main_image_url = self._extract_main_image(product_data)

        # Update other fields - extract validation status properly
        validation_status = self._extract_validation_status(product_data)
        if validation_status is not None:
            product.validation_status = validation_status
        product.number_of_offers = (
            product_data.get("number_of_offers") or product.number_of_offers
        )
        product.buy_button_rank = (
            product_data.get("buy_button_rank") or product.buy_button_rank
        )

        # Sync tracking
        product.sync_status = "synced"
        product.last_synced_at = datetime.now(UTC).replace(tzinfo=None)
        product.updated_at = datetime.now(UTC).replace(tzinfo=None)
        product.emag_modified_at = self._parse_datetime(product_data.get("modified"))
        product.raw_emag_data = product_data

        logger.debug(f"Updated product: {product.sku}")

    async def _create_sync_log(self, mode: str) -> EmagSyncLog:
        """Create a sync log entry."""
        sync_log = EmagSyncLog(
            id=uuid4(),
            sync_type="products",
            account_type=self.account_type,
            operation=f"{mode}_sync",
            status="running",
            started_at=datetime.now(UTC).replace(tzinfo=None),
        )
        self.db.add(sync_log)
        await self.db.flush()  # Flush instead of commit to keep transaction open
        await self.db.refresh(sync_log)
        return sync_log

    async def _complete_sync_log(
        self,
        sync_log: EmagSyncLog,
        status: str,
        error: str | None = None,
    ):
        """Complete the sync log entry."""
        sync_log.status = status
        completed_at = datetime.now(UTC).replace(tzinfo=None)
        sync_log.completed_at = completed_at

        # Calculate duration safely
        if sync_log.started_at:
            sync_log.duration_seconds = (
                completed_at - sync_log.started_at
            ).total_seconds()
        else:
            sync_log.duration_seconds = 0

        sync_log.total_items = self._sync_stats["total_processed"]
        sync_log.processed_items = self._sync_stats["total_processed"]
        sync_log.created_items = self._sync_stats["created"]
        sync_log.updated_items = self._sync_stats["updated"]
        sync_log.failed_items = self._sync_stats["failed"]

        if error:
            sync_log.errors = [
                {"error": error, "timestamp": datetime.now(UTC).replace(tzinfo=None).isoformat()}
            ]
        elif self._sync_stats["errors"]:
            sync_log.errors = [
                {"error": err, "timestamp": datetime.now(UTC).replace(tzinfo=None).isoformat()}
                for err in self._sync_stats["errors"]
            ]

        # Flush instead of commit (endpoint will handle final commit)
        await self.db.flush()

    async def _update_sync_progress(self, current_page: int, total_pages: int):
        """Update sync progress tracking."""
        if not self._sync_log_id:
            return

        percentage = (current_page / total_pages * 100) if total_pages > 0 else 0

        try:
            # Use a separate savepoint for progress updates to avoid aborting main transaction
            async with self.db.begin_nested():
                # Upsert progress - FIXED: removed created_at column that doesn't exist in table
                stmt = (
                    insert(EmagSyncProgress)
                    .values(
                        id=uuid4(),
                        sync_log_id=self._sync_log_id,
                        current_page=current_page,
                        total_pages=total_pages,
                        current_item=self._sync_stats["total_processed"],
                        percentage_complete=percentage,
                        is_active=True,
                        updated_at=datetime.now(UTC),
                    )
                    .on_conflict_do_update(
                        index_elements=["sync_log_id"],
                        set_={
                            "current_page": current_page,
                            "total_pages": total_pages,
                            "current_item": self._sync_stats["total_processed"],
                            "percentage_complete": percentage,
                            "updated_at": datetime.now(UTC),
                        },
                    )
                )

                await self.db.execute(stmt)
        except Exception as e:
            # Don't let progress tracking errors abort the sync
            logger.warning(f"Failed to update sync progress (non-critical): {e}")

    # Helper methods

    def _extract_price(self, product_data: dict[str, Any]) -> float | None:
        """Extract price from product data."""
        # Try different price fields
        if "sale_price" in product_data:
            return float(product_data["sale_price"])
        elif "price" in product_data:
            return float(product_data["price"])
        elif "recommended_price" in product_data:
            return float(product_data["recommended_price"])
        return None

    def _extract_images(self, product_data: dict[str, Any]) -> list[str] | None:
        """Extract image URLs from product data."""
        images = product_data.get("images", [])
        if isinstance(images, list):
            return [img.get("url") if isinstance(img, dict) else img for img in images]
        return None

    def _extract_main_image(self, product_data: dict[str, Any]) -> str | None:
        """Extract main image URL."""
        images = self._extract_images(product_data)
        return images[0] if images else None

    def _map_status(self, status_code: int | None) -> str:
        """Map eMAG status code to string."""
        status_map = {
            0: "inactive",
            1: "active",
            2: "pending",
        }
        return status_map.get(status_code, "unknown")

    async def _upsert_offer_from_product_data(
        self, product: EmagProductV2, product_data: dict[str, Any]
    ):
        """Create or update offer data from product payload."""
        try:
            from app.models.emag_models import EmagProductOfferV2

            # Extract offer-specific data
            sku = product.sku
            if not sku:
                return

            # Check if offer exists
            stmt = select(EmagProductOfferV2).where(
                and_(
                    EmagProductOfferV2.sku == sku,
                    EmagProductOfferV2.account_type == product.account_type,
                )
            )
            result = await self.db.execute(stmt)
            existing_offer = result.scalar_one_or_none()

            # Convert status to string (eMAG API returns int: 1=active, 0=inactive)
            status_value = product_data.get("status")
            if isinstance(status_value, int):
                status_str = "active" if status_value == 1 else "inactive"
            else:
                status_str = str(status_value) if status_value else "active"

            # Calculate stock values
            stock_value = self._extract_stock_quantity(product_data)

            offer_data = {
                "sku": sku,
                "account_type": product.account_type,
                "product_id": product.id,
                "emag_offer_id": str(product_data.get("id")),
                "price": self._extract_price(product_data),
                "sale_price": self._extract_price(product_data),
                "min_sale_price": product_data.get("min_sale_price"),
                "max_sale_price": product_data.get("max_sale_price"),
                "recommended_price": product_data.get("recommended_price"),
                "currency": product_data.get("currency", "RON"),
                "stock": stock_value,
                "reserved_stock": 0,
                "available_stock": stock_value,
                "status": status_str,
                "is_available": product_data.get("status") == 1
                or product_data.get("status") == "active",
                "visibility": "visible",
                "last_synced_at": datetime.now(UTC).replace(tzinfo=None),
                "sync_status": "synced",
                "sync_attempts": 0,
            }

            if existing_offer:
                # Update existing offer
                for key, value in offer_data.items():
                    if key not in ["sku", "account_type", "sync_attempts"]:
                        setattr(existing_offer, key, value)
                existing_offer.sync_attempts += 1
                existing_offer.updated_at = datetime.now(UTC).replace(tzinfo=None)
                logger.debug(f"Updated offer for SKU {sku} ({product.account_type})")
            else:
                # Create new offer
                new_offer = EmagProductOfferV2(**offer_data)
                self.db.add(new_offer)
                logger.info(f"Created new offer for SKU {sku} ({product.account_type})")

        except Exception as e:
            logger.error(
                "Error upserting offer for SKU %s: %s", sku, str(e), exc_info=True
            )

    def _parse_datetime(self, dt_str: str | None) -> datetime | None:
        """Parse datetime string from eMAG."""
        if not dt_str:
            return None
        try:
            # Handle ISO format with timezone
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    def _extract_stock_quantity(self, product_data: dict[str, Any]) -> int:
        """Extract stock quantity from product data.

        Stock can be:
        - An array of warehouse objects: [{"warehouse_id": 1, "value": 25}]
        - A dict with a value key: {"value": 25}
        - An integer: 25
        """
        stock = product_data.get("stock", 0)

        if isinstance(stock, list) and stock:
            # Sum all warehouse stocks
            return sum(
                item.get("value", 0) if isinstance(item, dict) else 0 for item in stock
            )
        elif isinstance(stock, dict):
            return stock.get("value", 0)
        elif isinstance(stock, (int, float)):
            return int(stock)

        return 0

    def _extract_validation_status(self, product_data: dict[str, Any]) -> int | None:
        """Extract validation status from product data.

        Validation status can be:
        - An integer: 9
        - An array of objects: [{"value": 9, "description": "...", "errors": None}]
        """
        validation_status = product_data.get("validation_status")

        if isinstance(validation_status, list) and validation_status:
            # Extract the value from the first item
            first_item = validation_status[0]
            if isinstance(first_item, dict):
                return first_item.get("value")
        elif isinstance(validation_status, (int, float)):
            return int(validation_status)

        return None

    def _safe_string(self, value: Any) -> str | None:
        """Safely convert a value to string, handling booleans and None."""
        if value is None:
            return None
        if isinstance(value, bool):
            return None  # Don't convert booleans to strings
        if isinstance(value, str):
            return value if value.strip() else None
        return str(value)

    async def get_sync_statistics(self) -> dict[str, Any]:
        """Get synchronization statistics."""
        # Get total products by account
        stmt = select(
            EmagProductV2.account_type,
            func.count(EmagProductV2.id).label("count"),
        ).group_by(EmagProductV2.account_type)

        result = await self.db.execute(stmt)
        products_by_account = {row.account_type: row.count for row in result}

        # Update Prometheus gauges
        for account_type, count in products_by_account.items():
            set_products_count(account_type, count)

        # Get recent sync logs
        stmt = (
            select(EmagSyncLog)
            .where(EmagSyncLog.sync_type == "products")
            .order_by(EmagSyncLog.started_at.desc())
            .limit(10)
        )
        result = await self.db.execute(stmt)
        recent_syncs = result.scalars().all()

        return {
            "products_by_account": products_by_account,
            "total_products": sum(products_by_account.values()),
            "recent_syncs": [
                {
                    "id": str(sync.id),
                    "account_type": sync.account_type,
                    "operation": sync.operation,
                    "status": sync.status,
                    "started_at": sync.started_at.isoformat(),
                    "completed_at": sync.completed_at.isoformat()
                    if sync.completed_at
                    else None,
                    "duration_seconds": sync.duration_seconds,
                    "total_items": sync.total_items,
                    "created_items": sync.created_items,
                    "updated_items": sync.updated_items,
                    "failed_items": sync.failed_items,
                }
                for sync in recent_syncs
            ],
        }
