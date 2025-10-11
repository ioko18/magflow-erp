"""
Product Relationship Service.

Handles complex product relationships including:
- Variant tracking and management
- PNK consistency validation
- Competition monitoring
- Product genealogy
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.emag_models import EmagProductV2
from app.models.product_relationships import (
    ProductCompetitionLog,
    ProductGenealogy,
    ProductPNKTracking,
    ProductVariant,
)


class ProductRelationshipService:
    """Service for managing product relationships and variants."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================================
    # PNK Consistency Tracking
    # ============================================================================

    async def check_pnk_consistency(self, sku: str) -> dict[str, Any]:
        """
        Check if part_number_key is consistent between MAIN and FBE accounts.

        Returns:
            {
                "sku": "SKU001",
                "is_consistent": True/False,
                "pnk_main": "PNK123",
                "pnk_fbe": "PNK123",
                "status": "consistent/inconsistent/missing",
                "issues": []
            }
        """
        # Get MAIN and FBE products
        query_main = select(EmagProductV2).where(
            and_(EmagProductV2.sku == sku, EmagProductV2.account_type == "main")
        )
        query_fbe = select(EmagProductV2).where(
            and_(EmagProductV2.sku == sku, EmagProductV2.account_type == "fbe")
        )

        result_main = await self.db.execute(query_main)
        result_fbe = await self.db.execute(query_fbe)

        product_main = result_main.scalar_one_or_none()
        product_fbe = result_fbe.scalar_one_or_none()

        pnk_main = product_main.part_number_key if product_main else None
        pnk_fbe = product_fbe.part_number_key if product_fbe else None

        issues = []
        status = "consistent"
        is_consistent = True

        # Check for issues
        if not product_main and not product_fbe:
            status = "missing"
            is_consistent = False
            issues.append("Produsul nu există nici pe MAIN, nici pe FBE")
        elif not product_main:
            status = "missing"
            is_consistent = False
            issues.append("Produsul lipsește pe MAIN")
        elif not product_fbe:
            status = "missing"
            is_consistent = False
            issues.append("Produsul lipsește pe FBE")
        elif not pnk_main and not pnk_fbe:
            status = "missing"
            is_consistent = False
            issues.append("PNK lipsește pe ambele conturi")
        elif not pnk_main:
            status = "missing"
            is_consistent = False
            issues.append("PNK lipsește pe MAIN")
        elif not pnk_fbe:
            status = "missing"
            is_consistent = False
            issues.append("PNK lipsește pe FBE")
        elif pnk_main != pnk_fbe:
            status = "inconsistent"
            is_consistent = False
            issues.append(f"PNK diferit: MAIN={pnk_main}, FBE={pnk_fbe}")

        # Update or create tracking record
        tracking_query = select(ProductPNKTracking).where(ProductPNKTracking.sku == sku)
        tracking_result = await self.db.execute(tracking_query)
        tracking = tracking_result.scalar_one_or_none()

        if tracking:
            tracking.pnk_main = pnk_main
            tracking.pnk_fbe = pnk_fbe
            tracking.is_consistent = is_consistent
            tracking.has_main_pnk = pnk_main is not None
            tracking.has_fbe_pnk = pnk_fbe is not None
            tracking.status = status
            tracking.last_checked = datetime.now(UTC)
            if is_consistent and tracking.resolved_at is None:
                tracking.resolved_at = datetime.now(UTC)
        else:
            tracking = ProductPNKTracking(
                sku=sku,
                pnk_main=pnk_main,
                pnk_fbe=pnk_fbe,
                emag_main_id=product_main.id if product_main else None,
                emag_fbe_id=product_fbe.id if product_fbe else None,
                is_consistent=is_consistent,
                has_main_pnk=pnk_main is not None,
                has_fbe_pnk=pnk_fbe is not None,
                status=status,
            )
            self.db.add(tracking)

        await self.db.commit()

        return {
            "sku": sku,
            "is_consistent": is_consistent,
            "pnk_main": pnk_main,
            "pnk_fbe": pnk_fbe,
            "status": status,
            "issues": issues,
            "has_main": product_main is not None,
            "has_fbe": product_fbe is not None,
        }

    async def get_pnk_inconsistencies(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get all products with PNK inconsistencies."""
        query = (
            select(ProductPNKTracking)
            .where(ProductPNKTracking.is_consistent is False)
            .order_by(ProductPNKTracking.last_checked.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        trackings = result.scalars().all()

        return [
            {
                "sku": t.sku,
                "pnk_main": t.pnk_main,
                "pnk_fbe": t.pnk_fbe,
                "status": t.status,
                "last_checked": t.last_checked.isoformat() if t.last_checked else None,
            }
            for t in trackings
        ]

    # ============================================================================
    # Competition Monitoring
    # ============================================================================

    async def check_competition(
        self, product_id: UUID, account_type: str
    ) -> dict[str, Any]:
        """
        Check if competitors have attached to this product.

        Returns:
            {
                "has_competitors": True/False,
                "number_of_offers": 5,
                "your_rank": 2,
                "requires_action": True/False,
                "recommendation": "Consider re-publishing with different SKU"
            }
        """
        # Get product
        query = select(EmagProductV2).where(EmagProductV2.id == product_id)
        result = await self.db.execute(query)
        product = result.scalar_one_or_none()

        if not product:
            return {"error": "Product not found"}

        number_of_offers = product.number_of_offers or 1
        your_rank = product.buy_button_rank
        has_competitors = number_of_offers > 1

        # Get previous competition log
        prev_log_query = (
            select(ProductCompetitionLog)
            .where(
                and_(
                    ProductCompetitionLog.emag_product_id == product_id,
                    ProductCompetitionLog.account_type == account_type,
                )
            )
            .order_by(ProductCompetitionLog.detected_at.desc())
            .limit(1)
        )

        prev_result = await self.db.execute(prev_log_query)
        prev_log = prev_result.scalar_one_or_none()

        previous_offer_count = prev_log.number_of_offers if prev_log else 1
        new_competitors = max(0, number_of_offers - previous_offer_count)

        # Determine if action is required
        requires_action = False
        recommendation = None

        if has_competitors:
            if number_of_offers >= 5:
                requires_action = True
                recommendation = "Mulți competitori (5+). Recomandăm re-publicare cu SKU/EAN diferit."
            elif your_rank and your_rank > 3:
                requires_action = True
                recommendation = f"Rank scăzut ({your_rank}). Considerați ajustare preț sau re-publicare."
            elif new_competitors >= 2:
                requires_action = True
                recommendation = (
                    f"{new_competitors} competitori noi. Monitorizați situația."
                )

        # Create competition log
        comp_log = ProductCompetitionLog(
            emag_product_id=product_id,
            sku=product.sku,
            part_number_key=product.part_number_key,
            account_type=account_type,
            number_of_offers=number_of_offers,
            your_rank=your_rank,
            best_competitor_price=product.best_offer_sale_price,
            your_price=product.price,
            previous_offer_count=previous_offer_count,
            new_competitors=new_competitors,
            requires_action=requires_action,
        )
        self.db.add(comp_log)
        await self.db.commit()

        return {
            "has_competitors": has_competitors,
            "number_of_offers": number_of_offers,
            "your_rank": your_rank,
            "previous_offer_count": previous_offer_count,
            "new_competitors": new_competitors,
            "requires_action": requires_action,
            "recommendation": recommendation,
            "best_competitor_price": product.best_offer_sale_price,
            "your_price": product.price,
        }

    async def get_products_with_competition(
        self, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get products that have competitors and may require action."""
        query = (
            select(ProductCompetitionLog)
            .where(ProductCompetitionLog.requires_action is True)
            .order_by(ProductCompetitionLog.detected_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        logs = result.scalars().all()

        return [
            {
                "sku": log.sku,
                "account_type": log.account_type,
                "number_of_offers": log.number_of_offers,
                "your_rank": log.your_rank,
                "new_competitors": log.new_competitors,
                "detected_at": log.detected_at.isoformat(),
                "action_taken": log.action_taken,
            }
            for log in logs
        ]

    # ============================================================================
    # Product Variants
    # ============================================================================

    async def create_variant_group(
        self,
        original_sku: str,
        variant_skus: list[str],
        reason: str = "Re-published due to competition",
    ) -> UUID:
        """
        Create a variant group linking multiple SKUs as the same physical product.

        Args:
            original_sku: The original/primary SKU
            variant_skus: List of variant SKUs (re-published versions)
            reason: Why variants were created

        Returns:
            variant_group_id: UUID for the variant group
        """
        variant_group_id = uuid4()

        # Create variant for original product
        original_variant = ProductVariant(
            variant_group_id=variant_group_id,
            sku=original_sku,
            variant_type="original",
            variant_reason=reason,
            is_primary=True,
            is_active=True,
        )
        self.db.add(original_variant)

        # Create variants for re-published products
        for variant_sku in variant_skus:
            variant = ProductVariant(
                variant_group_id=variant_group_id,
                sku=variant_sku,
                variant_type="republished",
                variant_reason=reason,
                is_primary=False,
                is_active=True,
                parent_variant_id=original_variant.id,
            )
            self.db.add(variant)

        await self.db.commit()
        return variant_group_id

    async def get_product_variants(self, sku: str) -> list[dict[str, Any]]:
        """Get all variants of a product."""
        # Find variant group
        query = select(ProductVariant).where(ProductVariant.sku == sku)
        result = await self.db.execute(query)
        variant = result.scalar_one_or_none()

        if not variant:
            return []

        # Get all variants in the same group
        group_query = (
            select(ProductVariant)
            .where(ProductVariant.variant_group_id == variant.variant_group_id)
            .order_by(ProductVariant.created_at)
        )

        group_result = await self.db.execute(group_query)
        variants = group_result.scalars().all()

        return [
            {
                "sku": v.sku,
                "variant_type": v.variant_type,
                "is_primary": v.is_primary,
                "is_active": v.is_active,
                "account_type": v.account_type,
                "has_competitors": v.has_competitors,
                "competitor_count": v.competitor_count,
                "created_at": v.created_at.isoformat(),
                "notes": v.notes,
            }
            for v in variants
        ]

    # ============================================================================
    # Product Genealogy
    # ============================================================================

    async def create_product_family(
        self, root_sku: str, family_name: str, product_type: str = "local"
    ) -> UUID:
        """Create a new product family (genealogy tree)."""
        family_id = uuid4()

        genealogy = ProductGenealogy(
            family_id=family_id,
            family_name=family_name,
            product_id=uuid4(),  # Will be updated with actual product ID
            product_type=product_type,
            sku=root_sku,
            generation=1,
            is_root=True,
            lifecycle_stage="active",
        )
        self.db.add(genealogy)
        await self.db.commit()

        return family_id

    async def add_product_to_family(
        self,
        family_id: UUID,
        sku: str,
        parent_sku: str,
        supersede_reason: str,
        product_type: str = "emag_main",
    ) -> UUID:
        """Add a new generation to a product family."""
        # Get parent
        parent_query = select(ProductGenealogy).where(
            and_(
                ProductGenealogy.family_id == family_id,
                ProductGenealogy.sku == parent_sku,
            )
        )
        parent_result = await self.db.execute(parent_query)
        parent = parent_result.scalar_one_or_none()

        if not parent:
            raise ValueError(f"Parent product {parent_sku} not found in family")

        # Mark parent as superseded
        parent.lifecycle_stage = "superseded"
        parent.superseded_at = datetime.now(UTC)
        parent.supersede_reason = supersede_reason

        # Create new generation
        new_gen = ProductGenealogy(
            family_id=family_id,
            family_name=parent.family_name,
            product_id=uuid4(),
            product_type=product_type,
            sku=sku,
            generation=parent.generation + 1,
            parent_id=parent.id,
            is_root=False,
            lifecycle_stage="active",
        )
        parent.superseded_by_id = new_gen.id

        self.db.add(new_gen)
        await self.db.commit()

        return new_gen.id

    async def get_product_family_tree(self, sku: str) -> dict[str, Any]:
        """Get the complete family tree for a product."""
        # Find product in genealogy
        query = select(ProductGenealogy).where(ProductGenealogy.sku == sku)
        result = await self.db.execute(query)
        product = result.scalar_one_or_none()

        if not product:
            return {"error": "Product not found in genealogy"}

        # Get all family members
        family_query = (
            select(ProductGenealogy)
            .where(ProductGenealogy.family_id == product.family_id)
            .order_by(ProductGenealogy.generation)
        )

        family_result = await self.db.execute(family_query)
        family_members = family_result.scalars().all()

        # Build tree structure
        tree = {
            "family_id": str(product.family_id),
            "family_name": product.family_name,
            "generations": {},
        }

        for member in family_members:
            gen = member.generation
            if gen not in tree["generations"]:
                tree["generations"][gen] = []

            tree["generations"][gen].append(
                {
                    "sku": member.sku,
                    "product_type": member.product_type,
                    "lifecycle_stage": member.lifecycle_stage,
                    "is_root": member.is_root,
                    "superseded_at": member.superseded_at.isoformat()
                    if member.superseded_at
                    else None,
                    "supersede_reason": member.supersede_reason,
                    "created_at": member.created_at.isoformat(),
                }
            )

        return tree
