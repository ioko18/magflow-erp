"""eMAG API v4.4.9 Enhanced Endpoints."""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel, Field
import logging

from app.db import get_db
from app.security.jwt import get_current_user
from app.services.enhanced_emag_service import EnhancedEmagIntegrationService
from app.services.emag_validation_service import EmagValidationService
from app.models.emag_models import EmagProductV2

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/emag/v449", tags=["eMAG v4.4.9"])


class EANSearchRequest(BaseModel):
    """Request model for EAN search."""
    ean_codes: List[str] = Field(..., max_items=100, description="EAN codes to search (max 100)")
    account_type: str = Field(default="main", description="Account type: main or fbe")


class QuickOfferUpdateRequest(BaseModel):
    """Request model for quick offer update."""
    sale_price: Optional[float] = None
    recommended_price: Optional[float] = None
    min_sale_price: Optional[float] = None
    max_sale_price: Optional[float] = None
    stock: Optional[List[Dict[str, int]]] = None
    handling_time: Optional[List[Dict[str, int]]] = None
    vat_id: Optional[int] = None
    status: Optional[int] = None
    currency_type: Optional[str] = None


class ProductMeasurementsRequest(BaseModel):
    """Request model for product measurements."""
    length: float = Field(..., ge=0, le=999999, description="Length in millimeters")
    width: float = Field(..., ge=0, le=999999, description="Width in millimeters")
    height: float = Field(..., ge=0, le=999999, description="Height in millimeters")
    weight: float = Field(..., ge=0, le=999999, description="Weight in grams")


