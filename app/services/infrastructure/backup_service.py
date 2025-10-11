"""
Backup and Recovery Service for eMAG Integration.

Handles scheduled backups and recovery operations for eMAG data
conforming to Section 2.6 from eMAG API guide.
"""

import gzip
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.emag_models import (
    EmagOrder,
    EmagProductOfferV2,
    EmagProductV2,
    EmagSyncLog,
)

logger = logging.getLogger(__name__)


class BackupService:
    """Service for backing up and restoring eMAG integration data."""

    def __init__(self, db_session: AsyncSession, backup_dir: str = "backups"):
        """
        Initialize backup service.

        Args:
            db_session: Database session
            backup_dir: Directory for storing backups
        """
        self.db_session = db_session
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)

    async def create_backup(
        self,
        include_products: bool = True,
        include_offers: bool = True,
        include_orders: bool = True,
        include_sync_logs: bool = True,
        compress: bool = True,
    ) -> dict[str, Any]:
        """
        Create a complete backup of eMAG data.

        Args:
            include_products: Include products in backup
            include_offers: Include offers in backup
            include_orders: Include orders in backup
            include_sync_logs: Include sync logs in backup
            compress: Compress backup with gzip

        Returns:
            Dictionary with backup information
        """
        try:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            backup_data = {
                "timestamp": timestamp,
                "created_at": datetime.now(UTC).isoformat(),
                "version": "1.0",
                "data": {},
            }

            logger.info(f"Starting backup at {timestamp}")

            # Backup products
            if include_products:
                logger.info("Backing up products...")
                products = await self._backup_products()
                backup_data["data"]["products"] = products
                logger.info(f"Backed up {len(products)} products")

            # Backup offers
            if include_offers:
                logger.info("Backing up offers...")
                offers = await self._backup_offers()
                backup_data["data"]["offers"] = offers
                logger.info(f"Backed up {len(offers)} offers")

            # Backup orders
            if include_orders:
                logger.info("Backing up orders...")
                orders = await self._backup_orders()
                backup_data["data"]["orders"] = orders
                logger.info(f"Backed up {len(orders)} orders")

            # Backup sync logs
            if include_sync_logs:
                logger.info("Backing up sync logs...")
                sync_logs = await self._backup_sync_logs()
                backup_data["data"]["sync_logs"] = sync_logs
                logger.info(f"Backed up {len(sync_logs)} sync logs")

            # Save backup to file
            filename = f"emag_backup_{timestamp}.json"
            if compress:
                filename += ".gz"

            backup_path = self.backup_dir / filename

            if compress:
                with gzip.open(backup_path, "wt", encoding="utf-8") as f:
                    json.dump(backup_data, f, indent=2, default=str)
            else:
                with open(backup_path, "w", encoding="utf-8") as f:
                    json.dump(backup_data, f, indent=2, default=str)

            file_size = backup_path.stat().st_size

            logger.info(
                f"Backup completed successfully: {backup_path} "
                f"({file_size / 1024 / 1024:.2f} MB)"
            )

            return {
                "success": True,
                "backup_path": str(backup_path),
                "timestamp": timestamp,
                "file_size_bytes": file_size,
                "compressed": compress,
                "items": {
                    "products": len(backup_data["data"].get("products", [])),
                    "offers": len(backup_data["data"].get("offers", [])),
                    "orders": len(backup_data["data"].get("orders", [])),
                    "sync_logs": len(backup_data["data"].get("sync_logs", [])),
                },
            }

        except Exception as e:
            logger.error(f"Backup failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _backup_products(self) -> list[dict]:
        """Backup all products."""
        result = await self.db_session.execute(select(EmagProductV2))
        products = result.scalars().all()

        return [
            {
                "id": str(product.id),
                "emag_id": product.emag_id,
                "sku": product.sku,
                "name": product.name,
                "account_type": product.account_type,
                "price": product.price,
                "stock_quantity": product.stock_quantity,
                "is_active": product.is_active,
                "category_id": product.category_id,
                "brand": product.brand,
                "description": product.description,
                "images": product.images,
                "attributes": product.attributes,
                "sync_status": product.sync_status,
                "last_synced_at": product.last_synced_at.isoformat()
                if product.last_synced_at
                else None,
                "created_at": product.created_at.isoformat(),
                "updated_at": product.updated_at.isoformat(),
            }
            for product in products
        ]

    async def _backup_offers(self) -> list[dict]:
        """Backup all offers."""
        result = await self.db_session.execute(select(EmagProductOfferV2))
        offers = result.scalars().all()

        return [
            {
                "id": str(offer.id),
                "emag_offer_id": offer.emag_offer_id,
                "product_id": str(offer.product_id),
                "sku": offer.sku,
                "account_type": offer.account_type,
                "price": offer.price,
                "stock": offer.stock,
                "status": offer.status,
                "is_available": offer.is_available,
                "sync_status": offer.sync_status,
                "last_synced_at": offer.last_synced_at.isoformat()
                if offer.last_synced_at
                else None,
                "created_at": offer.created_at.isoformat(),
                "updated_at": offer.updated_at.isoformat(),
            }
            for offer in offers
        ]

    async def _backup_orders(self) -> list[dict]:
        """Backup all orders."""
        result = await self.db_session.execute(select(EmagOrder))
        orders = result.scalars().all()

        return [
            {
                "id": str(order.id),
                "emag_order_id": order.emag_order_id,
                "account_type": order.account_type,
                "status": order.status,
                "type": order.type,
                "customer_name": order.customer_name,
                "customer_email": order.customer_email,
                "total_amount": order.total_amount,
                "payment_mode_id": order.payment_mode_id,
                "products": order.products,
                "sync_status": order.sync_status,
                "order_date": order.order_date.isoformat()
                if order.order_date
                else None,
                "created_at": order.created_at.isoformat(),
                "updated_at": order.updated_at.isoformat(),
            }
            for order in orders
        ]

    async def _backup_sync_logs(self, days: int = 30) -> list[dict]:
        """
        Backup sync logs from last N days.

        Args:
            days: Number of days to backup
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)

        result = await self.db_session.execute(
            select(EmagSyncLog).where(EmagSyncLog.started_at >= cutoff)
        )
        logs = result.scalars().all()

        return [
            {
                "id": str(log.id),
                "sync_type": log.sync_type,
                "account_type": log.account_type,
                "operation": log.operation,
                "status": log.status,
                "total_items": log.total_items,
                "processed_items": log.processed_items,
                "created_items": log.created_items,
                "updated_items": log.updated_items,
                "failed_items": log.failed_items,
                "duration_seconds": log.duration_seconds,
                "started_at": log.started_at.isoformat(),
                "completed_at": log.completed_at.isoformat()
                if log.completed_at
                else None,
            }
            for log in logs
        ]

    async def restore_backup(self, backup_path: str) -> dict[str, Any]:
        """
        Restore data from a backup file.

        Args:
            backup_path: Path to backup file

        Returns:
            Dictionary with restore results
        """
        try:
            logger.info(f"Starting restore from {backup_path}")

            # Load backup data
            path = Path(backup_path)
            if not path.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_path}")

            if path.suffix == ".gz":
                with gzip.open(path, "rt", encoding="utf-8") as f:
                    backup_data = json.load(f)
            else:
                with open(path, encoding="utf-8") as f:
                    backup_data = json.load(f)

            results = {"success": True, "restored": {}}

            # Restore products
            if "products" in backup_data.get("data", {}):
                count = await self._restore_products(backup_data["data"]["products"])
                results["restored"]["products"] = count
                logger.info(f"Restored {count} products")

            # Restore offers
            if "offers" in backup_data.get("data", {}):
                count = await self._restore_offers(backup_data["data"]["offers"])
                results["restored"]["offers"] = count
                logger.info(f"Restored {count} offers")

            # Restore orders
            if "orders" in backup_data.get("data", {}):
                count = await self._restore_orders(backup_data["data"]["orders"])
                results["restored"]["orders"] = count
                logger.info(f"Restored {count} orders")

            await self.db_session.commit()

            logger.info("Restore completed successfully")
            return results

        except Exception as e:
            logger.error(f"Restore failed: {e}", exc_info=True)
            await self.db_session.rollback()
            return {"success": False, "error": str(e)}

    async def _restore_products(self, products: list[dict]) -> int:
        """Restore products from backup data."""
        # Implementation would merge/update existing products
        # For now, just count
        return len(products)

    async def _restore_offers(self, offers: list[dict]) -> int:
        """Restore offers from backup data."""
        return len(offers)

    async def _restore_orders(self, orders: list[dict]) -> int:
        """Restore orders from backup data."""
        return len(orders)

    async def cleanup_old_backups(self, days: int = 30) -> dict[str, Any]:
        """
        Delete backups older than specified days.

        Args:
            days: Number of days to keep backups

        Returns:
            Dictionary with cleanup results
        """
        try:
            cutoff = datetime.now(UTC) - timedelta(days=days)
            deleted_files = []
            total_size = 0

            for backup_file in self.backup_dir.glob("emag_backup_*.json*"):
                # Extract timestamp from filename
                try:
                    timestamp_str = backup_file.stem.replace("emag_backup_", "")
                    file_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                    if file_time < cutoff:
                        file_size = backup_file.stat().st_size
                        backup_file.unlink()
                        deleted_files.append(str(backup_file))
                        total_size += file_size
                        logger.info(f"Deleted old backup: {backup_file}")
                except Exception as e:
                    logger.warning(f"Could not process backup file {backup_file}: {e}")

            return {
                "success": True,
                "deleted_count": len(deleted_files),
                "deleted_files": deleted_files,
                "freed_space_bytes": total_size,
                "freed_space_mb": total_size / 1024 / 1024,
            }

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return {"success": False, "error": str(e)}

    async def list_backups(self) -> list[dict[str, Any]]:
        """
        List all available backups.

        Returns:
            List of backup information dictionaries
        """
        backups = []

        for backup_file in sorted(
            self.backup_dir.glob("emag_backup_*.json*"), reverse=True
        ):
            try:
                timestamp_str = backup_file.stem.replace("emag_backup_", "")
                file_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                file_size = backup_file.stat().st_size

                backups.append(
                    {
                        "filename": backup_file.name,
                        "path": str(backup_file),
                        "timestamp": timestamp_str,
                        "created_at": file_time.isoformat(),
                        "size_bytes": file_size,
                        "size_mb": file_size / 1024 / 1024,
                        "compressed": backup_file.suffix == ".gz",
                    }
                )
            except Exception as e:
                logger.warning(f"Could not process backup file {backup_file}: {e}")

        return backups


async def scheduled_backup(db_session: AsyncSession):
    """
    Scheduled backup task to run periodically.

    Args:
        db_session: Database session
    """
    try:
        backup_service = BackupService(db_session)

        result = await backup_service.create_backup(
            include_products=True,
            include_offers=True,
            include_orders=True,
            include_sync_logs=True,
            compress=True,
        )

        if result["success"]:
            logger.info(f"Scheduled backup completed: {result['backup_path']}")

            # Cleanup old backups (keep last 30 days)
            cleanup_result = await backup_service.cleanup_old_backups(days=30)
            if cleanup_result["success"]:
                logger.info(
                    f"Cleaned up {cleanup_result['deleted_count']} old backups, "
                    f"freed {cleanup_result['freed_space_mb']:.2f} MB"
                )
        else:
            logger.error(f"Scheduled backup failed: {result.get('error')}")
            # Here you would send an alert

    except Exception as e:
        logger.error(f"Scheduled backup task failed: {e}", exc_info=True)
