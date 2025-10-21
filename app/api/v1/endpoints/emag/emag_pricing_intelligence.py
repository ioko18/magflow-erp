"""
eMAG Pricing Intelligence API Endpoints for MagFlow ERP.

This module provides REST API endpoints for eMAG pricing intelligence features:
- Commission estimates
- Smart Deals eligibility checks
- EAN-based product search
- Pricing optimization recommendations

Implements eMAG API v4.4.9 features.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config.emag_config import get_emag_config
from app.core.logging import get_logger
from app.db import get_db
from app.models.user import User
from app.services.emag.emag_api_client import EmagApiClient

logger = get_logger(__name__)
router = APIRouter()


# Pydantic models for request/response
class CommissionEstimateResponse(BaseModel):
    """Response model for commission estimate."""

    product_id: int
    commission_value: float | None = None
    commission_percentage: float | None = None
    created: str | None = None
    end_date: str | None = None
    error: str | None = None


class SmartDealsCheckResponse(BaseModel):
    """Response model for Smart Deals eligibility check."""

    product_id: int
    current_price: float | None = None
    target_price: float | None = None
    discount_required: float | None = None
    is_eligible: bool = False
    message: str | None = None
    error: str | None = None


class EANSearchRequest(BaseModel):
    """Request model for EAN search."""

    eans: list[str] = Field(..., description="List of EAN codes (max 100)")
    account_type: str = Field(
        default="main", description="Account type: 'main' or 'fbe'"
    )


class EANSearchResponse(BaseModel):
    """Response model for EAN search."""

    results: list[dict[str, Any]]
    total_found: int
    account_type: str


class PricingRecommendationRequest(BaseModel):
    """Request model for pricing recommendations."""

    product_id: int
    current_price: float
    account_type: str = Field(
        default="main", description="Account type: 'main' or 'fbe'"
    )


class PricingRecommendationResponse(BaseModel):
    """Response model for pricing recommendations."""

    product_id: int
    current_price: float
    recommended_price: float | None = None
    commission_estimate: float | None = None
    smart_deals_eligible: bool = False
    smart_deals_target_price: float | None = None
    potential_savings: float | None = None
    recommendations: list[str] = []


# API Endpoints


@router.get(
    "/commission/estimate/{product_id}", response_model=CommissionEstimateResponse
)
async def get_commission_estimate(
    product_id: int,
    account_type: str = Query(
        default="main", description="Account type: 'main' or 'fbe'"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CommissionEstimateResponse:
    """
    Get commission estimate for a product.

    This endpoint retrieves the estimated commission that eMAG will charge
    for selling a specific product. Useful for pricing strategy and profit
    margin calculations.

    Args:
        product_id: Seller internal product ID (ext_id)
        account_type: Account type ('main' or 'fbe')

    Returns:
        CommissionEstimateResponse with commission details
    """
    try:
        config = get_emag_config(account_type)

        async with EmagApiClient(
            username=config.api_username,
            password=config.api_password,
            base_url=config.base_url,
        ) as client:
            result = await client.get_commission_estimate(product_id)

            if result.get("isError"):
                error_msg = result.get("messages", [{}])[0].get("text", "Unknown error")
                logger.warning(
                    f"Commission estimate error for product {product_id}: {error_msg}"
                )
                return CommissionEstimateResponse(
                    product_id=product_id, error=error_msg
                )

            # Parse the response
            data = result.get("results", {})
            if isinstance(data, list) and data:
                data = data[0]

            return CommissionEstimateResponse(
                product_id=product_id,
                commission_value=data.get("value"),
                commission_percentage=data.get("percentage"),
                created=data.get("created"),
                end_date=data.get("end_date"),
            )

    except Exception as e:
        logger.error(f"Error getting commission estimate for product {product_id}: {e}")
        return CommissionEstimateResponse(product_id=product_id, error=str(e))


@router.get("/smart-deals/check/{product_id}", response_model=SmartDealsCheckResponse)
async def check_smart_deals_eligibility(
    product_id: int,
    account_type: str = Query(
        default="main", description="Account type: 'main' or 'fbe'"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SmartDealsCheckResponse:
    """
    Check if product qualifies for Smart Deals badge.

    Smart Deals is an eMAG program that highlights products with competitive
    pricing. This endpoint checks if a product qualifies and provides the
    target price needed for eligibility.

    Args:
        product_id: Seller internal product ID
        account_type: Account type ('main' or 'fbe')

    Returns:
        SmartDealsCheckResponse with eligibility details
    """
    try:
        config = get_emag_config(account_type)

        async with EmagApiClient(
            username=config.api_username,
            password=config.api_password,
            base_url=config.base_url,
        ) as client:
            result = await client.check_smart_deals_eligibility(product_id)

            if result.get("isError"):
                error_msg = result.get("messages", [{}])[0].get("text", "Unknown error")
                logger.warning(
                    f"Smart Deals check error for product {product_id}: {error_msg}"
                )
                return SmartDealsCheckResponse(product_id=product_id, error=error_msg)

            # Parse the response
            data = result.get("results", {})
            if isinstance(data, list) and data:
                data = data[0]

            current_price = data.get("currentPrice")
            target_price = data.get("targetPrice")

            discount_required = None
            if current_price and target_price and current_price > 0:
                discount_required = (
                    (current_price - target_price) / current_price
                ) * 100

            return SmartDealsCheckResponse(
                product_id=product_id,
                current_price=current_price,
                target_price=target_price,
                discount_required=discount_required,
                is_eligible=data.get("isEligible", False),
                message=data.get("message"),
            )

    except Exception as e:
        logger.error(
            f"Error checking Smart Deals eligibility for product {product_id}: {e}"
        )
        return SmartDealsCheckResponse(product_id=product_id, error=str(e))


@router.post("/ean/search", response_model=EANSearchResponse)
async def search_products_by_ean(
    request: EANSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EANSearchResponse:
    """
    Search for products by EAN codes.

    This endpoint searches the eMAG catalog for products matching the provided
    EAN codes. It can search up to 100 EANs per request and returns information
    about whether the products exist and if the vendor already has offers for them.

    Useful for:
    - Avoiding duplicate product creation
    - Checking if products already exist in eMAG catalog
    - Verifying if you already have offers for specific products

    Args:
        request: EANSearchRequest with list of EAN codes

    Returns:
        EANSearchResponse with search results
    """
    try:
        if len(request.eans) > 100:
            raise HTTPException(
                status_code=400, detail="Maximum 100 EAN codes allowed per request"
            )

        config = get_emag_config(request.account_type)

        async with EmagApiClient(
            username=config.api_username,
            password=config.api_password,
            base_url=config.base_url,
        ) as client:
            result = await client.find_products_by_eans(request.eans)

            if result.get("isError"):
                error_msg = result.get("messages", [{}])[0].get("text", "Unknown error")
                raise HTTPException(status_code=400, detail=error_msg)

            results = result.get("results", [])

            return EANSearchResponse(
                results=results,
                total_found=len(results),
                account_type=request.account_type,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching products by EAN: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/pricing/recommendations", response_model=PricingRecommendationResponse)
async def get_pricing_recommendations(
    request: PricingRecommendationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PricingRecommendationResponse:
    """
    Get comprehensive pricing recommendations for a product.

    This endpoint combines commission estimates and Smart Deals eligibility
    to provide actionable pricing recommendations. It helps optimize pricing
    strategy by considering both profitability and competitiveness.

    Args:
        request: PricingRecommendationRequest with product details

    Returns:
        PricingRecommendationResponse with recommendations
    """
    try:
        config = get_emag_config(request.account_type)
        recommendations = []

        async with EmagApiClient(
            username=config.api_username,
            password=config.api_password,
            base_url=config.base_url,
        ) as client:
            # Get commission estimate
            commission_result = await client.get_commission_estimate(request.product_id)
            commission_value = None
            commission_percentage = None

            if not commission_result.get("isError"):
                data = commission_result.get("results", {})
                if isinstance(data, list) and data:
                    data = data[0]
                commission_value = data.get("value")
                commission_percentage = data.get("percentage")

                if commission_percentage:
                    recommendations.append(
                        f"eMAG commission: {commission_percentage:.1f}%"
                    )

            # Check Smart Deals eligibility
            smart_deals_result = await client.check_smart_deals_eligibility(
                request.product_id
            )
            smart_deals_eligible = False
            smart_deals_target = None

            if not smart_deals_result.get("isError"):
                data = smart_deals_result.get("results", {})
                if isinstance(data, list) and data:
                    data = data[0]
                smart_deals_eligible = data.get("isEligible", False)
                smart_deals_target = data.get("targetPrice")

                if smart_deals_eligible:
                    recommendations.append("✓ Product qualifies for Smart Deals badge")
                elif smart_deals_target and smart_deals_target < request.current_price:
                    discount_needed = (
                        (request.current_price - smart_deals_target)
                        / request.current_price
                    ) * 100
                    recommendations.append(
                        f"Reduce price by {discount_needed:.1f}% to qualify for Smart Deals"
                    )

            # Calculate recommended price
            recommended_price = None
            potential_savings = None

            if smart_deals_target and not smart_deals_eligible:
                recommended_price = smart_deals_target
                potential_savings = request.current_price - smart_deals_target
                recommendations.append(
                    f"Recommended price: {recommended_price:.2f} RON for Smart Deals eligibility"
                )

            # Add profit margin recommendation
            if commission_value and request.current_price:
                net_revenue = request.current_price - commission_value
                margin_percentage = (net_revenue / request.current_price) * 100
                recommendations.append(
                    "Net revenue after commission: "
                    f"{net_revenue:.2f} RON "
                    f"({margin_percentage:.1f}% margin)"
                )

            return PricingRecommendationResponse(
                product_id=request.product_id,
                current_price=request.current_price,
                recommended_price=recommended_price,
                commission_estimate=commission_value,
                smart_deals_eligible=smart_deals_eligible,
                smart_deals_target_price=smart_deals_target,
                potential_savings=potential_savings,
                recommendations=recommendations,
            )

    except Exception as e:
        logger.error(f"Error getting pricing recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/pricing/bulk-recommendations")
async def get_bulk_pricing_recommendations(
    product_ids: str = Query(..., description="Comma-separated product IDs"),
    account_type: str = Query(
        default="main", description="Account type: 'main' or 'fbe'"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Get pricing recommendations for multiple products.

    This endpoint processes multiple products in batch to provide
    pricing intelligence at scale.

    Args:
        product_ids: Comma-separated list of product IDs
        account_type: Account type ('main' or 'fbe')

    Returns:
        Dictionary with recommendations for each product
    """
    try:
        ids = [int(pid.strip()) for pid in product_ids.split(",") if pid.strip()]

        if len(ids) > 50:
            raise HTTPException(
                status_code=400, detail="Maximum 50 products allowed per request"
            )

        results = []
        config = get_emag_config(account_type)

        async with EmagApiClient(
            username=config.api_username,
            password=config.api_password,
            base_url=config.base_url,
        ) as client:
            for product_id in ids:
                try:
                    # Get commission
                    commission_result = await client.get_commission_estimate(product_id)
                    commission_data = {}
                    if not commission_result.get("isError"):
                        data = commission_result.get("results", {})
                        if isinstance(data, list) and data:
                            data = data[0]
                        commission_data = data

                    # Get Smart Deals
                    smart_deals_result = await client.check_smart_deals_eligibility(
                        product_id
                    )
                    smart_deals_data = {}
                    if not smart_deals_result.get("isError"):
                        data = smart_deals_result.get("results", {})
                        if isinstance(data, list) and data:
                            data = data[0]
                        smart_deals_data = data

                    results.append(
                        {
                            "product_id": product_id,
                            "commission": commission_data,
                            "smart_deals": smart_deals_data,
                        }
                    )

                except Exception as e:
                    logger.warning(f"Error processing product {product_id}: {e}")
                    results.append({"product_id": product_id, "error": str(e)})

        return {
            "results": results,
            "total_processed": len(results),
            "account_type": account_type,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bulk pricing recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
