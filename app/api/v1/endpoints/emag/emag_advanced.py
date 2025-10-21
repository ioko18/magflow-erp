"""
Advanced eMAG API v4.4.9 endpoints for MagFlow ERP.

This module provides REST API endpoints for new eMAG API v4.4.9 features:
- Light Offer API for simplified offer updates
- EAN matching for product discovery
- Measurements API for product dimensions
- Categories synchronization
- VAT rates and handling times
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.emag_config import get_emag_config
from app.db import get_db
from app.security.jwt import get_current_user
from app.services.emag.emag_api_client import EmagApiClient, EmagApiError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/emag/advanced", tags=["emag-advanced"])


# ========== Request/Response Models ==========


class LightOfferUpdateRequest(BaseModel):
    """Request model for Light Offer API update."""

    product_id: int = Field(..., description="Seller internal product ID")
    account_type: str = Field(..., description="Account type: 'main' or 'fbe'")
    sale_price: float | None = Field(None, description="Sale price without VAT")
    recommended_price: float | None = Field(
        None, description="Recommended retail price"
    )
    min_sale_price: float | None = Field(None, description="Minimum sale price")
    max_sale_price: float | None = Field(None, description="Maximum sale price")
    stock_value: int | None = Field(None, description="Stock quantity")
    warehouse_id: int = Field(1, description="Warehouse ID")
    handling_time_value: int | None = Field(
        None, description="Handling time in days"
    )
    vat_id: int | None = Field(None, description="VAT rate ID")
    status: int | None = Field(
        None, description="Offer status (0=inactive, 1=active)"
    )
    currency_type: str | None = Field(None, description="Currency (EUR or PLN)")


class EANSearchRequest(BaseModel):
    """Request model for EAN search."""

    eans: list[str] = Field(..., description="List of EAN codes (max 100)")
    account_type: str = Field(..., description="Account type: 'main' or 'fbe'")


class MeasurementsRequest(BaseModel):
    """Request model for product measurements."""

    product_id: int = Field(..., description="Seller internal product ID")
    account_type: str = Field(..., description="Account type: 'main' or 'fbe'")
    length: float = Field(..., description="Length in millimeters", ge=0, le=999999)
    width: float = Field(..., description="Width in millimeters", ge=0, le=999999)
    height: float = Field(..., description="Height in millimeters", ge=0, le=999999)
    weight: float = Field(..., description="Weight in grams", ge=0, le=999999)


# ========== Helper Functions ==========


def get_emag_client(account_type: str) -> EmagApiClient:
    """Get eMAG API client for specified account type."""
    try:
        config = get_emag_config(account_type=account_type.lower())

        return EmagApiClient(
            username=config.api_username,
            password=config.api_password,
            base_url=config.base_url,
            timeout=config.api_timeout,
            max_retries=config.max_retries,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ========== API Endpoints ==========


@router.post("/offers/update-light", response_model=dict[str, Any])
async def update_offer_light(
    request: LightOfferUpdateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update existing offer using Light Offer API (v4.4.9).

    This simplified endpoint is for updating EXISTING offers only.
    It's faster and cleaner than the full product_offer/save endpoint.

    **Benefits:**
    - Simpler payload - only send what you want to change
    - Faster processing
    - Recommended for stock and price updates

    **Note:** Cannot create new offers or modify product information.
    """
    try:
        client = get_emag_client(request.account_type)

        # Build stock array if stock_value provided
        stock = None
        if request.stock_value is not None:
            stock = [
                {"warehouse_id": request.warehouse_id, "value": request.stock_value}
            ]

        # Build handling_time array if provided
        handling_time = None
        if request.handling_time_value is not None:
            handling_time = [
                {
                    "warehouse_id": request.warehouse_id,
                    "value": request.handling_time_value,
                }
            ]

        # Call Light Offer API
        result = await client.update_offer_light(
            product_id=request.product_id,
            sale_price=request.sale_price,
            recommended_price=request.recommended_price,
            min_sale_price=request.min_sale_price,
            max_sale_price=request.max_sale_price,
            stock=stock,
            handling_time=handling_time,
            vat_id=request.vat_id,
            status=request.status,
            currency_type=request.currency_type,
        )

        return {
            "status": "success",
            "message": "Offer updated successfully using Light API",
            "data": result,
        }

    except EmagApiError as e:
        logger.error(f"eMAG API error updating offer: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error updating offer: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update offer: {str(e)}") from e


