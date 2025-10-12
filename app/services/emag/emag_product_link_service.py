"""
eMAG Product Link Service

Manages links between MAIN and FBE products, enabling:
- Copy product from MAIN to FBE
- Sync pricing and stock between linked products
- Auto-update FBE when MAIN changes
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.emag_models import EmagProductV2

logger = get_logger(__name__)


class EmagProductLinkService:
    """Service for managing product links between MAIN and FBE accounts."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def copy_to_fbe(
        self,
        main_product_id: UUID,
        pricing_strategy: str = "discount",
        discount_percent: float = 5.0,
        stock_allocation: str = "split_50_50",
        custom_price: float | None = None,
        custom_stock: int | None = None,
        auto_sync: bool = True,
    ) -> dict[str, Any]:
        """
        Copy a product from MAIN to FBE account.

        Args:
            main_product_id: UUID of the MAIN product
            pricing_strategy: 'same', 'discount', 'profit_based', 'custom'
            discount_percent: Percentage discount for FBE (default 5%)
            stock_allocation: 'same', 'split_50_50', 'split_70_30', 'custom'
            custom_price: Custom price for FBE (if strategy='custom')
            custom_stock: Custom stock for FBE (if allocation='custom')
            auto_sync: Enable auto-sync of future changes

        Returns:
            Dict with status and FBE product details
        """
        try:
            # Get MAIN product
            main_product = await self._get_product(main_product_id, "main")
            if not main_product:
                return {
                    "status": "error",
                    "message": f"MAIN product {main_product_id} not found",
                }

            # Check if already exists in FBE
            existing_fbe = await self._check_fbe_exists(main_product.sku)
            if existing_fbe:
                return {
                    "status": "conflict",
                    "message": f"SKU {main_product.sku} already exists in FBE",
                    "existing_fbe_id": str(existing_fbe.id),
                    "resolution_options": ["link", "replace", "skip"],
                }

            # Calculate FBE pricing
            fbe_pricing = self._calculate_fbe_pricing(
                main_price=main_product.price or 0,
                strategy=pricing_strategy,
                discount_percent=discount_percent,
                custom_price=custom_price,
            )

            # Calculate FBE stock
            fbe_stock = self._calculate_fbe_stock(
                main_stock=main_product.stock_quantity or 0,
                allocation=stock_allocation,
                custom_stock=custom_stock,
            )

            # Create FBE product
            fbe_product = await self._create_fbe_product(
                main_product=main_product,
                fbe_price=fbe_pricing["sale_price"],
                fbe_stock=fbe_stock,
            )

            logger.info(
                f"Successfully copied product {main_product.sku} from MAIN to FBE. "
                f"FBE ID: {fbe_product.id}, Price: {fbe_pricing['sale_price']}, Stock: {fbe_stock}"
            )

            return {
                "status": "success",
                "main_product_id": str(main_product.id),
                "fbe_product_id": str(fbe_product.id),
                "pricing": fbe_pricing,
                "stock": {"main": main_product.stock_quantity, "fbe": fbe_stock},
                "auto_sync": auto_sync,
            }

        except Exception as e:
            logger.error(f"Error copying product to FBE: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def migrate_to_fbe(
        self,
        main_product_id: UUID,
        transfer_all_stock: bool = True,
        deactivate_main: bool = True,
        pricing_strategy: str = "same",
        discount_percent: float = 0.0,
    ) -> dict[str, Any]:
        """
        Migrate product from MAIN to FBE (full stock transfer).

        Perfect for when you want eMAG to handle fulfillment (FBE)
        so you can travel without worrying about shipping.

        Args:
            main_product_id: UUID of MAIN product
            transfer_all_stock: Transfer 100% of stock to FBE (default: True)
            deactivate_main: Deactivate MAIN after migration (default: True)
            pricing_strategy: 'same' or 'discount'
            discount_percent: Discount for FBE (0 = same price)

        Returns:
            Dict with migration status and details
        """
        try:
            # Get MAIN product
            main_product = await self._get_product(main_product_id, "main")
            if not main_product:
                return {
                    "status": "error",
                    "message": f"MAIN product {main_product_id} not found",
                }

            # Check if SKU exists in FBE
            existing_fbe = await self._check_fbe_exists(main_product.sku)

            if existing_fbe:
                # Update existing FBE with additional stock
                old_stock = existing_fbe.stock_quantity or 0
                new_stock = old_stock + (main_product.stock_quantity or 0)

                existing_fbe.stock_quantity = new_stock
                existing_fbe.updated_at = datetime.now(UTC).replace(tzinfo=None)

                # Optionally sync other fields
                existing_fbe.name = main_product.name
                existing_fbe.description = main_product.description
                existing_fbe.images = main_product.images

                fbe_product = existing_fbe
                stock_transferred = main_product.stock_quantity or 0

                logger.info(
                    f"Updated existing FBE product {main_product.sku}: "
                    f"old stock={old_stock}, added={stock_transferred}, new={new_stock}"
                )
            else:
                # Calculate FBE pricing
                if pricing_strategy == "same":
                    fbe_price = main_product.price or 0
                else:
                    fbe_price = (main_product.price or 0) * (1 - discount_percent / 100)

                # Create FBE product with ALL stock
                fbe_product = await self._create_fbe_product(
                    main_product=main_product,
                    fbe_price=fbe_price,
                    fbe_stock=main_product.stock_quantity or 0,
                )
                stock_transferred = main_product.stock_quantity or 0

            # Update MAIN product
            if transfer_all_stock:
                main_product.stock_quantity = 0

            if deactivate_main:
                main_product.is_active = False
                main_product.status = "migrated_to_fbe"

            await self.db.commit()

            logger.info(
                f"Successfully migrated {main_product.sku} to FBE. "
                f"Stock transferred: {stock_transferred}, "
                f"MAIN status: {'inactive' if deactivate_main else 'active'}"
            )

            return {
                "status": "success",
                "message": "Product migrated to FBE successfully",
                "main_product_id": str(main_product.id),
                "fbe_product_id": str(fbe_product.id),
                "sku": main_product.sku,
                "stock_transferred": stock_transferred,
                "main_stock_remaining": main_product.stock_quantity,
                "fbe_total_stock": fbe_product.stock_quantity,
                "main_status": "inactive" if deactivate_main else "active",
                "fbe_price": fbe_product.price,
            }

        except Exception as e:
            logger.error(f"Error migrating to FBE: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def bulk_copy_to_fbe(
        self, product_ids: list[UUID], settings: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Copy multiple products from MAIN to FBE.

        Args:
            product_ids: List of MAIN product UUIDs
            settings: Common settings for all products

        Returns:
            Dict with results for each product
        """
        results = []
        success_count = 0
        error_count = 0
        conflict_count = 0

        for product_id in product_ids:
            result = await self.copy_to_fbe(main_product_id=product_id, **settings)

            results.append({"product_id": str(product_id), **result})

            if result["status"] == "success":
                success_count += 1
            elif result["status"] == "conflict":
                conflict_count += 1
            else:
                error_count += 1

        return {
            "total": len(product_ids),
            "success": success_count,
            "conflicts": conflict_count,
            "errors": error_count,
            "results": results,
        }

    def _calculate_fbe_pricing(
        self,
        main_price: float,
        strategy: str,
        discount_percent: float = 5.0,
        custom_price: float | None = None,
    ) -> dict[str, float]:
        """Calculate FBE pricing based on strategy."""

        if strategy == "same":
            sale_price = main_price
        elif strategy == "discount":
            sale_price = main_price * (1 - discount_percent / 100)
        elif strategy == "custom" and custom_price:
            sale_price = custom_price
        else:
            # Default to 5% discount
            sale_price = main_price * 0.95

        # Auto-calculate min/max prices
        min_price = round(sale_price * 0.90, 2)  # 10% below sale price
        max_price = round(sale_price * 1.01, 2)  # 1% above sale price

        return {
            "sale_price": round(sale_price, 2),
            "min_price": min_price,
            "max_price": max_price,
            "discount_percent": round((1 - sale_price / main_price) * 100, 2)
            if main_price > 0
            else 0,
        }

    def _calculate_fbe_stock(
        self, main_stock: int, allocation: str, custom_stock: int | None = None
    ) -> int:
        """Calculate FBE stock based on allocation strategy."""

        if allocation == "same":
            return main_stock
        elif allocation == "split_50_50":
            return main_stock // 2
        elif allocation == "split_70_30":
            return int(main_stock * 0.3)
        elif allocation == "custom" and custom_stock is not None:
            return custom_stock
        else:
            # Default to 50/50 split
            return main_stock // 2

    async def _get_product(
        self, product_id: UUID, account_type: str
    ) -> EmagProductV2 | None:
        """Get product by ID and account type."""
        result = await self.db.execute(
            select(EmagProductV2).where(
                and_(
                    EmagProductV2.id == product_id,
                    EmagProductV2.account_type == account_type,
                )
            )
        )
        return result.scalar_one_or_none()

    async def _check_fbe_exists(self, sku: str) -> EmagProductV2 | None:
        """Check if SKU already exists in FBE account."""
        result = await self.db.execute(
            select(EmagProductV2).where(
                and_(EmagProductV2.sku == sku, EmagProductV2.account_type == "fbe")
            )
        )
        return result.scalar_one_or_none()

    async def _create_fbe_product(
        self, main_product: EmagProductV2, fbe_price: float, fbe_stock: int
    ) -> EmagProductV2:
        """Create a new FBE product based on MAIN product."""

        fbe_product = EmagProductV2(
            # Copy from MAIN
            sku=main_product.sku,
            name=main_product.name,
            description=main_product.description,
            brand=main_product.brand,
            manufacturer=main_product.manufacturer,
            category_id=main_product.category_id,
            images=main_product.images,
            attributes=main_product.attributes,
            specifications=main_product.specifications,
            # FBE specific
            account_type="fbe",
            price=fbe_price,
            stock_quantity=fbe_stock,
            currency=main_product.currency or "RON",
            # Status
            is_active=True,
            status="pending",
            sync_status="pending",
            # Metadata
            source_account="main",
            created_at=datetime.now(UTC).replace(tzinfo=None),
            updated_at=datetime.now(UTC).replace(tzinfo=None),
        )

        self.db.add(fbe_product)
        await self.db.commit()
        await self.db.refresh(fbe_product)

        return fbe_product
