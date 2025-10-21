"""
eMAG Product Publishing API Endpoints - v4.4.9

Complete product publishing functionality including:
- Draft and complete product creation
- Offer attachment to existing products
- EAN matching
- Category management
- Reference data (VAT, handling times)
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.emag_publishing_schemas import BatchProductUpdate
from app.services.emag.emag_batch_service import EmagBatchService
from app.services.emag.emag_category_service import EmagCategoryService
from app.services.emag.emag_ean_matching_service import EmagEANMatchingService
from app.services.emag.emag_product_publishing_service import (
    EmagProductPublishingService,
)
from app.services.emag.emag_reference_data_service import EmagReferenceDataService

logger = get_logger(__name__)
router = APIRouter()


# Request/Response Models


class DraftProductRequest(BaseModel):
    """Request model for creating draft product."""

    product_id: int = Field(..., description="Seller internal product ID")
    name: str = Field(..., min_length=1, max_length=255)
    brand: str = Field(..., min_length=1, max_length=255)
    part_number: str = Field(..., min_length=1, max_length=25)
    category_id: int | None = None
    ean: list[str] | None = None
    source_language: str | None = None


class ImageObject(BaseModel):
    """Image object for product."""

    display_type: int = Field(0, description="0=other, 1=main, 2=secondary")
    url: str = Field(..., min_length=1, max_length=1024)


class CharacteristicObject(BaseModel):
    """Characteristic object for product."""

    id: int = Field(..., description="eMAG characteristic ID")
    value: str = Field(..., min_length=1, max_length=255)
    tag: str | None = Field(None, max_length=255)


class FamilyObject(BaseModel):
    """Family object for product variants."""

    id: int = Field(..., description="Your family ID, 0 to remove from family")
    name: str | None = Field(None, max_length=255)
    family_type_id: int | None = None


class StockObject(BaseModel):
    """Stock object per warehouse."""

    warehouse_id: int = Field(..., description="Warehouse ID")
    value: int = Field(..., ge=0, description="Available quantity")


class HandlingTimeObject(BaseModel):
    """Handling time object per warehouse."""

    warehouse_id: int = Field(..., description="Warehouse ID")
    value: int = Field(..., ge=0, description="Days from order to dispatch")


class CompleteProductRequest(BaseModel):
    """Request model for creating complete product."""

    product_id: int
    category_id: int
    name: str = Field(..., min_length=1, max_length=255)
    part_number: str = Field(..., min_length=1, max_length=25)
    brand: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    images: list[ImageObject] = Field(..., min_items=1)
    characteristics: list[CharacteristicObject]
    sale_price: Decimal = Field(..., gt=0)
    vat_id: int
    stock: list[StockObject] = Field(..., min_items=1)
    handling_time: list[HandlingTimeObject] = Field(..., min_items=1)
    ean: list[str] | None = None
    warranty: int | None = Field(None, ge=0, le=255)
    url: str | None = Field(None, max_length=1024)
    source_language: str | None = None
    family: FamilyObject | None = None
    min_sale_price: Decimal | None = Field(None, gt=0)
    max_sale_price: Decimal | None = Field(None, gt=0)
    recommended_price: Decimal | None = Field(None, gt=0)


class AttachOfferRequest(BaseModel):
    """Request model for attaching offer to existing product."""

    product_id: int
    part_number_key: str | None = Field(None, max_length=50)
    ean: list[str] | None = None
    sale_price: Decimal = Field(..., gt=0)
    vat_id: int
    stock: list[StockObject] = Field(..., min_items=1)
    handling_time: list[HandlingTimeObject] = Field(..., min_items=1)
    status: int = Field(1, ge=0, le=2)
    min_sale_price: Decimal | None = None
    max_sale_price: Decimal | None = None
    recommended_price: Decimal | None = None
    warranty: int | None = None


class EANMatchRequest(BaseModel):
    """Request model for EAN matching."""

    eans: list[str] = Field(..., min_items=1, max_items=100)


# API Endpoints


@router.post("/draft")
async def create_draft_product(
    request: DraftProductRequest,
    account_type: str = Query(..., description="Account type: main or fbe"),
    current_user: User = Depends(get_current_user),
):
    """
    Create a draft product with minimal information.

    Draft products are not sent to eMAG validation until complete.
    Useful for quick product setup before adding full details.
    """
    try:
        async with EmagProductPublishingService(account_type) as service:
            result = await service.create_draft_product(
                product_id=request.product_id,
                name=request.name,
                brand=request.brand,
                part_number=request.part_number,
                category_id=request.category_id,
                ean=request.ean,
                source_language=request.source_language,
            )

            return {
                "status": "success",
                "message": "Draft product created successfully",
                "data": result,
            }

    except Exception as e:
        logger.error("Failed to create draft product: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/complete")
async def create_complete_product(
    request: CompleteProductRequest,
    account_type: str = Query(..., description="Account type: main or fbe"),
    current_user: User = Depends(get_current_user),
):
    """
    Create a complete product with full documentation and offer.

    This will be sent to eMAG for validation. Requires all mandatory fields
    including description, images, characteristics, and offer data.
    """
    try:
        async with EmagProductPublishingService(account_type) as service:
            result = await service.create_complete_product(
                product_id=request.product_id,
                category_id=request.category_id,
                name=request.name,
                part_number=request.part_number,
                brand=request.brand,
                description=request.description,
                images=[img.dict() for img in request.images],
                characteristics=[char.dict() for char in request.characteristics],
                sale_price=request.sale_price,
                vat_id=request.vat_id,
                stock=[s.dict() for s in request.stock],
                handling_time=[ht.dict() for ht in request.handling_time],
                ean=request.ean,
                warranty=request.warranty,
                url=request.url,
                source_language=request.source_language,
                family=request.family.dict() if request.family else None,
                min_sale_price=request.min_sale_price,
                max_sale_price=request.max_sale_price,
                recommended_price=request.recommended_price,
            )

            return {
                "status": "success",
                "message": f"Import completed: {result['imported']} products imported",
                "data": result,
            }

    except Exception as e:
        logger.error("Failed to create complete product: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/attach-offer")
async def attach_offer_to_existing_product(
    request: AttachOfferRequest,
    account_type: str = Query(..., description="Account type: main or fbe"),
    current_user: User = Depends(get_current_user),
):
    """
    Attach an offer to an existing eMAG product.

    Use either part_number_key OR ean to identify the existing product.
    This is faster than creating a new product if it already exists on eMAG.
    """
    try:
        if not request.part_number_key and not request.ean:
            raise HTTPException(
                status_code=400, detail="Either part_number_key or ean must be provided"
            )

        async with EmagProductPublishingService(account_type) as service:
            if request.part_number_key:
                result = await service.attach_offer_to_existing_product(
                    product_id=request.product_id,
                    part_number_key=request.part_number_key,
                    sale_price=request.sale_price,
                    vat_id=request.vat_id,
                    stock=[s.dict() for s in request.stock],
                    handling_time=[ht.dict() for ht in request.handling_time],
                    status=request.status,
                    min_sale_price=request.min_sale_price,
                    max_sale_price=request.max_sale_price,
                    recommended_price=request.recommended_price,
                    warranty=request.warranty,
                )
            else:
                result = await service.attach_offer_by_ean(
                    product_id=request.product_id,
                    ean=request.ean,
                    sale_price=request.sale_price,
                    vat_id=request.vat_id,
                    stock=[s.dict() for s in request.stock],
                    handling_time=[ht.dict() for ht in request.handling_time],
                    status=request.status,
                    min_sale_price=request.min_sale_price,
                    max_sale_price=request.max_sale_price,
                    recommended_price=request.recommended_price,
                    warranty=request.warranty,
                )

            return {
                "status": "success",
                "message": "Offer attached successfully",
                "data": result,
            }

    except Exception as e:
        logger.error("Failed to attach offer: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/match-ean")
async def match_products_by_ean(
    request: EANMatchRequest,
    account_type: str = Query(..., description="Account type: main or fbe"),
    current_user: User = Depends(get_current_user),
):
    """
    Match products by EAN codes (max 100 per request).

    Returns existing eMAG products that match the provided EANs,
    including information about whether you can add offers.
    """
    try:
        async with EmagEANMatchingService(account_type) as service:
            result = await service.bulk_find_products_by_eans(request.eans)

            return {
                "status": "success",
                "message": (
                    f"Found {result['products_found']} products for "
                    f"{result['eans_searched']} EANs"
                ),
                "data": result,
            }

    except Exception as e:
        logger.error("Failed to match EANs: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/categories")
async def get_categories(
    current_page: int = Query(1, ge=1),
    items_per_page: int = Query(100, ge=1, le=100),
    language: str = Query("ro", description="Language: en, ro, hu, bg, pl, gr, de"),
    account_type: str = Query("main", description="Account type: main or fbe"),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of eMAG categories with pagination.

    Returns categories with basic information. Use /categories/{id} for details.
    """
    try:
        async with EmagCategoryService(account_type) as service:
            result = await service.get_categories(
                current_page=current_page,
                items_per_page=items_per_page,
                language=language,
            )

            return {"status": "success", "data": result}

    except Exception as e:
        logger.error("Failed to fetch categories: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/categories/allowed")