@router.post("/products/find-by-eans", response_model=dict[str, Any])
async def find_products_by_eans(
    request: EANSearchRequest,
    current_user=Depends(get_current_user),
):
    """Search products by EAN codes (v4.4.9).

    Quickly check if your products already exist on eMAG by searching EAN codes.

    **Benefits:**
    - Faster offer associations
    - More accurate product matching
    - Check product availability before creating offers

    **Rate Limits:**
    - 5 requests/second
    - 200 requests/minute
    - 5,000 requests/day

    **Returns:**
    - Product information including part_number_key for offer attachment
    - Whether you can add an offer (allow_to_add_offer)
    - Whether you already have an offer (vendor_has_offer)
    - Product performance indicator (hotness)
    """
    try:
        if len(request.eans) > 100:
            raise HTTPException(
                status_code=400, detail="Maximum 100 EAN codes allowed per request"
            )

        client = get_emag_client(request.account_type)
        result = await client.find_products_by_eans(request.eans)

        # Check for errors in response
        if result.get("isError"):
            messages = result.get("messages", [])
            error_msg = messages[0].get("text") if messages else "Unknown error"
            raise HTTPException(status_code=400, detail=error_msg)

        products = result.get("results", [])

        return {
            "status": "success",
            "message": f"Found {len(products)} matching products",
            "data": {
                "products": products,
                "total": len(products),
                "searched_eans": len(request.eans),
            },
        }

    except EmagApiError as e:
        logger.error(f"eMAG API error searching EANs: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching EANs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to search EANs: {str(e)}") from e


@router.post("/products/measurements", response_model=dict[str, Any])
async def save_product_measurements(
    request: MeasurementsRequest,
    current_user=Depends(get_current_user),
):
    """Save volume measurements (dimensions and weight) for a product.

    **Units:**
    - Dimensions: millimeters (mm)
    - Weight: grams (g)

    **Constraints:**
    - All values: 0 to 999,999
    - Up to 2 decimal places
    """
    try:
        client = get_emag_client(request.account_type)

        result = await client.save_measurements(
            product_id=request.product_id,
            length=request.length,
            width=request.width,
            height=request.height,
            weight=request.weight,
        )

        # Check for errors in response
        if result.get("isError"):
            messages = result.get("messages", [])
            error_msg = messages[0].get("text") if messages else "Unknown error"
            raise HTTPException(status_code=400, detail=error_msg)

        return {
            "status": "success",
            "message": "Measurements saved successfully",
            "data": result,
        }

    except EmagApiError as e:
        logger.error(f"eMAG API error saving measurements: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving measurements: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to save measurements: {str(e)}"
        ) from e


