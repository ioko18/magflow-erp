"""
Product Relationships API Endpoints.

Provides endpoints for:
- PNK consistency checking
- Competition monitoring
- Product variant management
- Product genealogy tracking
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.user import User
from app.security.jwt import get_current_user
from app.services.product.product_relationship_service import ProductRelationshipService

router = APIRouter(prefix="/product-relationships", tags=["product-relationships"])


# ============================================================================
# Request/Response Models
# ============================================================================


class PNKConsistencyResponse(BaseModel):
    """Response for PNK consistency check."""

    sku: str
    is_consistent: bool
    pnk_main: str | None
    pnk_fbe: str | None
    status: str
    issues: list[str]
    has_main: bool
    has_fbe: bool


class CompetitionCheckResponse(BaseModel):
    """Response for competition check."""

    has_competitors: bool
    number_of_offers: int
    your_rank: int | None
    previous_offer_count: int
    new_competitors: int
    requires_action: bool
    recommendation: str | None
    best_competitor_price: float | None
    your_price: float | None


class CreateVariantGroupRequest(BaseModel):
    """Request to create a variant group."""

    original_sku: str = Field(..., description="Original/primary SKU")
    variant_skus: list[str] = Field(..., description="List of variant SKUs")
    reason: str = Field(
        default="Re-published due to competition", description="Reason for variants"
    )


class CreateProductFamilyRequest(BaseModel):
    """Request to create a product family."""

    root_sku: str = Field(..., description="Root product SKU")
    family_name: str = Field(..., description="Human-readable family name")
    product_type: str = Field(
        default="local", description="Product type: local, emag_main, emag_fbe"
    )


class AddToFamilyRequest(BaseModel):
    """Request to add product to family."""

    family_id: str = Field(..., description="Family UUID")
    sku: str = Field(..., description="New product SKU")
    parent_sku: str = Field(..., description="Parent product SKU")
    supersede_reason: str = Field(..., description="Why parent was superseded")
    product_type: str = Field(default="emag_main", description="Product type")


# ============================================================================
# PNK Consistency Endpoints
# ============================================================================


@router.get("/pnk/check/{sku}", response_model=PNKConsistencyResponse)
async def check_pnk_consistency(
    sku: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Check if part_number_key is consistent between MAIN and FBE accounts.

    This endpoint verifies that:
    - Both MAIN and FBE products exist
    - Both have PNK assigned
    - PNK values match between accounts
    """
    service = ProductRelationshipService(db)
    result = await service.check_pnk_consistency(sku)
    return result