async def get_allowed_categories(
    language: str = Query("ro", description="Language: en, ro, hu, bg, pl, gr, de"),
    account_type: str = Query("main", description="Account type: main or fbe"),
    current_user: User = Depends(get_current_user),
):
    """
    Get only categories where seller is allowed to post.

    Filters categories to show only those with is_allowed = 1.
    """
    try:
        async with EmagCategoryService(account_type) as service:
            result = await service.get_allowed_categories(language=language)

            return {
                "status": "success",
                "message": f"Found {len(result)} allowed categories",
                "data": {"categories": result, "count": len(result)},
            }

    except Exception as e:
        logger.error("Failed to fetch allowed categories: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/categories/{category_id}")
async def get_category_details(
    category_id: int,
    language: str = Query("ro", description="Language: en, ro, hu, bg, pl, gr, de"),
    account_type: str = Query("main", description="Account type: main or fbe"),
    current_user: User = Depends(get_current_user),
):
    """
    Get detailed category information including characteristics and family types.

    This is required before publishing products to understand mandatory fields.
    """
    try:
        async with EmagCategoryService(account_type) as service:
            result = await service.get_category_by_id(
                category_id=category_id, language=language
            )

            return {"status": "success", "data": result}

    except Exception as e:
        logger.error("Failed to fetch category %d: %s", category_id, str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/vat-rates")
async def get_vat_rates(
    account_type: str = Query("main", description="Account type: main or fbe"),
    current_user: User = Depends(get_current_user),
):
    """
    Get available VAT rates.

    Required when creating offers. Results are cached for 7 days.
    """
    try:
        async with EmagReferenceDataService(account_type) as service:
            result = await service.get_vat_rates()

            return {
                "status": "success",
                "data": {"vat_rates": result, "count": len(result)},
            }

    except Exception as e:
        logger.error("Failed to fetch VAT rates: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/handling-times")
async def get_handling_times(
    account_type: str = Query("main", description="Account type: main or fbe"),
    current_user: User = Depends(get_current_user),
):
    """
    Get available handling time values.

    Required when creating offers. Results are cached for 7 days.
    """
    try:
        async with EmagReferenceDataService(account_type) as service:
            result = await service.get_handling_times()

            return {
                "status": "success",
                "data": {"handling_times": result, "count": len(result)},
            }

    except Exception as e:
        logger.error("Failed to fetch handling times: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/batch/update-offers")
async def batch_update_offers(
    batch_data: BatchProductUpdate,
    account_type: str = Query("main", description="Account type: main or fbe"),
    current_user: User = Depends(get_current_user),
):
    """
    Update multiple offers in batches (10x performance improvement).

    Optimal batch size: 100 items per batch.
    Rate limiting: 3 requests/second.
    """
    try:
        async with EmagBatchService(account_type) as service:
            result = await service.batch_update_offers(batch_data.products)

            return {
                "status": "success",
                "message": (
                    "Batch update completed: "
                    f"{result['successful_batches']}"
                    "/"
                    f"{result['total_batches']}"
                    " batches successful"
                ),
                "data": result,
            }

    except Exception as e:
        logger.error("Batch update failed: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/batch/status")
async def get_batch_status(
    account_type: str = Query("main", description="Account type: main or fbe"),
    current_user: User = Depends(get_current_user),
):
    """
    Get current batch processing status and metrics.

    Includes performance metrics and health status.
    """
    try:
        async with EmagBatchService(account_type) as service:
            status = await service.get_batch_status()

            return {"status": "success", "data": status}

    except Exception as e:
        logger.error("Failed to get batch status: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
