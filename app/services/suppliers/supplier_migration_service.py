"""
Supplier Migration Service
Handles automatic migration from product_supplier_sheets to supplier_products
"""

import logging

from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product_supplier_sheet import ProductSupplierSheet

logger = logging.getLogger(__name__)


class SupplierMigrationService:
    """Service for migrating supplier data between tables"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def migrate_all(self) -> dict[str, int]:
        """
        Migrate all products from product_supplier_sheets to supplier_products

        Returns:
            Dict with migration statistics
        """
        stats = {"total_in_sheets": 0, "migrated": 0, "skipped": 0, "errors": 0}

        try:
            # Count total in sheets
            count_query = select(ProductSupplierSheet).where(
                ProductSupplierSheet.is_active.is_(True)
            )
            count_result = await self.db.execute(count_query)
            stats["total_in_sheets"] = len(count_result.scalars().all())

            # Use efficient bulk migration with raw SQL
            query = text("""
            INSERT INTO app.supplier_products (
                supplier_id, local_product_id, supplier_product_name,
                supplier_product_url, supplier_price, supplier_currency,
                supplier_product_chinese_name, supplier_product_specification,
                import_source, confidence_score, manual_confirmed,
                is_active, is_preferred, created_at, updated_at
            )
            SELECT
                s.id, p.id, pss.supplier_name,
                pss.supplier_url, pss.price_cny, 'CNY',
                pss.supplier_product_chinese_name, pss.supplier_product_specification,
                'google_sheets', 100.0, COALESCE(pss.is_verified, false),
                pss.is_active, COALESCE(pss.is_preferred, false),
                pss.created_at, pss.updated_at
            FROM app.product_supplier_sheets pss
            JOIN app.suppliers s ON s.name = pss.supplier_name
            JOIN app.products p ON p.sku = pss.sku
            WHERE pss.is_active = true
              AND NOT EXISTS (
                SELECT 1 FROM app.supplier_products sp
                WHERE sp.supplier_id = s.id
                  AND sp.local_product_id = p.id
                  AND sp.supplier_product_url = pss.supplier_url
              )
            """)

            result = await self.db.execute(query)
            stats["migrated"] = result.rowcount
            stats["skipped"] = stats["total_in_sheets"] - stats["migrated"]

            logger.info(
                f"Migration completed: {stats['migrated']} products migrated, {stats['skipped']} skipped"
            )

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            stats["errors"] = 1

        return stats

    async def migrate_by_supplier(self, supplier_name: str) -> dict[str, int]:
        """
        Migrate products for a specific supplier

        Args:
            supplier_name: Name of the supplier

        Returns:
            Dict with migration statistics
        """
        stats = {"total_in_sheets": 0, "migrated": 0, "skipped": 0, "errors": 0}

        try:
            # Count total for this supplier
            count_query = select(ProductSupplierSheet).where(
                and_(
                    ProductSupplierSheet.supplier_name == supplier_name,
                    ProductSupplierSheet.is_active.is_(True),
                )
            )
            count_result = await self.db.execute(count_query)
            stats["total_in_sheets"] = len(count_result.scalars().all())

            # Migrate for specific supplier
            query = text("""
            INSERT INTO app.supplier_products (
                supplier_id, local_product_id, supplier_product_name,
                supplier_product_url, supplier_price, supplier_currency,
                supplier_product_chinese_name, supplier_product_specification,
                import_source, confidence_score, manual_confirmed,
                is_active, is_preferred, created_at, updated_at
            )
            SELECT
                s.id, p.id, pss.supplier_name,
                pss.supplier_url, pss.price_cny, 'CNY',
                pss.supplier_product_chinese_name, pss.supplier_product_specification,
                'google_sheets', 100.0, COALESCE(pss.is_verified, false),
                pss.is_active, COALESCE(pss.is_preferred, false),
                pss.created_at, pss.updated_at
            FROM app.product_supplier_sheets pss
            JOIN app.suppliers s ON s.name = pss.supplier_name
            JOIN app.products p ON p.sku = pss.sku
            WHERE pss.is_active = true
              AND s.name = :supplier_name
              AND NOT EXISTS (
                SELECT 1 FROM app.supplier_products sp
                WHERE sp.supplier_id = s.id
                  AND sp.local_product_id = p.id
                  AND sp.supplier_product_url = pss.supplier_url
              )
            """)

            result = await self.db.execute(query, {"supplier_name": supplier_name})
            stats["migrated"] = result.rowcount
            stats["skipped"] = stats["total_in_sheets"] - stats["migrated"]

            logger.info(
                f"Migration for {supplier_name}: {stats['migrated']} products migrated"
            )

        except Exception as e:
            logger.error(f"Migration failed for {supplier_name}: {e}")
            stats["errors"] = 1

        return stats

    async def get_unmigrated_products(
        self, supplier_name: str | None = None, limit: int = 100
    ) -> list[dict]:
        """
        Get products that are in product_supplier_sheets but not in supplier_products

        Args:
            supplier_name: Optional supplier name filter
            limit: Maximum number of results

        Returns:
            List of unmigrated products
        """
        query = text("""
        SELECT
            pss.sku,
            pss.supplier_name,
            pss.supplier_url,
            pss.price_cny,
            pss.supplier_product_chinese_name,
            CASE
                WHEN p.id IS NULL THEN 'Product not found'
                WHEN s.id IS NULL THEN 'Supplier not found'
                ELSE 'Ready to migrate'
            END as status
        FROM app.product_supplier_sheets pss
        LEFT JOIN app.products p ON p.sku = pss.sku
        LEFT JOIN app.suppliers s ON s.name = pss.supplier_name
        WHERE pss.is_active = true
          AND (:supplier_name IS NULL OR pss.supplier_name = :supplier_name)
          AND NOT EXISTS (
            SELECT 1 FROM app.supplier_products sp
            WHERE sp.supplier_id = s.id
              AND sp.local_product_id = p.id
              AND sp.supplier_product_url = pss.supplier_url
          )
        LIMIT :limit
        """)

        result = await self.db.execute(
            query, {"supplier_name": supplier_name, "limit": limit}
        )

        return [dict(row._mapping) for row in result]

    async def validate_migration_readiness(self) -> dict[str, any]:
        """
        Validate if data is ready for migration

        Returns:
            Dict with validation results
        """
        validation = {"ready": True, "issues": [], "stats": {}}

        # Check for products without SKU match
        query = text("""
        SELECT COUNT(*) as count
        FROM app.product_supplier_sheets pss
        LEFT JOIN app.products p ON p.sku = pss.sku
        WHERE pss.is_active = true
          AND p.id IS NULL
        """)
        result = await self.db.execute(query)
        no_product_match = result.scalar()

        if no_product_match > 0:
            validation["issues"].append(
                f"{no_product_match} products in sheets have no matching SKU in products table"
            )

        # Check for suppliers without match
        query = text("""
        SELECT COUNT(*) as count
        FROM app.product_supplier_sheets pss
        LEFT JOIN app.suppliers s ON s.name = pss.supplier_name
        WHERE pss.is_active = true
          AND s.id IS NULL
        """)
        result = await self.db.execute(query)
        no_supplier_match = result.scalar()

        if no_supplier_match > 0:
            validation["issues"].append(
                f"{no_supplier_match} products in sheets have no matching supplier"
            )

        validation["stats"] = {
            "products_without_sku_match": no_product_match,
            "products_without_supplier_match": no_supplier_match,
        }

        if validation["issues"]:
            validation["ready"] = False

        return validation
