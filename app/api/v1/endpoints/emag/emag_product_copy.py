"""
eMAG Product Copy API Endpoints

Endpoints for copying products from MAIN to FBE account.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db import get_db
from app.security.jwt import get_current_user
from app.services.emag.emag_product_link_service import EmagProductLinkService

router = APIRouter(prefix="/emag/products", tags=["emag-product-copy"])
logger = get_logger(__name__)


# Request/Response Models
class CopyToFBERequest(BaseModel):
    """Request model for copying product to FBE."""

    main_product_id: UUID = Field(..., description="UUID of the MAIN product")
    pricing_strategy: str = Field(
        default="discount",
        description="Pricing strategy: same, discount, profit_based, custom",
    )
    discount_percent: float = Field(
        default=5.0, ge=0, le=100, description="Discount percentage for FBE (0-100)"
    )
    stock_allocation: str = Field(
        default="split_50_50",
        description="Stock allocation: same, split_50_50, split_70_30, custom",
    )
    custom_price: float | None = Field(
        None, ge=0, description="Custom price for FBE (if strategy=custom)"
    )
    custom_stock: int | None = Field(
        None, ge=0, description="Custom stock for FBE (if allocation=custom)"
    )
    auto_sync: bool = Field(
        default=True, description="Enable auto-sync of future changes"
    )


class BulkCopyToFBERequest(BaseModel):
    """Request model for bulk copying products to FBE."""

    product_ids: list[UUID] = Field(..., description="List of MAIN product UUIDs")
    pricing_strategy: str = Field(default="discount")
    discount_percent: float = Field(default=5.0, ge=0, le=100)
    stock_allocation: str = Field(default="split_50_50")
    auto_sync: bool = Field(default=True)


class MigrateToFBERequest(BaseModel):
    """Request model for migrating product to FBE (full transfer)."""

    main_product_id: UUID = Field(..., description="UUID of the MAIN product")
    transfer_all_stock: bool = Field(
        default=True, description="Transfer 100% of stock to FBE"
    )
    deactivate_main: bool = Field(
        default=True, description="Deactivate MAIN product after migration"
    )
    pricing_strategy: str = Field(
        default="same", description="Pricing: same or discount"
    )
    discount_percent: float = Field(
        default=0.0, ge=0, le=100, description="Discount percentage (0 = same price)"
    )


class CopyToFBEResponse(BaseModel):
    """Response model for copy operation."""

    status: str
    message: str | None = None
    main_product_id: str | None = None
    fbe_product_id: str | None = None
    pricing: dict | None = None
    stock: dict | None = None
    auto_sync: bool | None = None
    # For conflicts
    existing_fbe_id: str | None = None
    resolution_options: list[str] | None = None


@router.post("/copy-to-fbe", response_model=CopyToFBEResponse)
async def copy_product_to_fbe(
    request: CopyToFBERequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Copy a product from MAIN to FBE account.

    This endpoint allows you to:
    - Copy product details from MAIN to FBE
    - Configure different pricing strategies
    - Allocate stock between accounts
    - Enable auto-sync for future updates

    **Pricing Strategies:**
    - `same`: Use same price as MAIN
    - `discount`: Apply percentage discount (default 5%)
    - `custom`: Use custom price

    **Stock Allocation:**
    - `same`: Same stock as MAIN
    - `split_50_50`: Split stock equally
    - `split_70_30`: 70% MAIN, 30% FBE
    - `custom`: Custom stock amount

    **Example:**
    ```json
    {
      "main_product_id": "123e4567-e89b-12d3-a456-426614174000",
      "pricing_strategy": "discount",
      "discount_percent": 5.0,
      "stock_allocation": "split_50_50",
      "auto_sync": true
    }
    ```
    """
    try:
        service = EmagProductLinkService(db)

        result = await service.copy_to_fbe(
            main_product_id=request.main_product_id,
            pricing_strategy=request.pricing_strategy,
            discount_percent=request.discount_percent,
            stock_allocation=request.stock_allocation,
            custom_price=request.custom_price,
            custom_stock=request.custom_stock,
            auto_sync=request.auto_sync,
        )

        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))

        return CopyToFBEResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in copy_product_to_fbe: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/bulk-copy-to-fbe")
