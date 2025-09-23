#!/usr/bin/env python3
"""Automated sync processes for eMAG integration.

This script handles regular data exchange between MagFlow ERP and eMAG:
- Sync return requests (RMA)
- Sync cancellation requests
- Sync invoice status
- Sync product offers
- Monitor integration health
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict

import schedule
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, and_

from app.models.rma import ReturnRequest, ReturnStatus, EmagReturnIntegration
from app.models.cancellation import CancellationRequest, CancellationStatus, EmagCancellationIntegration
from app.models.invoice import Invoice, InvoiceStatus, EmagInvoiceIntegration
from app.integrations.emag.services import EmagRMAIntegration, EmagCancellationIntegration, EmagInvoiceIntegration
from app.core.config import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/emag_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class EmagSyncManager:
    """Manages automated sync processes with eMAG."""

    def __init__(self):
        self.rma_service = EmagRMAIntegration()
        self.cancellation_service = EmagCancellationIntegration()
        self.invoice_service = EmagInvoiceIntegration()

        # Database setup
        self.engine = create_async_engine(settings.DATABASE_URL)
        self.async_session = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def sync_pending_rmas(self) -> Dict[str, int]:
        """Sync pending return requests with eMAG."""
        logger.info("Starting RMA sync process...")

        async with self.async_session() as session:
            try:
                # Get pending return requests
                stmt = select(ReturnRequest).where(
                    and_(
                        ReturnRequest.status.in_([ReturnStatus.PENDING, ReturnStatus.APPROVED]),
                        ReturnRequest.emag_order_id.is_not(None)
                    )
                ).limit(50)  # Process in batches

                result = await session.execute(stmt)
                pending_rmas = result.scalars().all()

                if not pending_rmas:
                    logger.info("No pending RMAs to sync")
                    return {"processed": 0, "successful": 0, "failed": 0}

                successful = 0
                failed = 0

                for rma in pending_rmas:
                    try:
                        # Check if already synced
                        existing_sync = await session.execute(
                            select(EmagReturnIntegration).where(
                                EmagReturnIntegration.return_request_id == rma.id
                            )
                        )
                        existing = existing_sync.scalar_one_or_none()

                        if existing and existing.emag_return_id:
                            logger.debug(f"RMA {rma.id} already synced with eMAG")
                            continue

                        # Sync with eMAG
                        sync_result = await self.rma_service.create_return_request(rma)

                        if sync_result.get("success"):
                            # Update sync record
                            emag_integration = EmagReturnIntegration(
                                return_request_id=rma.id,
                                emag_return_id=sync_result.get("emag_rma_id"),
                                emag_status=sync_result.get("status", "new"),
                                emag_response=str(sync_result),
                                last_synced_at=datetime.utcnow()
                            )
                            session.add(emag_integration)
                            successful += 1
                            logger.info(f"RMA {rma.id} synced successfully")
                        else:
                            failed += 1
                            logger.error(f"Failed to sync RMA {rma.id}: {sync_result.get('error')}")

                    except Exception as e:
                        failed += 1
                        logger.error(f"Error syncing RMA {rma.id}: {str(e)}")

                await session.commit()
                logger.info(f"RMA sync completed: {successful} successful, {failed} failed")

                return {
                    "processed": len(pending_rmas),
                    "successful": successful,
                    "failed": failed
                }

            except Exception as e:
                logger.error(f"RMA sync error: {str(e)}")
                await session.rollback()
                raise

    async def sync_pending_cancellations(self) -> Dict[str, int]:
        """Sync pending cancellation requests with eMAG."""
        logger.info("Starting cancellation sync process...")

        async with self.async_session() as session:
            try:
                # Get pending cancellation requests
                stmt = select(CancellationRequest).where(
                    and_(
                        CancellationRequest.status.in_([CancellationStatus.PENDING, CancellationStatus.APPROVED]),
                        CancellationRequest.emag_order_id.is_not(None)
                    )
                ).limit(30)  # Process in batches

                result = await session.execute(stmt)
                pending_cancellations = result.scalars().all()

                if not pending_cancellations:
                    logger.info("No pending cancellations to sync")
                    return {"processed": 0, "successful": 0, "failed": 0}

                successful = 0
                failed = 0

                for cancellation in pending_cancellations:
                    try:
                        # Check if already synced
                        existing_sync = await session.execute(
                            select(EmagCancellationIntegration).where(
                                EmagCancellationIntegration.cancellation_request_id == cancellation.id
                            )
                        )
                        existing = existing_sync.scalar_one_or_none()

                        if existing and existing.emag_cancellation_id:
                            logger.debug(f"Cancellation {cancellation.id} already synced with eMAG")
                            continue

                        # Sync with eMAG
                        sync_result = await self.cancellation_service.create_cancellation_request(cancellation)

                        if sync_result.get("success"):
                            # Update sync record
                            emag_integration = EmagCancellationIntegration(
                                cancellation_request_id=cancellation.id,
                                emag_cancellation_id=sync_result.get("emag_cancellation_id"),
                                emag_status=sync_result.get("status", "pending"),
                                emag_response=str(sync_result),
                                last_synced_at=datetime.utcnow()
                            )
                            session.add(emag_integration)
                            successful += 1
                            logger.info(f"Cancellation {cancellation.id} synced successfully")
                        else:
                            failed += 1
                            logger.error(f"Failed to sync cancellation {cancellation.id}: {sync_result.get('error')}")

                    except Exception as e:
                        failed += 1
                        logger.error(f"Error syncing cancellation {cancellation.id}: {str(e)}")

                await session.commit()
                logger.info(f"Cancellation sync completed: {successful} successful, {failed} failed")

                return {
                    "processed": len(pending_cancellations),
                    "successful": successful,
                    "failed": failed
                }

            except Exception as e:
                logger.error(f"Cancellation sync error: {str(e)}")
                await session.rollback()
                raise

    async def sync_pending_invoices(self) -> Dict[str, int]:
        """Sync pending invoices with eMAG."""
        logger.info("Starting invoice sync process...")

        async with self.async_session() as session:
            try:
                # Get pending invoices
                stmt = select(Invoice).where(
                    and_(
                        Invoice.status.in_([InvoiceStatus.DRAFT, InvoiceStatus.ISSUED]),
                        Invoice.customer_id.is_not(None)  # Only sync customer invoices
                    )
                ).limit(25)  # Process in batches

                result = await session.execute(stmt)
                pending_invoices = result.scalars().all()

                if not pending_invoices:
                    logger.info("No pending invoices to sync")
                    return {"processed": 0, "successful": 0, "failed": 0}

                successful = 0
                failed = 0

                for invoice in pending_invoices:
                    try:
                        # Check if already synced
                        existing_sync = await session.execute(
                            select(EmagInvoiceIntegration).where(
                                EmagInvoiceIntegration.invoice_id == invoice.id
                            )
                        )
                        existing = existing_sync.scalar_one_or_none()

                        if existing and existing.emag_invoice_id:
                            logger.debug(f"Invoice {invoice.id} already synced with eMAG")
                            continue

                        # Sync with eMAG
                        sync_result = await self.invoice_service.create_invoice(invoice)

                        if sync_result.get("success"):
                            # Update sync record
                            emag_integration = EmagInvoiceIntegration(
                                invoice_id=invoice.id,
                                emag_invoice_id=sync_result.get("emag_invoice_id"),
                                emag_status=sync_result.get("status", "issued"),
                                emag_invoice_type=invoice.invoice_type.value,
                                emag_response=str(sync_result),
                                last_synced_at=datetime.utcnow()
                            )
                            session.add(emag_integration)
                            successful += 1
                            logger.info(f"Invoice {invoice.id} synced successfully")
                        else:
                            failed += 1
                            logger.error(f"Failed to sync invoice {invoice.id}: {sync_result.get('error')}")

                    except Exception as e:
                        failed += 1
                        logger.error(f"Error syncing invoice {invoice.id}: {str(e)}")

                await session.commit()
                logger.info(f"Invoice sync completed: {successful} successful, {failed} failed")

                return {
                    "processed": len(pending_invoices),
                    "successful": successful,
                    "failed": failed
                }

            except Exception as e:
                logger.error(f"Invoice sync error: {str(e)}")
                await session.rollback()
                raise

    async def run_full_sync(self) -> Dict[str, any]:
        """Run complete sync process for all flows."""
        logger.info("Starting full eMAG sync process...")

        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "rma": {"processed": 0, "successful": 0, "failed": 0},
            "cancellations": {"processed": 0, "successful": 0, "failed": 0},
            "invoices": {"processed": 0, "successful": 0, "failed": 0},
            "total_processed": 0,
            "total_successful": 0,
            "total_failed": 0
        }

        try:
            # Run all sync processes
            results["rma"] = await self.sync_pending_rmas()
            results["cancellations"] = await self.sync_pending_cancellations()
            results["invoices"] = await self.sync_pending_invoices()

            # Calculate totals
            results["total_processed"] = sum(flow["processed"] for flow in results.values() if isinstance(flow, dict))
            results["total_successful"] = sum(flow["successful"] for flow in results.values() if isinstance(flow, dict))
            results["total_failed"] = sum(flow["failed"] for flow in results.values() if isinstance(flow, dict))

            logger.info(f"Full sync completed: {results['total_successful']} successful, {results['total_failed']} failed")

            return results

        except Exception as e:
            logger.error(f"Full sync error: {str(e)}")
            results["error"] = str(e)
            return results


async def run_sync_job():
    """Run the sync job."""
    sync_manager = EmagSyncManager()
    try:
        results = await sync_manager.run_full_sync()

        # Log summary
        logger.info(f"Sync job completed: {results['total_successful']} successful, {results['total_failed']} failed")

        # Send alerts if there are failures
        if results['total_failed'] > 0:
            logger.warning(f"Sync failures detected: {results['total_failed']} failed operations")

        return results

    except Exception as e:
        logger.error(f"Sync job failed: {str(e)}")
        return {"error": str(e)}


def main():
    """Main function to run scheduled sync jobs."""
    logger.info("Starting eMAG sync scheduler...")

    # Schedule sync jobs
    schedule.every(5).minutes.do(lambda: asyncio.run(run_sync_job()))  # Every 5 minutes
    schedule.every().hour.at(":00").do(lambda: asyncio.run(run_sync_job()))  # Every hour
    schedule.every().day.at("02:00").do(lambda: asyncio.run(run_sync_job()))  # Daily at 2 AM

    logger.info("Sync jobs scheduled:")
    logger.info("  - Every 5 minutes")
    logger.info("  - Every hour")
    logger.info("  - Daily at 2:00 AM")

    try:
        while True:
            schedule.run_pending()
            asyncio.run(asyncio.sleep(60))  # Check every minute

    except KeyboardInterrupt:
        logger.info("Sync scheduler stopped by user")
    except Exception as e:
        logger.error(f"Sync scheduler error: {str(e)}")


if __name__ == "__main__":
    main()
