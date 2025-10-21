"""
Chinese Name Synchronization Service for Supplier Products

This service handles automatic synchronization of Chinese product names
from supplier_product_name to supplier_product_chinese_name field.
"""

import logging
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.chinese_text_utils import (
    contains_chinese,
    normalize_chinese_name,
)
from app.models.supplier import SupplierProduct

logger = logging.getLogger(__name__)


class ChineseNameSyncService:
    """Service for synchronizing Chinese product names."""

    def __init__(self, db: AsyncSession):
        """Initialize sync service.

        Args:
            db: Database session
        """
        self.db = db

    async def sync_supplier_products(
        self, supplier_id: int | None = None
    ) -> dict[str, Any]:
        """Synchronize Chinese names for supplier products.

        Args:
            supplier_id: Optional supplier ID to sync only for specific supplier.
                        If None, syncs all suppliers.

        Returns:
            Dictionary with sync statistics
        """
        try:
            # Build query
            query = select(SupplierProduct).where(
                SupplierProduct.supplier_product_chinese_name.is_(None)
            )

            if supplier_id:
                query = query.where(SupplierProduct.supplier_id == supplier_id)

            result = await self.db.execute(query)
            products = result.scalars().all()

            synced_count = 0
            skipped_count = 0
            synced_products = []

            for product in products:
                # Check if supplier_product_name contains Chinese characters
                if contains_chinese(product.supplier_product_name):
                    # Normalize and copy to chinese_name field
                    normalized_name = normalize_chinese_name(
                        product.supplier_product_name
                    )
                    if normalized_name:
                        product.supplier_product_chinese_name = normalized_name
                        synced_count += 1
                        synced_products.append(
                            {
                                "id": product.id,
                                "supplier_id": product.supplier_id,
                                "name": (
                                    normalized_name[:50] + "..."
                                    if len(normalized_name) > 50
                                    else normalized_name
                                ),
                            }
                        )
                else:
                    skipped_count += 1

            if synced_count > 0:
                await self.db.commit()
                logger.info(
                    f"Synchronized {synced_count} Chinese names for supplier {supplier_id or 'all'}"
                )

            return {
                "status": "success",
                "synced_count": synced_count,
                "skipped_count": skipped_count,
                "synced_products": synced_products[:10],  # Return first 10 as sample
            }

        except Exception as e:
            logger.error(
                f"Error synchronizing Chinese names for supplier {supplier_id}: {str(e)}",
                exc_info=True,
            )
            await self.db.rollback()
            raise

    async def sync_single_product(
        self, product: SupplierProduct
    ) -> bool:
        """Synchronize Chinese name for a single product.

        Args:
            product: SupplierProduct instance to sync

        Returns:
            True if synced, False if skipped
        """
        if product.supplier_product_chinese_name:
            # Already has Chinese name
            return False

        if not contains_chinese(product.supplier_product_name):
            # No Chinese characters in name
            return False

        normalized_name = normalize_chinese_name(product.supplier_product_name)
        if normalized_name:
            product.supplier_product_chinese_name = normalized_name
            return True

        return False