@router.get("/categories", response_model=dict[str, Any])
async def get_emag_categories(
    account_type: str = Query(..., description="Account type: 'main' or 'fbe'"),
    category_id: int | None = Query(
        None, description="Specific category ID for detailed info"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    items_per_page: int = Query(100, ge=1, le=100, description="Items per page"),
    language: str = Query(
        "ro", description="Response language (en, ro, hu, bg, pl, gr, de)"
    ),
    current_user=Depends(get_current_user),
):
    """Get eMAG categories with characteristics and family types.

    **Without category_id:** Returns list of categories (first 100 by default)

    **With category_id:** Returns detailed category information including:
    - Category name and metadata
    - Available characteristics (with IDs and validation rules)
    - Available product family_types (with IDs)
    - Mandatory/restrictive characteristics
    - Allowed values for characteristics
    """
    try:
        client = get_emag_client(account_type)

        result = await client.get_categories(
            category_id=category_id,
            page=page,
            items_per_page=items_per_page,
            language=language,
        )

        # Check for errors in response
        if result.get("isError"):
            messages = result.get("messages", [])
            error_msg = messages[0].get("text") if messages else "Unknown error"
            raise HTTPException(status_code=400, detail=error_msg)

        categories = result.get("results", [])

        return {
            "status": "success",
            "message": f"Retrieved {len(categories)} categories",
            "data": {
                "categories": categories,
                "total": len(categories),
                "page": page,
                "items_per_page": items_per_page,
            },
        }

    except EmagApiError as e:
        logger.error(f"eMAG API error fetching categories: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching categories: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch categories: {str(e)}"
        ) from e


@router.get("/vat-rates", response_model=dict[str, Any])
async def get_vat_rates(
    account_type: str = Query(..., description="Account type: 'main' or 'fbe'"),
    current_user=Depends(get_current_user),
):
    """Get available VAT rates from eMAG.

    Returns list of VAT rates with their IDs for use in offer creation/updates.
    """
    try:
        client = get_emag_client(account_type)
        result = await client.get_vat_rates()

        # Check for errors in response
        if result.get("isError"):
            messages = result.get("messages", [])
            error_msg = messages[0].get("text") if messages else "Unknown error"
            raise HTTPException(status_code=400, detail=error_msg)

        vat_rates = result.get("results", [])

        return {
            "status": "success",
            "message": f"Retrieved {len(vat_rates)} VAT rates",
            "data": {
                "vat_rates": vat_rates,
                "total": len(vat_rates),
            },
        }

    except EmagApiError as e:
        logger.error(f"eMAG API error fetching VAT rates: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching VAT rates: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch VAT rates: {str(e)}"
        ) from e


@router.get("/handling-times", response_model=dict[str, Any])
async def get_handling_times(
    account_type: str = Query(..., description="Account type: 'main' or 'fbe'"),
    current_user=Depends(get_current_user),
):
    """Get available handling time values from eMAG.

    Returns list of handling time values for use in offer creation/updates.
    """
    try:
        client = get_emag_client(account_type)
        result = await client.get_handling_times()

        # Check for errors in response
        if result.get("isError"):
            messages = result.get("messages", [])
            error_msg = messages[0].get("text") if messages else "Unknown error"
            raise HTTPException(status_code=400, detail=error_msg)

        handling_times = result.get("results", [])

        return {
            "status": "success",
            "message": f"Retrieved {len(handling_times)} handling time values",
            "data": {
                "handling_times": handling_times,
                "total": len(handling_times),
            },
        }

    except EmagApiError as e:
        logger.error(f"eMAG API error fetching handling times: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching handling times: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch handling times: {str(e)}"
        ) from e


@router.post("/offers/bulk-update-light", response_model=dict[str, Any])
async def bulk_update_offers_light(
    updates: list[LightOfferUpdateRequest],
    batch_size: int = Query(
        default=25, ge=1, le=50, description="Batch size for processing"
    ),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk update multiple offers using Light Offer API (v4.4.9).

    This endpoint processes multiple offer updates in batches for optimal performance.

    **Benefits:**
    - Update multiple products at once
    - Automatic batching for rate limit compliance
    - Progress tracking for each update

    **Batch Size:**
    - Recommended: 10-25 updates per batch
    - Maximum: 50 updates per batch
    - Automatic rate limiting applied

    **Returns:**
    - Success/failure status for each update
    - Total processed count
    - Error details for failed updates
    """
    import asyncio

    if len(updates) > 100:
        raise HTTPException(
            status_code=400,
            detail=(
                "Maximum 100 updates allowed per request. "
                "Use multiple requests for larger batches."
            ),
        )

    results = []
    total_success = 0
    total_failed = 0

    # Group updates by account type for efficiency
    updates_by_account = {}
    for update in updates:
        account = update.account_type.lower()
        if account not in updates_by_account:
            updates_by_account[account] = []
        updates_by_account[account].append(update)

    # Process each account's updates
    for account_type, account_updates in updates_by_account.items():
        try:
            client = get_emag_client(account_type)

            # Process in batches
            for i in range(0, len(account_updates), batch_size):
                batch = account_updates[i : i + batch_size]

                # Process batch concurrently
                batch_tasks = []
                for update in batch:
                    # Build stock array if stock_value provided
                    stock = None
                    if update.stock_value is not None:
                        stock = [
                            {
                                "warehouse_id": update.warehouse_id,
                                "value": update.stock_value,
                            }
                        ]

                    # Build handling_time array if provided
                    handling_time = None
                    if update.handling_time_value is not None:
                        handling_time = [
                            {
                                "warehouse_id": update.warehouse_id,
                                "value": update.handling_time_value,
                            }
                        ]

                    # Create task for this update
                    task = client.update_offer_light(
                        product_id=update.product_id,
                        sale_price=update.sale_price,
                        recommended_price=update.recommended_price,
                        min_sale_price=update.min_sale_price,
                        max_sale_price=update.max_sale_price,
                        stock=stock,
                        handling_time=handling_time,
                        vat_id=update.vat_id,
                        status=update.status,
                        currency_type=update.currency_type,
                    )
                    batch_tasks.append((update.product_id, task))

                # Execute batch
                batch_results = await asyncio.gather(
                    *[task for _, task in batch_tasks], return_exceptions=True
                )

                # Process results
                for (product_id, _), result in zip(batch_tasks, batch_results, strict=False):
                    if isinstance(result, Exception):
                        results.append(
                            {
                                "product_id": product_id,
                                "status": "failed",
                                "error": str(result),
                            }
                        )
                        total_failed += 1
                    elif result.get("isError"):
                        messages = result.get("messages", [])
                        error_msg = (
                            messages[0].get("text") if messages else "Unknown error"
                        )
                        results.append(
                            {
                                "product_id": product_id,
                                "status": "failed",
                                "error": error_msg,
                            }
                        )
                        total_failed += 1
                    else:
                        results.append(
                            {
                                "product_id": product_id,
                                "status": "success",
                                "data": result,
                            }
                        )
                        total_success += 1

                # Rate limiting between batches
                if i + batch_size < len(account_updates):
                    await asyncio.sleep(0.4)  # ~3 requests per second

        except Exception as e:
            logger.error(
                f"Error processing bulk updates for account {account_type}: {e}",
                exc_info=True,
            )
            # Mark remaining updates as failed
            for update in account_updates:
                if not any(r["product_id"] == update.product_id for r in results):
                    results.append(
                        {
                            "product_id": update.product_id,
                            "status": "failed",
                            "error": f"Batch processing error: {str(e)}",
                        }
                    )
                    total_failed += 1

    return {
        "status": "completed",
        "message": (
            f"Processed {len(updates)} updates: "
            f"{total_success} succeeded, {total_failed} failed"
        ),
        "summary": {
            "total": len(updates),
            "success": total_success,
            "failed": total_failed,
            "success_rate": round((total_success / len(updates)) * 100, 2)
            if updates
            else 0,
        },
        "results": results,
    }


__all__ = ["router"]
