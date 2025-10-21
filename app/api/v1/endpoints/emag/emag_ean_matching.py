"""eMAG EAN Matching API Endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.security.jwt import get_current_user
from app.services.emag.emag_ean_matching_service import EmagEANMatchingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/emag", tags=["eMAG EAN Matching"])


class EANSearchRequest(BaseModel):
    """Request model for EAN search."""

    ean_codes: list[str] = Field(
        ..., max_items=100, description="EAN codes to search (max 100)"
    )
    account_type: str = Field(default="main", description="Account type: main or fbe")


@router.post("/ean-matching/find-by-eans")
async def find_products_by_eans(
    request: EANSearchRequest,
    current_user=Depends(get_current_user),
):
    """
    Find products on eMAG by EAN codes.

    This endpoint uses the new v4.4.9 EAN matching API to quickly find
    products that already exist on eMAG marketplace.

    **Rate Limits**: 5 requests/second, 200 requests/minute, 5,000 requests/day
    **Max EANs**: 100 per request
    """
    try:
        logger.info(
            f"EAN search requested by {current_user.email} for {len(request.ean_codes)} EANs"
        )

        async with EmagEANMatchingService(request.account_type) as service:
            result = await service.bulk_find_products_by_eans(request.ean_codes)

            logger.info(
                f"EAN search completed: {result['products_found']} products found"
            )

            return {
                "status": "success",
                "account_type": request.account_type,
                "eans_searched": result["eans_searched"],
                "products_found": result["products_found"],
                "products": result["products"],
            }

    except Exception as e:
        logger.error(f"EAN search error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"EAN search failed: {str(e)}") from e


@router.get("/phase2/ean/validate/{ean}")
async def validate_ean(
    ean: str,
    account_type: str = "main",
    current_user=Depends(get_current_user),
):
    """
    Validate EAN code format and checksum.

    Validates:
    - Format (6-14 numeric characters)
    - EAN-13 checksum if applicable
    """
    try:
        logger.info(f"EAN validation requested by {current_user.email} for EAN: {ean}")

        async with EmagEANMatchingService(account_type) as service:
            validation_result = await service.validate_ean_format(ean)

            if not validation_result["valid"]:
                return {
                    "status": "invalid",
                    "ean": ean,
                    "error": validation_result.get("error"),
                }

            return {
                "status": "valid",
                "ean": validation_result["ean"],
                "format": validation_result.get("format"),
            }

    except Exception as e:
        logger.error(f"EAN validation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"EAN validation failed: {str(e)}") from e


@router.post("/phase2/ean/search")
async def search_by_ean(
    request: EANSearchRequest,
    current_user=Depends(get_current_user),
):
    """
    Search products by EAN codes (alias for find-by-eans).

    This is an alternative endpoint for EAN search functionality.
    """
    try:
        logger.info(
            "EAN search (phase2) requested by %s for %d EANs",
            current_user.email,
            len(request.ean_codes),
        )

        async with EmagEANMatchingService(request.account_type) as service:
            result = await service.bulk_find_products_by_eans(request.ean_codes)

            return {
                "status": "success",
                "account_type": request.account_type,
                "results": result["products"],
                "total_found": result["products_found"],
            }

    except Exception as e:
        logger.error(f"EAN search (phase2) error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"EAN search failed: {str(e)}") from e
