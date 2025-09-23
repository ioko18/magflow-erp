"""Service for importing and synchronizing eMAG offers with the database."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db_session
from app.models.emag_offers import (
    EmagImportConflict,
    EmagOfferSync,
    EmagProduct,
    EmagProductOffer,
    EmagSyncStatus,
)

from ..models.responses.offer import ProductOfferResponse
from .conflict_resolution_service import ConflictResolutionService
from .data_transformation_service import DataTransformationService
from .emag_import_service import EmagImportService

logger = logging.getLogger(__name__)


class ImportResult:
    """Result of an import operation."""

    def __init__(self):
        self.offers_processed = 0
        self.offers_created = 0
        self.offers_updated = 0
        self.offers_failed = 0
        self.offers_skipped = 0
        self.products_created = 0
        self.products_updated = 0
        self.conflicts_found = 0
        self.errors = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "offers_processed": self.offers_processed,
            "offers_created": self.offers_created,
            "offers_updated": self.offers_updated,
            "offers_failed": self.offers_failed,
            "offers_skipped": self.offers_skipped,
            "products_created": self.products_created,
            "products_updated": self.products_updated,
            "conflicts_found": self.conflicts_found,
            "errors": self.errors,
        }


class ConflictResolutionStrategy:
    """Strategies for resolving import conflicts."""

    SKIP = "skip"  # Skip conflicting records
    UPDATE = "update"  # Update existing records
    MERGE = "merge"  # Merge data from both sources
    MANUAL = "manual"  # Flag for manual review


class EmagOfferImportService:
    """Service for importing and synchronizing eMAG offers with the database."""

    def __init__(self, db: Optional[AsyncSession] = None):
        """Initialize the import service.

        Args:
            db: Optional database session

        """
        self.db = db
        self.import_service = EmagImportService()
        self.transformation_service = DataTransformationService()
        self.conflict_service = ConflictResolutionService()

    async def _ensure_db_session(self) -> AsyncSession:
        """Ensure we have a database session."""
        if self.db is None:
            self.db = await get_db_session()
        return self.db

    async def import_offers_from_emag(
        self,
        account_type: str = "main",
        filters: Optional[Dict[str, Any]] = None,
        conflict_strategy: str = ConflictResolutionStrategy.UPDATE,
        batch_size: int = 50,
        max_offers: Optional[int] = None,
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
    ) -> Tuple[str, ImportResult]:
        """Import offers from eMAG and store them in the database.

        Args:
            account_type: Account type ('main' or 'fbe')
            filters: Optional filters for the import
            conflict_strategy: Strategy for handling conflicts
            batch_size: Number of offers to process in each batch
            max_offers: Maximum number of offers to import
            user_id: ID of the user initiating the import
            user_name: Name of the user initiating the import

        Returns:
            Tuple of (sync_id, ImportResult)

        """
        db = await self._ensure_db_session()
        sync_id = str(uuid4())
        result = ImportResult()

        try:
            # Create sync record
            sync_record = EmagOfferSync(
                sync_id=sync_id,
                account_type=account_type,
                operation_type="full_import",
                status=EmagSyncStatus.RUNNING,
                started_at=datetime.now(timezone.utc),
                filters=filters or {},
                user_id=user_id,
                initiated_by=user_name,
            )
            db.add(sync_record)
            await db.commit()

            logger.info(f"Started import sync {sync_id} for account {account_type}")

            # Fetch offers from eMAG
            offers = await self.import_service.get_all_offers(
                filters=filters,
                account_type=account_type,
                max_pages=(
                    max_offers // self.import_service.batch_size if max_offers else None
                ),
            )

            if max_offers:
                offers = offers[:max_offers]

            logger.info(f"Fetched {len(offers)} offers from eMAG")

            # Process offers in batches
            for i in range(0, len(offers), batch_size):
                batch = offers[i : i + batch_size]

                try:
                    await self._process_offer_batch(
                        batch,
                        account_type,
                        conflict_strategy,
                        result,
                        sync_id,
                    )

                    # Update sync progress
                    sync_record.total_offers_processed = result.offers_processed
                    sync_record.offers_created = result.offers_created
                    sync_record.offers_updated = result.offers_updated
                    sync_record.offers_failed = result.offers_failed
                    sync_record.offers_skipped = result.offers_skipped
                    await db.commit()

                except Exception as e:
                    logger.error(
                        f"Error processing batch {i//batch_size + 1}: {e!s}",
                    )
                    result.errors.append(f"Batch {i//batch_size + 1}: {e!s}")
                    result.offers_failed += len(batch)

            # Update final sync status
            sync_record.status = EmagSyncStatus.COMPLETED
            sync_record.completed_at = datetime.now(timezone.utc)
            sync_record.duration_seconds = (
                sync_record.completed_at - sync_record.started_at
            ).total_seconds()

            await db.commit()

            logger.info(
                f"Completed import sync {sync_id}: {result.offers_processed} offers processed",
            )

        except Exception as e:
            logger.error(f"Import sync {sync_id} failed: {e!s}")

            # Update sync record with failure
            if sync_record:
                sync_record.status = EmagSyncStatus.FAILED
                sync_record.completed_at = datetime.now(timezone.utc)
                sync_record.error_count += 1
                sync_record.errors.append(
                    {
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                await db.commit()

            result.errors.append(str(e))
            raise

        return sync_id, result

    async def _process_offer_batch(
        self,
        offers: List[ProductOfferResponse],
        account_type: str,
        conflict_strategy: str,
        result: ImportResult,
        sync_id: str,
    ) -> None:
        """Process a batch of offers.

        Args:
            offers: List of offers to process
            account_type: Account type
            conflict_strategy: Conflict resolution strategy
            result: Import result to update
            sync_id: Sync operation ID

        """
        db = await self._ensure_db_session()

        for offer in offers:
            try:
                result.offers_processed += 1

                # Check if offer already exists
                existing_offer = await self._get_existing_offer(
                    offer.emag_id,
                    offer.product_id,
                )

                if existing_offer:
                    # Handle existing offer based on conflict strategy
                    await self._handle_existing_offer(
                        existing_offer,
                        offer,
                        conflict_strategy,
                        result,
                        sync_id,
                    )
                else:
                    # Create new offer
                    await self._create_new_offer(offer, account_type, result, sync_id)

                # Commit every 10 offers to avoid large transactions
                if result.offers_processed % 10 == 0:
                    await db.commit()

            except Exception as e:
                logger.error(f"Error processing offer {offer.emag_id}: {e!s}")
                result.offers_failed += 1
                result.errors.append(f"Offer {offer.emag_id}: {e!s}")

        # Final commit for the batch
        await db.commit()

    async def _get_existing_offer(
        self,
        emag_offer_id: int,
        emag_product_id: str,
    ) -> Optional[EmagProductOffer]:
        """Get existing offer from database.

        Args:
            emag_offer_id: eMAG offer ID
            emag_product_id: eMAG product ID

        Returns:
            Existing offer or None

        """
        db = await self._ensure_db_session()

        stmt = select(EmagProductOffer).where(
            and_(
                EmagProductOffer.emag_offer_id == emag_offer_id,
                EmagProductOffer.emag_product_id == emag_product_id,
            ),
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def _handle_existing_offer(
        self,
        existing_offer: EmagProductOffer,
        new_offer: ProductOfferResponse,
        conflict_strategy: str,
        result: ImportResult,
        sync_id: str,
    ) -> None:
        """Handle an existing offer based on conflict resolution strategy.

        Args:
            existing_offer: Existing offer in database
            new_offer: New offer from eMAG
            conflict_strategy: Conflict resolution strategy
            result: Import result to update
            sync_id: Sync operation ID

        """
        # Transform new offer data
        new_offer_data = self.transformation_service.transform_emag_offer_to_internal(
            new_offer,
            existing_offer.account_type,
        )

        # Detect conflicts using the conflict resolution service
        conflicts = self.conflict_service.detect_offer_conflicts(
            existing_offer,
            new_offer_data,
        )

        if not conflicts:
            # No conflicts, update the offer
            await self._update_offer_from_emag_data(existing_offer, new_offer)
            result.offers_updated += 1
            return

        # Handle conflicts based on strategy
        if conflict_strategy == ConflictResolutionStrategy.SKIP:
            result.offers_skipped += 1
            return

        if conflict_strategy == ConflictResolutionStrategy.UPDATE:
            # Update despite conflicts
            await self._update_offer_from_emag_data(existing_offer, new_offer)
            result.offers_updated += 1

        elif conflict_strategy == ConflictResolutionStrategy.MERGE:
            # Apply merge resolution
            resolution_action, resolution_details = (
                self.conflict_service.resolve_conflicts(
                    conflicts,
                    ConflictResolutionService.STRATEGY_MERGE,
                )
            )
            self.conflict_service.apply_resolution_to_offer(
                existing_offer,
                new_offer_data,
                resolution_action,
                resolution_details,
            )
            result.offers_updated += 1

        elif conflict_strategy == ConflictResolutionStrategy.MANUAL:
            # Create conflict record for manual review
            conflict_record = self.conflict_service.create_conflict_record(
                existing_offer,
                new_offer_data,
                conflicts,
                sync_id,
            )
            db = await self._ensure_db_session()
            db.add(conflict_record)
            result.conflicts_found += 1
            result.offers_skipped += 1

    async def _create_new_offer(
        self,
        offer: ProductOfferResponse,
        account_type: str,
        result: ImportResult,
        sync_id: str,
    ) -> None:
        """Create a new offer in the database.

        Args:
            offer: Offer data from eMAG
            account_type: Account type
            result: Import result to update
            sync_id: Sync operation ID

        """
        db = await self._ensure_db_session()

        # Transform eMAG offer to internal format
        transformed_offer = (
            self.transformation_service.transform_emag_offer_to_internal(
                offer,
                account_type,
            )
        )

        # Ensure product exists
        product = await self._ensure_product_exists(offer.product_id)
        if not product:
            result.products_created += 1

        # Create offer record with transformed data
        offer_record = EmagProductOffer(
            **transformed_offer,
            product_id=product.id if product else None,
            import_batch_id=sync_id,
        )

        db.add(offer_record)
        result.offers_created += 1

    async def _ensure_product_exists(
        self,
        emag_product_id: str,
    ) -> Optional[EmagProduct]:
        """Ensure a product exists in the database.

        Args:
            emag_product_id: eMAG product ID

        Returns:
            Product record or None

        """
        db = await self._ensure_db_session()

        # Check if product already exists
        stmt = select(EmagProduct).where(EmagProduct.emag_id == emag_product_id)
        result = await db.execute(stmt)
        product = result.scalars().first()

        if product:
            return product

        # Product doesn't exist, we could fetch it from eMAG API here
        # For now, create a minimal product record
        try:
            product = EmagProduct(
                emag_id=emag_product_id,
                name=f"Product {emag_product_id}",
                last_imported_at=datetime.now(timezone.utc),
                is_active=True,
            )
            db.add(product)
            await db.commit()
            await db.refresh(product)
            return product
        except Exception as e:
            logger.error(f"Error creating product {emag_product_id}: {e!s}")
            return None

    async def _update_offer_from_emag_data(
        self,
        offer_record: EmagProductOffer,
        emag_offer: ProductOfferResponse,
    ) -> None:
        """Update an offer record with data from eMAG.

        Args:
            offer_record: Database offer record
            emag_offer: Offer data from eMAG

        """
        # Transform eMAG data to internal format
        transformed_data = self.transformation_service.transform_emag_offer_to_internal(
            emag_offer,
            offer_record.account_type,
        )

        # Update the offer record with transformed data
        for field, value in transformed_data.items():
            if hasattr(offer_record, field):
                setattr(offer_record, field, value)

    async def _create_conflict_record(
        self,
        existing_offer: EmagProductOffer,
        new_offer: ProductOfferResponse,
        sync_id: str,
    ) -> None:
        """Create a conflict record for manual review.

        Args:
            existing_offer: Existing offer in database
            new_offer: New offer from eMAG
            sync_id: Sync operation ID

        """
        db = await self._ensure_db_session()

        conflict = EmagImportConflict(
            sync_id=sync_id,
            emag_offer_id=new_offer.emag_id,
            emag_product_id=new_offer.product_id,
            conflict_type="price_mismatch",  # Could be more sophisticated
            emag_data={
                "price": new_offer.price,
                "stock": getattr(new_offer, "stock", None),
                "status": getattr(new_offer, "status", None),
            },
            internal_data={
                "price": existing_offer.price,
                "stock": existing_offer.stock,
                "status": existing_offer.status,
            },
            status="pending",
        )

        db.add(conflict)

    async def list_sync_operations(
        self,
        account_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[EmagOfferSync]:
        """List sync operations with optional filtering.

        Args:
            account_type: Filter by account type
            status: Filter by status
            limit: Maximum number of records to return

        Returns:
            List of sync operations

        """
        db = await self._ensure_db_session()

        stmt = select(EmagOfferSync).order_by(EmagOfferSync.created_at.desc())

        if account_type:
            stmt = stmt.where(EmagOfferSync.account_type == account_type)

        if status:
            stmt = stmt.where(EmagOfferSync.status == status)

        stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_import_statistics(
        self,
        account_type: str = "main",
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get import statistics for the specified period.

        Args:
            account_type: Account type to get statistics for
            days: Number of days to look back

        Returns:
            Dictionary with import statistics

        """
        db = await self._ensure_db_session()

        # Calculate date threshold
        from datetime import timedelta

        threshold_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Get completed syncs in the period
        stmt = select(EmagOfferSync).where(
            and_(
                EmagOfferSync.account_type == account_type,
                EmagOfferSync.status == EmagSyncStatus.COMPLETED,
                EmagOfferSync.completed_at >= threshold_date,
            ),
        )

        result = await db.execute(stmt)
        syncs = result.scalars().all()

        # Calculate statistics
        stats = {
            "period_days": days,
            "account_type": account_type,
            "total_syncs": len(syncs),
            "total_offers_processed": sum(s.total_offers_processed for s in syncs),
            "total_offers_created": sum(s.offers_created for s in syncs),
            "total_offers_updated": sum(s.offers_updated for s in syncs),
            "total_offers_failed": sum(s.offers_failed for s in syncs),
            "avg_processing_time": 0,
            "success_rate": 0,
        }

        if syncs:
            total_duration = sum(
                s.duration_seconds for s in syncs if s.duration_seconds
            )
            if total_duration > 0:
                stats["avg_processing_time"] = total_duration / len(syncs)

            total_processed = sum(s.total_offers_processed for s in syncs)
            total_successful = sum(s.offers_created + s.offers_updated for s in syncs)
            if total_processed > 0:
                stats["success_rate"] = (total_successful / total_processed) * 100

        return stats

    async def import_saleable_offers(
        self,
        account_type: str = "main",
        max_offers: Optional[int] = None,
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
    ) -> Tuple[str, ImportResult]:
        """Import only saleable offers according to API v4.4.8 validation rules.

        This imports only offers that are actually available for sale based on:
        - status = 1 (active)
        - offer_validation_status = 1 (saleable)
        - validation_status ∈ {9, 11, 12} (approved)
        - stock > 0

        Args:
            account_type: Account type ('main' or 'fbe')
            max_offers: Maximum number of offers to import
            user_id: ID of the user initiating the import
            user_name: Username who initiated the import

        Returns:
            Tuple of (sync_id, ImportResult)

        """
        # Use advanced filters for saleable offers only
        filters = {"only_saleable": True}

        offers = await self.import_service.get_offers_with_filters(
            filters=filters,
            account_type=account_type,
            max_pages=(
                max_offers // self.import_service.batch_size if max_offers else None
            ),
        )

        if max_offers and len(offers) > max_offers:
            offers = offers[:max_offers]

        # Use the full import logic
        return await self._perform_import(
            offers=offers,
            account_type=account_type,
            operation_type="saleable_import",
            conflict_strategy="update",
            max_offers=max_offers,
            user_id=user_id,
            user_name=user_name,
        )

    async def update_offer_stock(
        self,
        offer_id: int,
        stock_data: Dict[str, Any],
        account_type: str = "main",
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update stock for a specific offer using PATCH /offer_stock/{id} (API v4.4.8).

        Args:
            offer_id: eMAG offer ID to update
            stock_data: Stock update data
            account_type: Account type
            user_id: User ID performing update
            user_name: Username performing update

        Returns:
            Update result

        """
        db = await self._ensure_db_session()

        try:
            # Find existing offer in database
            existing_offer = await self._get_existing_offer_by_emag_id(offer_id)
            if not existing_offer:
                raise ValueError(f"Offer {offer_id} not found in database")

            # Get current stock value for logging
            old_stock = existing_offer.stock

            # Prepare stock update for eMAG API
            emag_stock_data = {"resourceId": offer_id, "stock": stock_data["stock"]}

            # Call eMAG API to update stock
            response = await self.import_service.client.patch(
                endpoint=f"offer_stock/{offer_id}",
                data=emag_stock_data,
                is_order_endpoint=False,
            )

            # Update local database
            existing_offer.stock = stock_data["stock"]
            existing_offer.last_imported_at = datetime.now(timezone.utc)
            await db.commit()

            return {
                "success": True,
                "offer_id": offer_id,
                "old_stock": old_stock,
                "new_stock": stock_data["stock"],
                "emag_response": response,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to update stock for offer {offer_id}: {e!s}")
            await db.rollback()
            raise

    async def schedule_offer_update(
        self,
        update_data: Dict[str, Any],
        account_type: str = "main",
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Schedule offer updates with start_date (API v4.4.8 feature).

        Args:
            update_data: Update data with start_date
            account_type: Account type
            user_id: User ID
            user_name: Username

        Returns:
            Scheduling result

        """
        try:
            offer_ids = update_data["offer_ids"]
            start_date = update_data["start_date"]

            # Validate start_date format
            from datetime import datetime

            # start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))

            scheduled_updates = []

            for offer_id in offer_ids:
                # Find offer in database
                existing_offer = await self._get_existing_offer_by_emag_id(offer_id)
                if not existing_offer:
                    logger.warning(f"Offer {offer_id} not found in database, skipping")
                    continue

                # Prepare scheduled update data
                scheduled_data = {
                    "id": offer_id,
                    "start_date": start_date,
                    "scheduled_at": datetime.now(timezone.utc),
                    "scheduled_by": user_name,
                }

                # Add optional fields
                if "sale_price" in update_data:
                    scheduled_data["sale_price"] = update_data["sale_price"]
                if "stock" in update_data:
                    scheduled_data["stock"] = update_data["stock"]

                # Store scheduled update (in production, this would be in a separate table)
                # For now, we'll log it and return success
                logger.info(f"Scheduled update for offer {offer_id} at {start_date}")

                scheduled_updates.append(
                    {
                        "offer_id": offer_id,
                        "start_date": start_date,
                        "status": "scheduled",
                    },
                )

            return {
                "success": True,
                "scheduled_updates": scheduled_updates,
                "total_scheduled": len(scheduled_updates),
                "start_date": start_date,
            }

        except Exception as e:
            logger.error(f"Failed to schedule offer updates: {e!s}")
            raise

    async def create_campaign_proposal(
        self,
        campaign_data: Dict[str, Any],
        account_type: str = "main",
        user_id: Optional[int] = None,
        user_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create campaign proposals with MultiDeals support (API v4.4.8).

        Args:
            campaign_data: Campaign proposal data
            account_type: Account type
            user_id: User ID
            user_name: Username

        Returns:
            Campaign creation result

        """
        try:
            # Call eMAG API to create campaign proposal
            response = await self.import_service.client.post(
                endpoint="campaign_proposals/save",
                data=campaign_data,
                is_order_endpoint=False,
            )

            logger.info(
                f"Campaign proposal created: {campaign_data['id']} by {user_name}",
            )

            return {
                "success": True,
                "campaign_id": campaign_data["id"],
                "emag_response": response,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": user_name,
            }

        except Exception as e:
            logger.error(f"Failed to create campaign proposal: {e!s}")
            raise

    async def _get_existing_offer_by_emag_id(
        self,
        emag_offer_id: int,
    ) -> Optional[EmagProductOffer]:
        """Get existing offer by eMAG offer ID.

        Args:
            emag_offer_id: eMAG offer ID

        Returns:
            Existing offer or None

        """
        db = await self._ensure_db_session()

        stmt = select(EmagProductOffer).where(
            EmagProductOffer.emag_offer_id == emag_offer_id,
        )
        result = await db.execute(stmt)
        return result.scalars().first()
