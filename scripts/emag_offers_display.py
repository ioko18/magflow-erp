# Refactored eMAG offers display using async client and structured logging

"""CLI script to synchronize eMAG offers into the ERP database.

The original script performed a single synchronous request and printed a huge
human‑readable dump. This version uses the async ``OfferSyncService`` defined in
``app.emag.services.offer_sync_service`` to fetch *all* offers, upsert them into the
database, and log progress with the project's structured logger.
"""

import asyncio
import logging
import os

from dotenv import load_dotenv

from app.emag.services.offer_sync_service import OfferSyncService
from app.logging_setup import setup_logging

# ---------------------------------------------------------------------------
# Configuration & logging
# ---------------------------------------------------------------------------
load_dotenv()
setup_logging(service_name="emag_sync", log_level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger(__name__)

async def main() -> None:
    """Entry point – run the full eMAG offer import.

    The service records a sync operation in the ``emag_offer_syncs`` table,
    fetches all offers (paginated) and upserts them. Detailed progress is emitted
    via the structured logger.
    """
    per_page = int(os.getenv("EMAG_SYNC_PER_PAGE", "100"))
    service = OfferSyncService(per_page=per_page)
    await service.sync_all_offers()

if __name__ == "__main__":
    asyncio.run(main())