@router.post("/products/search-by-ean")
async def search_products_by_ean(
    request: EANSearchRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search eMAG products by EAN codes (v4.4.9).
    
    This endpoint uses the new EAN Search API to quickly find products
    in the eMAG marketplace by their EAN codes.
    
    Rate Limits:
    - 5 requests/second
    - 200 requests/minute
    - 5,000 requests/day
    
    Returns:
    - List of products found with their details
    - Information about whether you can add offers
    - Competition metrics (hotness, number of offers)
    """
    try:
        logger.info(f"EAN search requested by {current_user.email} for {len(request.ean_codes)} codes")

        async with EnhancedEmagIntegrationService(request.account_type, db) as service:
            results = await service.api_client.find_products_by_eans(request.ean_codes)

            if results.get("isError"):
                error_messages = results.get("messages", ["EAN search failed"])
                logger.error(f"EAN search failed: {error_messages}")
                raise HTTPException(
                    status_code=400,
                    detail=error_messages[0] if isinstance(error_messages, list) else str(error_messages)
                )

            products_found = results.get("results", [])
            logger.info(f"EAN search found {len(products_found)} products")

            return {
                "status": "success",
                "data": products_found,
                "total": len(products_found),
                "searched_eans": len(request.ean_codes),
                "account_type": request.account_type
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"EAN search error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"EAN search failed: {str(e)}")


@router.patch("/products/{product_id}/offer-quick-update")
async def quick_update_offer(
    product_id: int,
    update_data: QuickOfferUpdateRequest,
    account_type: str = Query(default="main", description="Account type: main or fbe"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Quick update offer using Light Offer API (v4.4.9).
    
    This endpoint is significantly faster than the traditional product_offer/save
    because it only sends the fields you want to update, not the entire product data.
    
    Performance:
    - 3x faster than traditional API
    - Only sends modified fields
    - Ideal for frequent price/stock updates
    
    Limitations:
    - Can only update EXISTING offers
    - Cannot create new offers
    - Cannot modify product documentation
    """
    try:
        logger.info(f"Quick offer update requested by {current_user.email} for product {product_id}")

        async with EnhancedEmagIntegrationService(account_type, db) as service:
            # Build update data - only include provided fields
            offer_data: Dict[str, Any] = {"id": product_id}

            if update_data.sale_price is not None:
                offer_data["sale_price"] = update_data.sale_price
            if update_data.recommended_price is not None:
                offer_data["recommended_price"] = update_data.recommended_price
            if update_data.min_sale_price is not None:
                offer_data["min_sale_price"] = update_data.min_sale_price
            if update_data.max_sale_price is not None:
                offer_data["max_sale_price"] = update_data.max_sale_price
            if update_data.stock is not None:
                offer_data["stock"] = update_data.stock
            if update_data.handling_time is not None:
                offer_data["handling_time"] = update_data.handling_time
            if update_data.vat_id is not None:
                offer_data["vat_id"] = update_data.vat_id
            if update_data.status is not None:
                offer_data["status"] = update_data.status
            if update_data.currency_type is not None:
                offer_data["currency_type"] = update_data.currency_type

            # Call Light Offer API
            result = await service.api_client.update_offer_light(**offer_data)

            if result.get("isError"):
                error_messages = result.get("messages", ["Offer update failed"])
                logger.error(f"Offer update failed: {error_messages}")
                raise HTTPException(
                    status_code=400,
                    detail=error_messages[0] if isinstance(error_messages, list) else str(error_messages)
                )

            logger.info(f"Successfully updated offer for product {product_id}")

            return {
                "status": "success",
                "message": "Offer updated successfully using Light Offer API",
                "product_id": product_id,
                "updated_fields": [k for k in offer_data.keys() if k != "id"],
                "account_type": account_type
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quick offer update error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Offer update failed: {str(e)}")


@router.post("/products/{product_id}/measurements")
async def save_product_measurements(
    product_id: str,  # Can be UUID or emag_id
    measurements: ProductMeasurementsRequest,
    account_type: str = Query(default="main", description="Account type: main or fbe"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save product measurements (dimensions and weight).
    
    This endpoint saves the physical dimensions and weight of a product,
    which are required for accurate shipping cost calculation and logistics.
    
    Units (as per eMAG API specification):
    - Dimensions: millimeters (mm)
    - Weight: grams (g)
    
    The measurements are saved both in eMAG and in the local database.
    """
    try:
        logger.info(f"Measurements save requested by {current_user.email} for product {product_id}")

        # Find product in database
        stmt = select(EmagProductV2).where(
            (EmagProductV2.emag_id == product_id) | (EmagProductV2.sku == product_id)
        ).where(
            EmagProductV2.account_type == account_type
        )
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product {product_id} not found in {account_type} account"
            )

        # Get the actual eMAG product ID for API call
        emag_product_id = product.emag_id
        if not emag_product_id:
            raise HTTPException(
                status_code=400,
                detail="Product does not have an eMAG ID"
            )

        async with EnhancedEmagIntegrationService(account_type, db) as service:
            # Save measurements to eMAG
            result = await service.api_client.save_measurements(
                product_id=int(emag_product_id),
                length=measurements.length,
                width=measurements.width,
                height=measurements.height,
                weight=measurements.weight
            )

            if result.get("isError"):
                error_messages = result.get("messages", ["Measurements save failed"])
                logger.error(f"Measurements save failed: {error_messages}")
                raise HTTPException(
                    status_code=400,
                    detail=error_messages[0] if isinstance(error_messages, list) else str(error_messages)
                )

            # Update local database
            stmt = (
                update(EmagProductV2)
                .where(EmagProductV2.id == product.id)
                .values(
                    length_mm=measurements.length,
                    width_mm=measurements.width,
                    height_mm=measurements.height,
                    weight_g=measurements.weight
                )
            )
            await db.execute(stmt)
            await db.commit()

            logger.info(f"Successfully saved measurements for product {product_id}")

            return {
                "status": "success",
                "message": "Measurements saved successfully in eMAG and local database",
                "product_id": product_id,
                "emag_id": emag_product_id,
                "measurements": {
                    "length_mm": measurements.length,
                    "width_mm": measurements.width,
                    "height_mm": measurements.height,
                    "weight_g": measurements.weight
                },
                "account_type": account_type
            }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Measurements save error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Measurements save failed: {str(e)}")


@router.patch("/products/{product_id}/stock-only")
async def update_stock_only(
    product_id: int,
    stock_value: int = Query(..., ge=0, description="New stock quantity"),
    warehouse_id: int = Query(default=1, description="Warehouse ID"),
    account_type: str = Query(default="main", description="Account type: main or fbe"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update ONLY stock using PATCH endpoint (fastest method).
    
    This is the absolute fastest way to update inventory in eMAG.
    It uses the PATCH method which is 5x faster than traditional POST.
    
    Use this endpoint for:
    - Real-time inventory synchronization
    - Frequent stock updates
    - High-volume stock changes
    
    Performance:
    - 5x faster than full offer update
    - Only modifies stock, nothing else
    - Ideal for inventory sync systems
    """
    try:
        logger.info(f"Stock-only update requested by {current_user.email} for product {product_id}")

        async with EnhancedEmagIntegrationService(account_type, db) as service:
            result = await service.api_client.update_stock_only(
                product_id=product_id,
                warehouse_id=warehouse_id,
                stock_value=stock_value
            )

            if result.get("isError"):
                error_messages = result.get("messages", ["Stock update failed"])
                logger.error(f"Stock update failed: {error_messages}")
                raise HTTPException(
                    status_code=400,
                    detail=error_messages[0] if isinstance(error_messages, list) else str(error_messages)
                )

            logger.info(f"Successfully updated stock for product {product_id} to {stock_value}")

            return {
                "status": "success",
                "message": "Stock updated successfully using PATCH method",
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "new_stock": stock_value,
                "account_type": account_type
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stock update error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Stock update failed: {str(e)}")


class CampaignProposalRequest(BaseModel):
    """Request model for campaign proposal."""
    campaign_id: int = Field(..., description="eMAG campaign ID")
    sale_price: float = Field(..., gt=0, description="Campaign price without VAT")
    stock: int = Field(..., ge=1, le=255, description="Reserved stock for campaign")
    max_qty_per_order: Optional[int] = Field(None, description="Max quantity per customer order")
    voucher_discount: Optional[int] = Field(None, ge=10, le=100, description="Voucher discount percentage (10-100)")
    post_campaign_sale_price: Optional[float] = Field(None, description="Price after campaign ends")
    not_available_post_campaign: bool = Field(default=False, description="Deactivate offer after campaign")
    date_intervals: Optional[List[Dict[str, Any]]] = Field(None, description="Required for MultiDeals campaigns")


@router.post("/products/{product_id}/campaign-proposal")
async def propose_to_campaign(
    product_id: int,
    proposal: CampaignProposalRequest,
    account_type: str = Query(default="main", description="Account type: main or fbe"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Propose product to eMAG campaign.
    
    This endpoint allows you to submit product offers to eMAG campaigns.
    
    Campaign Types:
    - **Standard**: Basic campaign with sale price and stock
    - **Stock-in-site**: Requires max_qty_per_order
    - **MultiDeals**: Requires date_intervals array (max 30 intervals)
    
    Stock Management:
    - Stock reserved for campaign is separate from regular offer stock
    - Once campaign stock is depleted, product cannot be ordered in campaign
    - Regular offer stock remains unaffected
    
    Post-Campaign Behavior:
    - If not_available_post_campaign=True: offer becomes inactive after campaign
    - If False: offer returns to normal state with post_campaign_sale_price
    - post_campaign_sale_price defaults to current sale price if not specified
    
    Example (Simple Campaign):
        {
            "campaign_id": 344,
            "sale_price": 51.65,
            "stock": 10,
            "max_qty_per_order": 4,
            "voucher_discount": 15
        }
    
    Example (MultiDeals Campaign):
        {
            "campaign_id": 400,
            "sale_price": 99.99,
            "stock": 50,
            "max_qty_per_order": 3,
            "date_intervals": [
                {
                    "start_date": {"date": "2025-04-21 00:00:00.000000", "timezone_type": 3, "timezone": "Europe/Bucharest"},
                    "end_date": {"date": "2025-04-22 23:59:59.000000", "timezone_type": 3, "timezone": "Europe/Bucharest"},
                    "voucher_discount": 10,
                    "index": 1
                }
            ]
        }
    """
    try:
        logger.info(f"Campaign proposal requested by {current_user.email} for product {product_id} to campaign {proposal.campaign_id}")

        async with EnhancedEmagIntegrationService(account_type, db) as service:
            result = await service.api_client.propose_to_campaign(
                product_id=product_id,
                campaign_id=proposal.campaign_id,
                sale_price=proposal.sale_price,
                stock=proposal.stock,
                max_qty_per_order=proposal.max_qty_per_order,
                voucher_discount=proposal.voucher_discount,
                post_campaign_sale_price=proposal.post_campaign_sale_price,
                not_available_post_campaign=proposal.not_available_post_campaign,
                date_intervals=proposal.date_intervals
            )

            if result.get("isError"):
                error_messages = result.get("messages", ["Campaign proposal failed"])
                logger.error(f"Campaign proposal failed: {error_messages}")
                raise HTTPException(
                    status_code=400,
                    detail=error_messages[0] if isinstance(error_messages, list) else str(error_messages)
                )

            logger.info(f"Successfully proposed product {product_id} to campaign {proposal.campaign_id}")

            return {
                "status": "success",
                "message": "Product successfully proposed to campaign",
                "product_id": product_id,
                "campaign_id": proposal.campaign_id,
                "sale_price": proposal.sale_price,
                "stock": proposal.stock,
                "account_type": account_type
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Campaign proposal error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Campaign proposal failed: {str(e)}")


class ProductValidationRequest(BaseModel):
    """Request model for product validation."""
    product_data: Dict[str, Any] = Field(..., description="Product data to validate")
    category_template: Optional[Dict[str, Any]] = Field(None, description="Optional category template")


@router.post("/products/validate")
async def validate_product(
    request: ProductValidationRequest,
    current_user=Depends(get_current_user),
):
    """
    Validate product data before publication to eMAG.
    
    Performs comprehensive validation including:
    - Required fields check
    - Image validation (format, main image, URLs)
    - EAN code validation (format and checksum)
    - Characteristics validation against category template
    - Pricing validation
    - Measurements validation
    - Field length constraints
    
    Returns validation results with errors and warnings.
    """
    try:
        logger.info(f"Product validation requested by {current_user.email}")

        validation_service = EmagValidationService()

        # Perform complete validation
        is_valid, errors, warnings = validation_service.validate_product_complete(
            product_data=request.product_data,
            category_template=request.category_template
        )

        # Get formatted summary
        summary = validation_service.get_validation_summary(errors, warnings)

        logger.info(
            f"Validation complete: valid={is_valid}, errors={len(errors)}, warnings={len(warnings)}"
        )

        return {
            "status": "success",
            "validation": summary,
            "product_name": request.product_data.get('name', 'Unknown'),
            "sku": request.product_data.get('part_number', 'Unknown')
        }

    except Exception as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.post("/products/validate-bulk")
async def validate_products_bulk(
    products: List[Dict[str, Any]],
    category_template: Optional[Dict[str, Any]] = None,
    current_user=Depends(get_current_user),
):
    """
    Validate multiple products in bulk.
    
    Returns validation results for each product.
    """
    try:
        logger.info(f"Bulk validation requested by {current_user.email} for {len(products)} products")

        validation_service = EmagValidationService()
        results = []

        for idx, product_data in enumerate(products):
            try:
                is_valid, errors, warnings = validation_service.validate_product_complete(
                    product_data=product_data,
                    category_template=category_template
                )

                summary = validation_service.get_validation_summary(errors, warnings)

                results.append({
                    "index": idx,
                    "sku": product_data.get('part_number', 'Unknown'),
                    "name": product_data.get('name', 'Unknown'),
                    "validation": summary
                })
            except Exception as e:
                results.append({
                    "index": idx,
                    "sku": product_data.get('part_number', 'Unknown'),
                    "name": product_data.get('name', 'Unknown'),
                    "validation": {
                        "is_valid": False,
                        "error_count": 1,
                        "warning_count": 0,
                        "errors": [f"Validation exception: {str(e)}"],
                        "warnings": [],
                        "severity": "error"
                    }
                })

        # Calculate summary statistics
        total = len(results)
        valid = sum(1 for r in results if r['validation']['is_valid'])
        invalid = total - valid

        logger.info(f"Bulk validation complete: {valid}/{total} valid")

        return {
            "status": "success",
            "summary": {
                "total": total,
                "valid": valid,
                "invalid": invalid,
                "validation_rate": round((valid / total * 100), 2) if total > 0 else 0
            },
            "results": results
        }

    except Exception as e:
        logger.error(f"Bulk validation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Bulk validation failed: {str(e)}")
