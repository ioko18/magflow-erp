"""
Stock Synchronization Service.

Handles intelligent stock synchronization between MAIN and FBE accounts,
with special handling for products with competition.

Key Features:
- Automatic stock balancing between MAIN and FBE
- Competition-aware stock allocation
- Weekly offer updates (eMAG best practice)
- Stock transfer recommendations
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.emag_models import EmagProductV2
from app.services.product.product_relationship_service import ProductRelationshipService


class StockSyncService:
    """Service for intelligent stock synchronization."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.relationship_service = ProductRelationshipService(db)

    async def analyze_stock_distribution(self, sku: str) -> dict[str, Any]:
        """
        Analyze stock distribution for a product across MAIN and FBE.

        Returns recommendations for stock allocation based on:
        - Competition level
        - Current stock levels
        - Sales velocity (if available)
        - Buy button rank
        """
        # Get products
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

        if not product_main and not product_fbe:
            return {"error": "Product not found on any account"}

        # Current situation
        stock_main = product_main.stock_quantity if product_main else 0
        stock_fbe = product_fbe.stock_quantity if product_fbe else 0
        total_stock = stock_main + stock_fbe

        offers_main = product_main.number_of_offers if product_main else 1
        offers_fbe = product_fbe.number_of_offers if product_fbe else 1

        rank_main = product_main.buy_button_rank if product_main else None
        rank_fbe = product_fbe.buy_button_rank if product_fbe else None

        # Competition analysis
        has_competition_main = offers_main > 1
        has_competition_fbe = offers_fbe > 1

        # Recommendations
        recommendations = []
        priority = "normal"
        action_required = False

        # Case 1: Zero stock on MAIN with competition
        if stock_main == 0 and has_competition_main and stock_fbe > 0:
            priority = "high"
            action_required = True
            recommendations.append(
                {
                    "type": "stock_transfer",
                    "from_account": "fbe",
                    "to_account": "main",
                    "suggested_amount": min(stock_fbe, 10),  # Transfer up to 10 units
                    "reason": "MAIN has 0 stock with competition - losing buy button",
                    "impact": "Regain buy button on MAIN account",
                }
            )

        # Case 2: Low stock on account with competition
        if stock_main > 0 and stock_main < 5 and has_competition_main:
            priority = "medium"
            action_required = True
            recommendations.append(
                {
                    "type": "stock_alert",
                    "account": "main",
                    "current_stock": stock_main,
                    "reason": "Low stock with competition - risk of losing buy button",
                    "suggested_action": "Increase stock or transfer from FBE",
                }
            )

        # Case 3: Better rank on one account - allocate more stock there
        if rank_main and rank_fbe:
            if rank_main < rank_fbe and stock_main < stock_fbe:
                recommendations.append(
                    {
                        "type": "stock_rebalance",
                        "reason": (
                            f"MAIN has better rank ({rank_main} vs {rank_fbe}) "
                            "but less stock"
                        ),
                        "suggested_action": (
                            f"Transfer {min(stock_fbe // 2, 10)} units "
                            "from FBE to MAIN"
                        ),
                    }
                )
            elif rank_fbe < rank_main and stock_fbe < stock_main:
                recommendations.append(
                    {
                        "type": "stock_rebalance",
                        "reason": (
                            f"FBE has better rank ({rank_fbe} vs {rank_main}) "
                            "but less stock"
                        ),
                        "suggested_action": (
                            f"Transfer {min(stock_main // 2, 10)} units "
                            "from MAIN to FBE"
                        ),
                    }
                )
        # Case 4: No competition on one account - can reduce stock there
        if not has_competition_fbe and has_competition_main and stock_fbe > 10:
            recommendations.append(
                {
                    "type": "stock_optimization",
                    "reason": "FBE has no competition - can safely reduce stock there",
                    "suggested_action": (
                        "Keep minimum stock on FBE, transfer excess to MAIN "
                        f"(up to {stock_fbe - 10} units)"
                    ),
                }
            )

        # Case 5: Weekly offer update needed (eMAG best practice)
        if product_main and product_main.last_synced_at:
            days_since_sync = (datetime.now(UTC) - product_main.last_synced_at).days
            if days_since_sync >= 7:
                recommendations.append(
                    {
                        "type": "offer_update",
                        "account": "main",
                        "reason": (
                            f"Last sync {days_since_sync} days ago - "
                            "weekly update recommended"
                        ),
                        "suggested_action": "Update offer even if nothing changed",
                    }
                )

        if product_fbe and product_fbe.last_synced_at:
            days_since_sync = (datetime.now(UTC) - product_fbe.last_synced_at).days
            if days_since_sync >= 7:
                recommendations.append(
                    {
                        "type": "offer_update",
                        "account": "fbe",
                        "reason": (
                            f"Last sync {days_since_sync} days ago - "
                            "weekly update recommended"
                        ),
                        "suggested_action": "Update offer even if nothing changed",
                    }
                )

        return {
            "sku": sku,
            "current_situation": {
                "stock_main": stock_main,
                "stock_fbe": stock_fbe,
                "total_stock": total_stock,
                "offers_main": offers_main,
                "offers_fbe": offers_fbe,
                "rank_main": rank_main,
                "rank_fbe": rank_fbe,
                "has_competition_main": has_competition_main,
                "has_competition_fbe": has_competition_fbe,
            },
            "recommendations": recommendations,
            "priority": priority,
            "action_required": action_required,
        }

    async def get_products_needing_stock_sync(
        self, limit: int = 50
    ) -> list[dict[str, Any]]:
        """
        Get products that need stock synchronization attention.

        Criteria:
        - Zero stock on one account with competition
        - Imbalanced stock distribution
        - Offers not updated in 7+ days
        """
        # Query products with potential issues
        query = (
            select(EmagProductV2)
            .where(
                or_(
                    # Zero stock with competition
                    and_(
                        EmagProductV2.stock_quantity == 0,
                        EmagProductV2.number_of_offers > 1,
                    ),
                    # Not synced in 7+ days
                    EmagProductV2.last_synced_at
                    < datetime.now(UTC) - timedelta(days=7),
                )
            )
            .limit(limit)
        )

        result = await self.db.execute(query)
        products = result.scalars().all()

        issues = []
        for product in products:
            issue_type = []

            if product.stock_quantity == 0 and product.number_of_offers > 1:
                issue_type.append("zero_stock_with_competition")

            if (
                product.last_synced_at
                and (datetime.now(UTC) - product.last_synced_at).days >= 7
            ):
                issue_type.append("needs_weekly_update")

            issues.append(
                {
                    "sku": product.sku,
                    "account_type": product.account_type,
                    "stock": product.stock_quantity,
                    "offers": product.number_of_offers,
                    "rank": product.buy_button_rank,
                    "last_synced": product.last_synced_at.isoformat()
                    if product.last_synced_at
                    else None,
                    "issues": issue_type,
                }
            )

        return issues

    async def suggest_stock_transfer(
        self, sku: str, from_account: str, to_account: str, amount: int
    ) -> dict[str, Any]:
        """
        Generate stock transfer suggestion with validation.

        Returns transfer plan with:
        - Current stock levels
        - Proposed transfer amount
        - Impact analysis
        - Validation checks
        """
        # Get current stock
        query_from = select(EmagProductV2).where(
            and_(EmagProductV2.sku == sku, EmagProductV2.account_type == from_account)
        )
        query_to = select(EmagProductV2).where(
            and_(EmagProductV2.sku == sku, EmagProductV2.account_type == to_account)
        )

        result_from = await self.db.execute(query_from)
        result_to = await self.db.execute(query_to)

        product_from = result_from.scalar_one_or_none()
        product_to = result_to.scalar_one_or_none()

        if not product_from or not product_to:
            return {"error": "Product not found on one or both accounts"}

        stock_from = product_from.stock_quantity or 0
        stock_to = product_to.stock_quantity or 0

        # Validation
        if stock_from < amount:
            return {
                "error": "Insufficient stock",
                "available": stock_from,
                "requested": amount,
            }

        # Calculate impact
        new_stock_from = stock_from - amount
        new_stock_to = stock_to + amount

        # Check if transfer makes sense
        warnings = []
        if new_stock_from == 0 and product_from.number_of_offers > 1:
            warnings.append(
                f"Transfer will leave {from_account} with 0 stock and competition"
            )

        if new_stock_from < 3 and product_from.number_of_offers > 1:
            warnings.append(
                f"Transfer will leave {from_account} with low stock "
                f"({new_stock_from}) and competition"
            )

        return {
            "sku": sku,
            "transfer": {
                "from_account": from_account,
                "to_account": to_account,
                "amount": amount,
            },
            "current_state": {
                f"stock_{from_account}": stock_from,
                f"stock_{to_account}": stock_to,
            },
            "proposed_state": {
                f"stock_{from_account}": new_stock_from,
                f"stock_{to_account}": new_stock_to,
            },
            "impact": {
                "from_account_impact": "Will lose buy button"
                if new_stock_from == 0 and product_from.number_of_offers > 1
                else "Safe",
                "to_account_impact": "Will gain/maintain buy button"
                if new_stock_to > 0
                else "Neutral",
            },
            "warnings": warnings,
            "recommendation": "Proceed" if not warnings else "Review warnings first",
        }
