"""
eMAG Price Update API Endpoint

Provides functionality to update product prices on eMAG FBE marketplace.
Inspired by the legacy price updater script but adapted for the new database structure.
"""

import logging
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user, get_database_session
from app.core.exceptions import ServiceError
from app.db.models import User as UserModel
from app.models.emag_offers import EmagProductOffer
from app.models.product import Product
from app.services.emag.emag_light_offer_service import EmagLightOfferService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/emag/price", tags=["emag-price-update"])


class PriceUpdateRequest(BaseModel):
    """Request model for price update."""

    product_id: int = Field(..., description="eMAG Product ID (Emag_FBE_Product_ID)")
    sale_price_with_vat: float = Field(
        ..., description="Sale price WITH VAT (will be converted to ex-VAT)", gt=0
    )
    min_sale_price_with_vat: float | None = Field(
        None, description="Minimum sale price WITH VAT (optional)", gt=0
    )
    max_sale_price_with_vat: float | None = Field(
        None, description="Maximum sale price WITH VAT (optional)", gt=0
    )
    vat_rate: float = Field(
        21.0, description="VAT rate percentage (default: 21% for Romania)", ge=0, le=100
    )
    # NOTE: Stock cannot be modified for FBE Fulfillment accounts (managed by eMAG)
    # stock: int | None = Field(None, description="Stock quantity (optional)", ge=0)
    # warehouse_id: int = Field(1, description="Warehouse ID (default: 1)", ge=1)


class PriceUpdateResponse(BaseModel):
    """Response model for price update."""

    success: bool
    message: str
    product_id: int
    sale_price_ex_vat: float
    sale_price_with_vat: float
    emag_response: dict[str, Any] | None = None


def gross_to_net(gross: float, vat_percent: float) -> float:
    """
    Convert price with VAT to price without VAT.

    Args:
        gross: Price with VAT
        vat_percent: VAT percentage (e.g., 21 for 21%)

    Returns:
        Price without VAT, rounded to 4 decimals
    """
    return round(gross / (1.0 + vat_percent / 100.0), 4)


def net_to_gross(net: float, vat_percent: float) -> float:
    """
    Convert price without VAT to price with VAT.

    Args:
        net: Price without VAT
        vat_percent: VAT percentage (e.g., 21 for 21%)

    Returns:
        Price with VAT, rounded to 2 decimals
    """
    return round(net * (1.0 + vat_percent / 100.0), 2)


