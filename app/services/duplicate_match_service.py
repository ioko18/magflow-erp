"""
Duplicate Match Detection and Management Service.

This service handles detection and resolution of duplicate supplier product matches,
where multiple supplier products are matched to the same local product.
"""

import logging
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.supplier import Supplier, SupplierProduct

logger = logging.getLogger(__name__)


class DuplicateMatchService:
    """Service for managing duplicate supplier product matches."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_duplicate_matches(
        self, supplier_id: int | None = None, min_duplicates: int = 2
    ) -> list[dict[str, Any]]:
        """
        Find local products that have multiple supplier products matched.

        Args:
            supplier_id: Optional supplier ID to filter by
            min_duplicates: Minimum number of matches to consider duplicate

        Returns:
            List of duplicate match groups
        """
        # Query to find duplicates
        query = (
            select(
                SupplierProduct.local_product_id,
                func.count(SupplierProduct.id).label("match_count"),
            )
            .where(SupplierProduct.local_product_id.isnot(None))
            .group_by(SupplierProduct.local_product_id)
            .having(func.count(SupplierProduct.id) >= min_duplicates)
        )

        if supplier_id:
            query = query.where(SupplierProduct.supplier_id == supplier_id)

        result = await self.db.execute(query)
        duplicate_groups = result.all()

        logger.info(f"Found {len(duplicate_groups)} products with duplicate matches")

        # Get details for each duplicate group
        duplicates_details = []

        for local_product_id, match_count in duplicate_groups:
            # Get local product info
            local_product_query = select(Product).where(Product.id == local_product_id)
            local_result = await self.db.execute(local_product_query)
            local_product = local_result.scalar_one_or_none()

            if not local_product:
                continue

            # Get all supplier products matched to this local product
            sp_query = (
                select(SupplierProduct, Supplier.name)
                .join(Supplier, SupplierProduct.supplier_id == Supplier.id)
                .where(SupplierProduct.local_product_id == local_product_id)
                .order_by(
                    SupplierProduct.confidence_score.desc(),
                    SupplierProduct.created_at.desc(),
                )
            )

            sp_result = await self.db.execute(sp_query)
            supplier_products = sp_result.all()

            matches = []
            for sp, supplier_name in supplier_products:
                matches.append(
                    {
                        "supplier_product_id": sp.id,
                        "supplier_id": sp.supplier_id,
                        "supplier_name": supplier_name,
                        "supplier_product_name": sp.supplier_product_name,
                        "supplier_product_chinese_name": sp.supplier_product_chinese_name,
                        "supplier_product_url": sp.supplier_product_url,
                        "confidence_score": sp.confidence_score,
                        "manual_confirmed": sp.manual_confirmed,
                        "import_source": sp.import_source,
                        "created_at": sp.created_at.isoformat()
                        if sp.created_at
                        else None,
                    }
                )

            duplicates_details.append(
                {
                    "local_product_id": local_product_id,
                    "local_product_sku": local_product.sku,
                    "local_product_name": local_product.name,
                    "local_product_chinese_name": local_product.chinese_name,
                    "match_count": match_count,
                    "matches": matches,
                }
            )

        return duplicates_details

    async def resolve_duplicates_keep_best(
        self, local_product_id: int, strategy: str = "highest_confidence"
    ) -> dict[str, Any]:
        """
        Resolve duplicates by keeping only the best match.

        Args:
            local_product_id: Local product ID with duplicates
            strategy: Resolution strategy
                - "highest_confidence": Keep match with highest confidence
                - "most_recent": Keep most recent match
                - "manual_confirmed": Keep manually confirmed match
                - "google_sheets": Prefer Google Sheets import

        Returns:
            Resolution result
        """
        # Get all matches
        sp_query = select(SupplierProduct).where(
            SupplierProduct.local_product_id == local_product_id
        )

        if strategy == "highest_confidence":
            sp_query = sp_query.order_by(
                SupplierProduct.confidence_score.desc(),
                SupplierProduct.created_at.desc(),
            )
        elif strategy == "most_recent":
            sp_query = sp_query.order_by(SupplierProduct.created_at.desc())
        elif strategy == "manual_confirmed":
            sp_query = sp_query.order_by(
                SupplierProduct.manual_confirmed.desc(),
                SupplierProduct.confidence_score.desc(),
            )
        elif strategy == "google_sheets":
            # Prefer google_sheets, then highest confidence
            sp_query = sp_query.order_by(
                (SupplierProduct.import_source == "google_sheets").desc(),
                SupplierProduct.confidence_score.desc(),
            )

        result = await self.db.execute(sp_query)
        all_matches = result.scalars().all()

        if len(all_matches) <= 1:
            return {
                "status": "no_duplicates",
                "kept_count": len(all_matches),
                "removed_count": 0,
            }

        # Keep first (best) match
        best_match = all_matches[0]
        matches_to_remove = all_matches[1:]

        # Unmatch the duplicates
        for sp in matches_to_remove:
            sp.local_product_id = None
            sp.manual_confirmed = False
            sp.confidence_score = None

        await self.db.commit()

        logger.info(
            f"Resolved duplicates for product {local_product_id}: "
            f"kept {best_match.id}, removed {len(matches_to_remove)} matches"
        )

        return {
            "status": "resolved",
            "local_product_id": local_product_id,
            "kept_match": {
                "supplier_product_id": best_match.id,
                "supplier_id": best_match.supplier_id,
                "confidence_score": best_match.confidence_score,
                "import_source": best_match.import_source,
            },
            "removed_count": len(matches_to_remove),
            "removed_ids": [sp.id for sp in matches_to_remove],
        }

    async def resolve_all_duplicates(
        self,
        supplier_id: int | None = None,
        strategy: str = "highest_confidence",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Resolve all duplicate matches in bulk.

        Args:
            supplier_id: Optional supplier ID to filter by
            strategy: Resolution strategy
            dry_run: If True, don't save changes

        Returns:
            Bulk resolution statistics
        """
        duplicates = await self.find_duplicate_matches(supplier_id=supplier_id)

        if dry_run:
            return {
                "status": "dry_run",
                "total_duplicates": len(duplicates),
                "total_matches_to_remove": sum(
                    d["match_count"] - 1 for d in duplicates
                ),
                "duplicates": duplicates[:10],  # Preview first 10
            }

        resolved_count = 0
        total_removed = 0

        for duplicate in duplicates:
            result = await self.resolve_duplicates_keep_best(
                local_product_id=duplicate["local_product_id"], strategy=strategy
            )

            if result["status"] == "resolved":
                resolved_count += 1
                total_removed += result["removed_count"]

        return {
            "status": "completed",
            "total_duplicates": len(duplicates),
            "resolved_count": resolved_count,
            "total_matches_removed": total_removed,
            "strategy_used": strategy,
        }

    async def get_duplicate_statistics(
        self, supplier_id: int | None = None
    ) -> dict[str, Any]:
        """
        Get statistics about duplicate matches.

        Args:
            supplier_id: Optional supplier ID to filter by

        Returns:
            Statistics dictionary
        """
        # Total products with duplicates
        duplicates_query = select(
            func.count(func.distinct(SupplierProduct.local_product_id))
        ).where(
            SupplierProduct.local_product_id.isnot(None),
            SupplierProduct.local_product_id.in_(
                select(SupplierProduct.local_product_id)
                .where(SupplierProduct.local_product_id.isnot(None))
                .group_by(SupplierProduct.local_product_id)
                .having(func.count(SupplierProduct.id) > 1)
            ),
        )

        if supplier_id:
            duplicates_query = duplicates_query.where(
                SupplierProduct.supplier_id == supplier_id
            )

        duplicates_result = await self.db.execute(duplicates_query)
        products_with_duplicates = duplicates_result.scalar()

        # Total duplicate matches (extra matches beyond first)
        total_matches_query = (
            select(
                SupplierProduct.local_product_id,
                func.count(SupplierProduct.id).label("count"),
            )
            .where(SupplierProduct.local_product_id.isnot(None))
            .group_by(SupplierProduct.local_product_id)
            .having(func.count(SupplierProduct.id) > 1)
        )

        if supplier_id:
            total_matches_query = total_matches_query.where(
                SupplierProduct.supplier_id == supplier_id
            )

        total_result = await self.db.execute(total_matches_query)
        duplicate_groups = total_result.all()

        total_extra_matches = sum(count - 1 for _, count in duplicate_groups)

        # Max duplicates for a single product
        max_duplicates = max((count for _, count in duplicate_groups), default=0)

        return {
            "products_with_duplicates": products_with_duplicates,
            "total_extra_matches": total_extra_matches,
            "max_duplicates_per_product": max_duplicates,
            "average_duplicates": round(
                sum(count for _, count in duplicate_groups) / len(duplicate_groups), 2
            )
            if duplicate_groups
            else 0,
        }

    async def prevent_duplicate_match(
        self, supplier_product_id: int, local_product_id: int
    ) -> dict[str, Any]:
        """
        Check if matching would create a duplicate and prevent it.

        Args:
            supplier_product_id: Supplier product ID to match
            local_product_id: Local product ID to match to

        Returns:
            Validation result
        """
        # Check if local product already has matches
        existing_query = select(SupplierProduct).where(
            and_(
                SupplierProduct.local_product_id == local_product_id,
                SupplierProduct.id != supplier_product_id,
            )
        )

        result = await self.db.execute(existing_query)
        existing_matches = result.scalars().all()

        if existing_matches:
            return {
                "allowed": False,
                "reason": "duplicate_match",
                "message": f"Product already has {len(existing_matches)} match(es)",
                "existing_matches": [
                    {
                        "supplier_product_id": sp.id,
                        "supplier_id": sp.supplier_id,
                        "confidence_score": sp.confidence_score,
                        "import_source": sp.import_source,
                    }
                    for sp in existing_matches
                ],
            }

        return {
            "allowed": True,
            "message": "No duplicate detected",
        }
