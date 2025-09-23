"""Service to synchronize eMAG offers into the ERP database.

The service uses :class:`app.emag.client.EmagAPIWrapper` (an async wrapper around the
full-featured ``EmagClient``) to fetch offers from the eMAG API and then upserts
them into the existing SQLAlchemy models defined in ``app.models.emag_offers``.

Key responsibilities:
* Fetch all offers (paginated) using ``fetch_all_offers``.
* Transform the raw JSON payload into ``EmagProduct`` and ``EmagProductOffer``
  instances.
* Perform an ``INSERT … ON CONFLICT DO UPDATE`` (upsert) for both product and
  offer tables.
* Record a sync operation in ``EmagOfferSync`` for audit / monitoring.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.dialects.postgresql import insert

from app.db import get_db
from app.emag.client import EmagAPIWrapper
from app.models.emag_offers import (
    EmagOfferSync,
    EmagProduct,
    EmagProductOffer,
)

log = logging.getLogger(__name__)


class OfferSyncService:
    """High‑level service that orchestrates the import of eMAG offers.

    The service is deliberately async so it can be used from FastAPI background
    tasks or a CLI script executed with ``asyncio.run``.
    """

    def __init__(self, per_page: int = 100) -> None:
        self.per_page = per_page
        self.sync_id = f"sync-{uuid.uuid4().hex[:8]}"
        self.started_at = datetime.utcnow()

    async def _record_sync_start(self) -> EmagOfferSync:
        """Create a ``EmagOfferSync`` row marking the start of the operation."""
        async for session in get_db():
            try:
                sync = EmagOfferSync(
                    sync_id=self.sync_id,
                    account_type="main",
                    operation_type="full_import",
                    status="running",
                    started_at=self.started_at,
                )
                session.add(sync)
                await session.commit()
                await session.refresh(sync)
                return sync
            except Exception:
                pass

    async def _record_sync_end(
        self,
        sync: EmagOfferSync,
        success: bool,
        processed: int,
    ) -> None:
        """Update the ``EmagOfferSync`` row with final statistics."""
        async for session in get_db():
            try:
                sync.completed_at = datetime.utcnow()
                sync.duration_seconds = (
                    sync.completed_at - sync.started_at
                ).total_seconds()
                sync.total_offers_processed = processed
                sync.status = "completed" if success else "failed"
                await session.commit()
            except Exception:
                pass

    async def _upsert_product(
        self,
        session,
        product_data: Dict[str, Any],
    ) -> EmagProduct:
        """Upsert a product (``EmagProduct``) using PostgreSQL ``ON CONFLICT``.

        Returns the persisted ``EmagProduct`` instance (with ``id`` populated).
        """
        stmt = insert(EmagProduct).values(
            emag_id=product_data["emag_id"],
            name=product_data.get("name"),
            description=product_data.get("description"),
            part_number=product_data.get("part_number"),
            emag_category_id=product_data.get("emag_category_id"),
            emag_brand_id=product_data.get("emag_brand_id"),
            emag_category_name=product_data.get("emag_category_name"),
            emag_brand_name=product_data.get("emag_brand_name"),
            characteristics=product_data.get("characteristics", {}),
            images=product_data.get("images", []),
            is_active=product_data.get("is_active", True),
            last_imported_at=datetime.utcnow(),
            raw_data=product_data,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[EmagProduct.emag_id],
            set_={
                "name": stmt.excluded.name,
                "description": stmt.excluded.description,
                "part_number": stmt.excluded.part_number,
                "emag_category_id": stmt.excluded.emag_category_id,
                "emag_brand_id": stmt.excluded.emag_brand_id,
                "emag_category_name": stmt.excluded.emag_category_name,
                "emag_brand_name": stmt.excluded.emag_brand_name,
                "characteristics": stmt.excluded.characteristics,
                "images": stmt.excluded.images,
                "is_active": stmt.excluded.is_active,
                "last_imported_at": datetime.utcnow(),
                "raw_data": stmt.excluded.raw_data,
            },
        )
        await session.execute(stmt)
        # Retrieve the product to get its primary key
        result = await session.execute(
            EmagProduct.__table__.select().where(
                EmagProduct.emag_id == product_data["emag_id"],
            ),
        )
        product = result.fetchone()
        return product

    async def _upsert_offer(
        self,
        session,
        offer_data: Dict[str, Any],
        product_id: int,
    ) -> EmagProductOffer:
        """Upsert an ``EmagProductOffer`` linked to the given ``product_id``."""
        stmt = insert(EmagProductOffer).values(
            emag_product_id=offer_data.get("emag_id"),
            emag_offer_id=offer_data.get("id"),
            product_id=product_id,
            price=offer_data.get("price"),
            sale_price=offer_data.get("sale_price"),
            currency=offer_data.get("currency", "RON"),
            stock=offer_data.get("general_stock", 0),
            stock_status=offer_data.get("stock_status"),
            handling_time=offer_data.get("handling_time", [{}])[0].get("value"),
            status=offer_data.get("status"),
            is_available=offer_data.get("is_available", True),
            is_visible=offer_data.get("is_visible", True),
            vat_rate=offer_data.get("vat_rate"),
            vat_included=offer_data.get("vat_included", True),
            warehouse_id=offer_data.get("warehouse_id"),
            warehouse_name=offer_data.get("warehouse_name"),
            account_type=offer_data.get("account_type", "main"),
            warranty=offer_data.get("warranty"),
            last_imported_at=datetime.utcnow(),
            raw_data=offer_data,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[EmagProductOffer.emag_offer_id],
            set_={
                "price": stmt.excluded.price,
                "sale_price": stmt.excluded.sale_price,
                "currency": stmt.excluded.currency,
                "stock": stmt.excluded.stock,
                "stock_status": stmt.excluded.stock_status,
                "handling_time": stmt.excluded.handling_time,
                "status": stmt.excluded.status,
                "is_available": stmt.excluded.is_available,
                "is_visible": stmt.excluded.is_visible,
                "vat_rate": stmt.excluded.vat_rate,
                "vat_included": stmt.excluded.vat_included,
                "warehouse_id": stmt.excluded.warehouse_id,
                "warehouse_name": stmt.excluded.warehouse_name,
                "account_type": stmt.excluded.account_type,
                "warranty": stmt.excluded.warranty,
                "last_imported_at": datetime.utcnow(),
                "raw_data": stmt.excluded.raw_data,
            },
        )
        await session.execute(stmt)
        # Return the persisted row (optional, not used currently)
        result = await session.execute(
            EmagProductOffer.__table__.select().where(
                EmagProductOffer.emag_offer_id == offer_data.get("id"),
            ),
        )
        return result.fetchone()

    async def sync_all_offers(self) -> None:
        """Main entry point – fetch all offers and persist them.

        The method records a sync start/end row, logs progress and returns when
        the operation is complete.
        """
        log.info("Starting eMAG offers sync", sync_id=self.sync_id)
        sync_record = await self._record_sync_start()
        processed = 0
        success = True

        try:
            async with EmagAPIWrapper() as client:
                offers: List[Dict[str, Any]] = await client.fetch_all_offers(
                    per_page=self.per_page,
                )
                log.info("Fetched %d offers from eMAG", len(offers))

                async for session in get_db():
                    try:
                        for offer in offers:
                            # Build a minimal product representation
                            product_payload = {
                                "emag_id": offer.get("product_id"),
                                "name": offer.get("name"),
                                "description": offer.get("description"),
                                "part_number": offer.get("part_number"),
                                "emag_category_id": offer.get("category_id"),
                                "emag_brand_id": offer.get("brand_id"),
                                "emag_category_name": offer.get("category_name"),
                                "emag_brand_name": offer.get("brand_name"),
                                "characteristics": offer.get("characteristics", []),
                                "images": offer.get("images", []),
                                "is_active": offer.get("status") == 1,
                            }
                            product_row = await self._upsert_product(
                                session,
                                product_payload,
                            )
                            product_id = (
                                product_row["id"]
                                if isinstance(product_row, dict)
                                else product_row.id
                            )
                            await self._upsert_offer(session, offer, product_id)
                            processed += 1
                    except Exception:
                        pass
        except Exception as exc:
            log.exception("Error during eMAG sync: %s", exc)
            success = False
        finally:
            await self._record_sync_end(sync_record, success, processed)
            log.info(
                "eMAG sync finished",
                sync_id=self.sync_id,
                success=success,
                processed=processed,
            )


# Helper for CLI usage
async def main() -> None:
    service = OfferSyncService(per_page=100)
    await service.sync_all_offers()


if __name__ == "__main__":
    asyncio.run(main())