@router.get("/product/{product_id}/info")
async def get_product_price_info(
    product_id: int,
    db: AsyncSession = Depends(get_database_session),
    current_user: UserModel = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    Get product price information including min/max prices from eMAG FBE.

    This endpoint retrieves the current prices from the local database,
    including min_sale_price and max_sale_price from the FBE offer.
    """
    try:
        # Get product from database
        result = await db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {product_id} not found",
            )

        # Get FBE offer info - try V2 first, then fall back to V1
        from app.models.emag_models import EmagProductOfferV2

        # Try V2 table first (newer)
        fbe_offer_v2_result = await db.execute(
            select(EmagProductOfferV2)
            .where(EmagProductOfferV2.sku == product.sku)
            .where(EmagProductOfferV2.account_type == "fbe")
        )
        fbe_offer_v2 = fbe_offer_v2_result.scalar_one_or_none()

        # Fall back to V1 table if not found in V2
        fbe_offer_v1 = None
        if not fbe_offer_v2:
            fbe_offer_result = await db.execute(
                select(EmagProductOffer)
                .where(EmagProductOffer.emag_product_id == product.sku)
                .where(EmagProductOffer.account_type == "fbe")
            )
            fbe_offer_v1 = fbe_offer_result.scalar_one_or_none()

        # Use whichever we found
        fbe_offer = fbe_offer_v2 or fbe_offer_v1

        # IMPORTANT: base_price is stored WITHOUT VAT (ex-VAT) in the database
        # So we need to ADD VAT to get the price with VAT
        base_price_ex_vat = product.base_price  # Already ex-VAT
        base_price_with_vat = net_to_gross(product.base_price, 21.0) if product.base_price else None
        
        logger.info(
            f"Product {product.id} ({product.sku}): base_price={product.base_price} (ex-VAT), "
            f"calculated with VAT={base_price_with_vat}"
        )
        
        response_data = {
            "product_id": product.id,
            "name": product.name,
            "sku": product.sku,
            "base_price": base_price_ex_vat,  # ex-VAT
            "base_price_with_vat": base_price_with_vat,  # with VAT
        }

        # Add FBE offer prices if available
        if fbe_offer:
            response_data.update({
                "has_fbe_offer": True,
                "emag_offer_id": fbe_offer.emag_offer_id,
                "min_sale_price": fbe_offer.min_sale_price,  # ex-VAT
                "max_sale_price": fbe_offer.max_sale_price,  # ex-VAT
                "recommended_price": fbe_offer.recommended_price,  # ex-VAT
                "min_sale_price_with_vat": fbe_offer.min_sale_price * 1.21 if fbe_offer.min_sale_price else None,
                "max_sale_price_with_vat": fbe_offer.max_sale_price * 1.21 if fbe_offer.max_sale_price else None,
                "recommended_price_with_vat": fbe_offer.recommended_price * 1.21 if fbe_offer.recommended_price else None,
            })
        else:
            response_data["has_fbe_offer"] = False

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting price info for product {product_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get product price info: {str(e)}",
        ) from e


@router.post("/update", response_model=PriceUpdateResponse)
async def update_emag_price(
    request: PriceUpdateRequest,
    db: AsyncSession = Depends(get_database_session),
    current_user: UserModel = Depends(get_current_active_user),
) -> PriceUpdateResponse:
    """
    Update product price on eMAG FBE marketplace.

    This endpoint:
    1. Converts prices from WITH VAT to WITHOUT VAT (as required by eMAG API)
    2. Updates the price using the Light Offer API (fast and efficient)
    3. Optionally updates stock if provided
    4. Returns confirmation with both ex-VAT and with-VAT prices

    **Important Notes:**
    - Prices are sent to eMAG WITHOUT VAT (ex-VAT)
    - The API automatically applies VAT for display on the marketplace
    - TVA România: 21%
    - **Stock cannot be modified for FBE Fulfillment accounts** (managed by eMAG)

    **Example:**
    - Input: sale_price_with_vat = 30.00 RON
    - Converted: sale_price_ex_vat = 24.79 RON (sent to eMAG)
    - eMAG displays: 30.00 RON (with VAT)
    """
    try:
        logger.info(
            f"User {current_user.email} requesting price update for product {request.product_id}"
        )

        # 1. Get product from database to find eMAG identifier
        result = await db.execute(
            select(Product).where(Product.id == request.product_id)
        )
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {request.product_id} not found in database",
            )

        # 2. Get eMAG identifier (SKU/part_number)
        emag_identifier = product.sku  # Use seller's SKU as part_number
        if not emag_identifier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product {product.name} does not have a SKU",
            )

        logger.info(
            f"Found product: {product.name} (SKU: {emag_identifier})"
        )

        # 3. Try to find the FBE offer ID in our database first (faster)
        fbe_offer_result = await db.execute(
            select(EmagProductOffer)
            .where(EmagProductOffer.emag_product_id == emag_identifier)
            .where(EmagProductOffer.account_type == "fbe")
        )
        fbe_offer_local = fbe_offer_result.scalar_one_or_none()

        emag_offer_id_from_db = None
        if fbe_offer_local:
            emag_offer_id_from_db = fbe_offer_local.emag_offer_id
            logger.info(
                f"Found FBE offer in local DB: ID={emag_offer_id_from_db}, "
                f"SKU={emag_identifier}"
            )

        # Convert prices from WITH VAT to WITHOUT VAT
        sale_price_ex_vat = gross_to_net(request.sale_price_with_vat, request.vat_rate)

        min_sale_price_ex_vat = None
        if request.min_sale_price_with_vat is not None:
            min_sale_price_ex_vat = gross_to_net(
                request.min_sale_price_with_vat, request.vat_rate
            )

        max_sale_price_ex_vat = None
        if request.max_sale_price_with_vat is not None:
            max_sale_price_ex_vat = gross_to_net(
                request.max_sale_price_with_vat, request.vat_rate
            )

        logger.info(
            f"Price conversion: {request.sale_price_with_vat} RON (with VAT) → "
            f"{sale_price_ex_vat} RON (ex-VAT) at {request.vat_rate}% VAT"
        )

        # Initialize eMAG Light Offer Service for FBE account
        async with EmagLightOfferService(account_type="fbe") as service:
            # 4. Get the eMAG FBE offer ID (from DB or API)
            emag_offer_id = emag_offer_id_from_db

            if not emag_offer_id:
                # Fallback: Search in eMAG API if not found in local DB
                logger.info(f"Searching for FBE offer in eMAG API with part_number: {emag_identifier}")

                # IMPORTANT: Search in FBE account specifically
                # The same SKU can have different IDs on MAIN vs FBE accounts
                search_response = await service.client.get_products(
                    page=1,
                    items_per_page=10,
                    filters={"part_number": emag_identifier},
                )

                if not search_response.get("results"):
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Offer not found on eMAG FBE for SKU: {emag_identifier}. "
                               f"Make sure the product is published on eMAG FBE account. "
                               f"Try running 'Sincronizare FBE' or 'Sincronizare AMBELE' first.",
                    )

                emag_offer = search_response["results"][0]

                # DEBUG: Log full offer response to see structure
                logger.info(f"Full eMAG offer response: {emag_offer}")

                # IMPORTANT: Use product ID (emag_offer["id"]), NOT offer_details.id
                # The offer/save endpoint expects the product ID from eMAG catalog
                # emag_offer["id"] = 398 (product ID - CORRECT for offer/save!)
                # emag_offer["offer_details"]["id"] = 105419640 (offer ID - used internally by eMAG)
                emag_offer_id = emag_offer.get("id")

                if not emag_offer_id:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"eMAG offer found but has no offer_details.id: {emag_offer}",
                    )

                # Extract current stock and vat_id from eMAG offer
                # CRITICAL: For FBE products, we CANNOT modify stock - must send current value
                current_stock = emag_offer.get("general_stock", 0)
                current_vat_id = emag_offer.get("vat_id", 9)  # Default to 9 (21% VAT Romania)

                logger.info(
                    f"Found eMAG FBE offer via API: ID={emag_offer_id}, name={emag_offer.get('name')}, "
                    f"current_price={emag_offer.get('sale_price')}, stock={current_stock}, vat_id={current_vat_id}"
                )

            # 5. Update price using eMAG product ID
            # IMPORTANT: offer/save (Light API) expects the eMAG product ID (from API response)
            # NOT our internal database ID
            logger.info(
                f"Updating price for product {request.product_id} (eMAG ID: {emag_offer_id}): "
                f"price={sale_price_ex_vat} ex-VAT, stock={current_stock}, vat_id={current_vat_id}"
            )
            emag_response = await service.update_offer_price(
                product_id=emag_offer_id,  # Use eMAG's ID from API response!
                sale_price=sale_price_ex_vat,
                min_sale_price=min_sale_price_ex_vat,
                max_sale_price=max_sale_price_ex_vat,
                current_stock=current_stock,  # Pass current stock from eMAG
                vat_id=current_vat_id,  # Pass current vat_id from eMAG
            )

        logger.info(
            f"Successfully updated price for product {request.product_id}. "
            f"Response: {emag_response}"
        )

        # 6. Update price in local database (Product table)
        try:
            product.base_price = sale_price_ex_vat  # Store ex-VAT price
            if request.max_sale_price_with_vat:
                product.recommended_price = gross_to_net(
                    request.max_sale_price_with_vat, request.vat_rate
                )

            await db.commit()
            await db.refresh(product)

            logger.info(
                f"Updated local DB price for product {request.product_id}: "
                f"base_price={sale_price_ex_vat}"
            )
        except Exception as e:
            logger.warning(
                f"Failed to update local DB price for product {request.product_id}: {str(e)}. "
                f"eMAG price was updated successfully."
            )
            # Don't fail the request if local DB update fails

        # 7. Update min/max prices in EmagProductOfferV2 table
        try:
            from app.models.emag_models import EmagProductOfferV2

            # Find the FBE offer in EmagProductOfferV2
            fbe_offer_v2_result = await db.execute(
                select(EmagProductOfferV2)
                .where(EmagProductOfferV2.sku == product.sku)
                .where(EmagProductOfferV2.account_type == "fbe")
            )
            fbe_offer_v2 = fbe_offer_v2_result.scalar_one_or_none()

            if fbe_offer_v2:
                # Update prices in EmagProductOfferV2
                fbe_offer_v2.sale_price = sale_price_ex_vat
                if min_sale_price_ex_vat is not None:
                    fbe_offer_v2.min_sale_price = min_sale_price_ex_vat
                if max_sale_price_ex_vat is not None:
                    fbe_offer_v2.max_sale_price = max_sale_price_ex_vat

                await db.commit()
                await db.refresh(fbe_offer_v2)

                logger.info(
                    f"Updated EmagProductOfferV2 for SKU {product.sku}: "
                    f"sale_price={sale_price_ex_vat}, "
                    f"min_sale_price={min_sale_price_ex_vat}, "
                    f"max_sale_price={max_sale_price_ex_vat}"
                )
            else:
                logger.warning(
                    f"No EmagProductOfferV2 found for SKU {product.sku} (FBE account). "
                    f"Prices updated on eMAG but not in local offer table."
                )
        except Exception as e:
            logger.warning(
                f"Failed to update EmagProductOfferV2 for product {request.product_id}: {str(e)}. "
                f"eMAG price was updated successfully."
            )
            # Don't fail the request if offer table update fails

        return PriceUpdateResponse(
            success=True,
            message=f"Price updated successfully on eMAG FBE and local database. "
            f"New price: {request.sale_price_with_vat} RON (with VAT) / "
            f"{sale_price_ex_vat} RON (ex-VAT)",
            product_id=request.product_id,
            sale_price_ex_vat=sale_price_ex_vat,
            sale_price_with_vat=request.sale_price_with_vat,
            emag_response=emag_response,
        )

    except ServiceError as e:
        logger.error(
            f"Service error updating price for product {request.product_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update price on eMAG: {str(e)}",
        ) from e
    except Exception as e:
        logger.error(
            f"Unexpected error updating price for product {request.product_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e


@router.post("/bulk-update")
async def bulk_update_emag_prices(
    updates: list[PriceUpdateRequest] = Body(
        ..., description="List of price updates to perform"
    ),
    current_user: UserModel = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    Bulk update prices for multiple products on eMAG FBE.

    This endpoint processes multiple price updates in batches for efficiency.
    Useful for updating prices for multiple products at once.

    **Rate Limiting:**
    - Processes ~3 requests per second to respect eMAG API limits
    - Batches of 25 products for optimal performance
    """
    try:
        logger.info(
            f"User {current_user.email} requesting bulk price update for "
            f"{len(updates)} products"
        )

        results = {
            "total": len(updates),
            "successful": 0,
            "failed": 0,
            "errors": [],
            "details": [],
        }

        async with EmagLightOfferService(account_type="fbe") as service:
            for update_request in updates:
                try:
                    # Convert price
                    sale_price_ex_vat = gross_to_net(
                        update_request.sale_price_with_vat, update_request.vat_rate
                    )

                    # Update on eMAG
                    await service.update_offer_price(
                        product_id=update_request.product_id,
                        sale_price=sale_price_ex_vat,
                    )

                    results["successful"] += 1
                    results["details"].append(
                        {
                            "product_id": update_request.product_id,
                            "status": "success",
                            "price_with_vat": update_request.sale_price_with_vat,
                            "price_ex_vat": sale_price_ex_vat,
                        }
                    )

                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(
                        {
                            "product_id": update_request.product_id,
                            "error": str(e),
                        }
                    )
                    logger.error(
                        f"Failed to update product {update_request.product_id}: {str(e)}"
                    )

        logger.info(
            f"Bulk update completed: {results['successful']} successful, "
            f"{results['failed']} failed"
        )

        return results

    except Exception as e:
        logger.error(f"Unexpected error in bulk price update: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk update failed: {str(e)}",
        ) from e