@router.get("/pnk/inconsistencies")
async def get_pnk_inconsistencies(
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all products with PNK inconsistencies.

    Returns products where:
    - PNK is missing on one or both accounts
    - PNK values differ between MAIN and FBE
    """
    service = ProductRelationshipService(db)
    inconsistencies = await service.get_pnk_inconsistencies(limit)

    return {
        "status": "success",
        "data": {
            "inconsistencies": inconsistencies,
            "total": len(inconsistencies),
        },
    }


class BulkCheckRequest(BaseModel):
    """Request for bulk PNK check."""

    skus: list[str] = Field(..., description="List of SKUs to check")


@router.post("/pnk/bulk-check")
async def bulk_check_pnk_consistency(
    request: BulkCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Check PNK consistency for multiple products at once.

    Useful for batch validation after sync operations.
    """
    service = ProductRelationshipService(db)
    results = []

    for sku in request.skus:
        try:
            result = await service.check_pnk_consistency(sku)
            results.append(result)
        except Exception as e:
            results.append({"sku": sku, "error": str(e)})

    inconsistent_count = sum(1 for r in results if not r.get("is_consistent", True))

    return {
        "status": "success",
        "data": {
            "results": results,
            "total_checked": len(results),
            "inconsistent_count": inconsistent_count,
        },
    }


# ============================================================================
# Competition Monitoring Endpoints
# ============================================================================


@router.get("/competition/check/{product_id}")
async def check_product_competition(
    product_id: UUID,
    account_type: str = Query(..., description="Account type: main or fbe"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Check if competitors have attached to this product.

    Monitors:
    - Number of offers (sellers on this product)
    - Your buy button rank
    - New competitors since last check
    - Provides recommendations for action
    """
    if account_type not in ["main", "fbe"]:
        raise HTTPException(status_code=400, detail="Invalid account_type")

    service = ProductRelationshipService(db)
    result = await service.check_competition(product_id, account_type)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return {"status": "success", "data": result}


@router.get("/competition/alerts")
async def get_competition_alerts(
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get products with competition that require action.

    Returns products where:
    - Multiple competitors have attached
    - Your rank has dropped
    - New competitors appeared recently
    """
    service = ProductRelationshipService(db)
    alerts = await service.get_products_with_competition(limit)

    return {
        "status": "success",
        "data": {
            "alerts": alerts,
            "total": len(alerts),
        },
    }


# ============================================================================
# Product Variants Endpoints
# ============================================================================


@router.post("/variants/create-group")
async def create_variant_group(
    request: CreateVariantGroupRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a variant group linking multiple SKUs as the same physical product.

    Use this when you need to re-publish a product with different:
    - SKU (due to competition)
    - EAN (to avoid conflicts)
    - Name (slight variations)

    All variants will be tracked as the same physical product.
    """
    service = ProductRelationshipService(db)

    try:
        variant_group_id = await service.create_variant_group(
            original_sku=request.original_sku,
            variant_skus=request.variant_skus,
            reason=request.reason,
        )

        return {
            "status": "success",
            "data": {
                "variant_group_id": str(variant_group_id),
                "original_sku": request.original_sku,
                "variant_count": len(request.variant_skus),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/variants/{sku}")
async def get_product_variants(
    sku: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all variants of a product.

    Returns all SKUs that represent the same physical product,
    including the original and all re-published versions.
    """
    service = ProductRelationshipService(db)
    variants = await service.get_product_variants(sku)

    return {
        "status": "success",
        "data": {
            "sku": sku,
            "variants": variants,
            "total_variants": len(variants),
        },
    }


# ============================================================================
# Product Genealogy Endpoints
# ============================================================================


@router.post("/genealogy/create-family")
async def create_product_family(
    request: CreateProductFamilyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new product family (genealogy tree).

    Use this to track the complete lifecycle of a product across
    multiple re-publications and variations.
    """
    service = ProductRelationshipService(db)

    try:
        family_id = await service.create_product_family(
            root_sku=request.root_sku,
            family_name=request.family_name,
            product_type=request.product_type,
        )

        return {
            "status": "success",
            "data": {
                "family_id": str(family_id),
                "family_name": request.family_name,
                "root_sku": request.root_sku,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/genealogy/add-to-family")
async def add_product_to_family(
    request: AddToFamilyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add a new generation to a product family.

    Use this when you re-publish a product due to:
    - Competition (other sellers attached)
    - Price wars
    - Product improvements

    This creates a parent-child relationship and marks the parent as superseded.
    """
    service = ProductRelationshipService(db)

    try:
        genealogy_id = await service.add_product_to_family(
            family_id=UUID(request.family_id),
            sku=request.sku,
            parent_sku=request.parent_sku,
            supersede_reason=request.supersede_reason,
            product_type=request.product_type,
        )

        return {
            "status": "success",
            "data": {
                "genealogy_id": str(genealogy_id),
                "sku": request.sku,
                "parent_sku": request.parent_sku,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/genealogy/family-tree/{sku}")
async def get_product_family_tree(
    sku: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the complete family tree for a product.

    Returns:
    - All generations of the product
    - Parent-child relationships
    - Lifecycle stages
    - Supersession history
    """
    service = ProductRelationshipService(db)
    tree = await service.get_product_family_tree(sku)

    if "error" in tree:
        raise HTTPException(status_code=404, detail=tree["error"])

    return {"status": "success", "data": tree}


# ============================================================================
# Dashboard & Analytics Endpoints
# ============================================================================


@router.get("/dashboard/summary")
async def get_relationships_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get summary dashboard for product relationships.

    Provides overview of:
    - PNK inconsistencies
    - Competition alerts
    - Active variant groups
    - Product families
    """
    service = ProductRelationshipService(db)

    # Get counts
    inconsistencies = await service.get_pnk_inconsistencies(limit=1000)
    competition_alerts = await service.get_products_with_competition(limit=1000)

    return {
        "status": "success",
        "data": {
            "pnk_inconsistencies": {
                "total": len(inconsistencies),
                "critical": len(
                    [i for i in inconsistencies if i["status"] == "inconsistent"]
                ),
                "missing": len(
                    [i for i in inconsistencies if i["status"] == "missing"]
                ),
            },
            "competition": {
                "total_alerts": len(competition_alerts),
                "requires_action": len(
                    [a for a in competition_alerts if a.get("action_taken") is None]
                ),
            },
        },
    }