async def bulk_copy_products_to_fbe(
    request: BulkCopyToFBERequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Copy multiple products from MAIN to FBE account.

    This endpoint allows bulk operations with the same settings
    applied to all selected products.

    **Example:**
    ```json
    {
      "product_ids": [
        "123e4567-e89b-12d3-a456-426614174000",
        "223e4567-e89b-12d3-a456-426614174001"
      ],
      "pricing_strategy": "discount",
      "discount_percent": 5.0,
      "stock_allocation": "split_50_50",
      "auto_sync": true
    }
    ```

    **Response:**
    ```json
    {
      "total": 2,
      "success": 2,
      "conflicts": 0,
      "errors": 0,
      "results": [...]
    }
    ```
    """
    try:
        service = EmagProductLinkService(db)

        settings = {
            "pricing_strategy": request.pricing_strategy,
            "discount_percent": request.discount_percent,
            "stock_allocation": request.stock_allocation,
            "auto_sync": request.auto_sync,
        }

        result = await service.bulk_copy_to_fbe(
            product_ids=request.product_ids, settings=settings
        )

        return result

    except Exception as e:
        logger.error(f"Error in bulk_copy_products_to_fbe: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/copy-preview/{product_id}")
async def preview_copy_to_fbe(
    product_id: UUID,
    pricing_strategy: str = Query("discount"),
    discount_percent: float = Query(5.0, ge=0, le=100),
    stock_allocation: str = Query("split_50_50"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Preview what the FBE product would look like before copying.

    This endpoint calculates pricing and stock allocation without
    actually creating the FBE product.

    **Example:**
    ```
    GET /api/v1/emag/products/copy-preview/123e4567-e89b-12d3-a456-426614174000?
        pricing_strategy=discount&
        discount_percent=5
    ```
    """
    try:
        service = EmagProductLinkService(db)

        # Get MAIN product
        from sqlalchemy import and_, select

        from app.models.emag_models import EmagProductV2

        result = await db.execute(
            select(EmagProductV2).where(
                and_(
                    EmagProductV2.id == product_id, EmagProductV2.account_type == "main"
                )
            )
        )
        main_product = result.scalar_one_or_none()

        if not main_product:
            raise HTTPException(
                status_code=404, detail=f"MAIN product {product_id} not found"
            )

        # Calculate preview
        pricing = service._calculate_fbe_pricing(
            main_price=main_product.price or 0,
            strategy=pricing_strategy,
            discount_percent=discount_percent,
        )

        fbe_stock = service._calculate_fbe_stock(
            main_stock=main_product.stock_quantity or 0, allocation=stock_allocation
        )

        return {
            "main_product": {
                "id": str(main_product.id),
                "sku": main_product.sku,
                "name": main_product.name,
                "price": main_product.price,
                "stock": main_product.stock_quantity,
            },
            "fbe_preview": {
                "pricing": pricing,
                "stock": fbe_stock,
                "estimated_revenue": round(pricing["sale_price"] * fbe_stock, 2)
                if fbe_stock
                else 0,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in preview_copy_to_fbe: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/migrate-to-fbe")
async def migrate_product_to_fbe(
    request: MigrateToFBERequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Migrate product from MAIN to FBE (full stock transfer).

    **Perfect for:** Switching to FBE fulfillment so you can travel!

    **What it does:**
    1. Transfers ALL stock from MAIN to FBE
    2. Keeps same SKU in both accounts (easy tracking)
    3. Optionally deactivates MAIN product
    4. Creates or updates FBE product

    **Use Case:**
    You want eMAG to handle fulfillment (storage, packing, shipping)
    so you can travel without worrying about orders.

    **Example:**
    ```json
    {
      "main_product_id": "123e4567-e89b-12d3-a456-426614174000",
      "transfer_all_stock": true,
      "deactivate_main": true,
      "pricing_strategy": "same",
      "discount_percent": 0
    }
    ```

    **Result:**
    - MAIN: Stock = 0, Status = Inactive
    - FBE: Stock = 10 (all transferred), Status = Active
    - Same SKU for easy tracking
    - eMAG handles everything! ✈️
    """
    try:
        service = EmagProductLinkService(db)

        result = await service.migrate_to_fbe(
            main_product_id=request.main_product_id,
            transfer_all_stock=request.transfer_all_stock,
            deactivate_main=request.deactivate_main,
            pricing_strategy=request.pricing_strategy,
            discount_percent=request.discount_percent,
        )

        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in migrate_product_to_fbe: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/bulk-migrate-to-fbe")
async def bulk_migrate_to_fbe(
    product_ids: list[UUID],
    transfer_all_stock: bool = Query(True),
    deactivate_main: bool = Query(True),
    pricing_strategy: str = Query("same"),
    discount_percent: float = Query(0.0, ge=0, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Migrate multiple products to FBE at once.

    **Perfect for:** Migrating your entire inventory to FBE fulfillment!

    **Example:**
    ```
    POST /api/v1/emag/products/bulk-migrate-to-fbe?transfer_all_stock=true&deactivate_main=true

    Body:
    {
      "product_ids": ["uuid1", "uuid2", "uuid3"]
    }
    ```

    **Response:**
    ```json
    {
      "total": 3,
      "success": 3,
      "failed": 0,
      "total_stock_transferred": 25,
      "results": [...]
    }
    ```
    """
    try:
        service = EmagProductLinkService(db)
        results = []
        total_stock = 0

        for product_id in product_ids:
            result = await service.migrate_to_fbe(
                main_product_id=product_id,
                transfer_all_stock=transfer_all_stock,
                deactivate_main=deactivate_main,
                pricing_strategy=pricing_strategy,
                discount_percent=discount_percent,
            )

            if result["status"] == "success":
                total_stock += result.get("stock_transferred", 0)

            results.append({"product_id": str(product_id), **result})

        success_count = len([r for r in results if r["status"] == "success"])

        return {
            "total": len(product_ids),
            "success": success_count,
            "failed": len(product_ids) - success_count,
            "total_stock_transferred": total_stock,
            "results": results,
        }

    except Exception as e:
        logger.error(f"Error in bulk_migrate_to_fbe: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
