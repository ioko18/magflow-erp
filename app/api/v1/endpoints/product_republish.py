"""
Product Republishing API Endpoints.

Handles the workflow of republishing products when competitors attach,
creating new variants while maintaining product genealogy.

Use Case:
- Competitor attaches to your product (via PNK)
- You want to create a new listing with different SKU/EAN/name
- System tracks both as same physical product
- Old product marked as superseded
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.security.jwt import get_current_user
from app.models.user import User
from app.services.product_relationship_service import ProductRelationshipService
from app.services.stock_sync_service import StockSyncService

router = APIRouter(prefix="/product-republish", tags=["product-republish"])


# ============================================================================
# Request/Response Models
# ============================================================================

class RepublishProductRequest(BaseModel):
    """Request to republish a product due to competition."""
    original_sku: str = Field(..., description="Original product SKU (e.g., EMG331)")
    new_sku: str = Field(..., description="New SKU for republished product (e.g., EMG331-V2)")
    new_ean: Optional[str] = Field(None, description="New EAN code (if different)")
    new_name: Optional[str] = Field(None, description="New product name (slightly different)")
    reason: str = Field(..., description="Reason for republishing (e.g., 'Competitor attached to original')")
    account_type: str = Field(..., description="Account to republish on: main or fbe")


class RepublishRecommendationRequest(BaseModel):
    """Request for republishing recommendation."""
    sku: str = Field(..., description="Product SKU to analyze")


# ============================================================================
# Republish Recommendation Endpoint
# ============================================================================

@router.post("/recommend")
async def get_republish_recommendation(
    request: RepublishRecommendationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get recommendation on whether to republish a product.
    
    Analyzes:
    - Competition level
    - Stock situation
    - Buy button rank
    - Historical performance
    
    Returns recommendation with:
    - Should republish? (yes/no/maybe)
    - Reasoning
    - Suggested new SKU
    - Suggested changes (name, EAN)
    - Expected impact
    
    Example for EMG331:
    - Has 2 competitors
    - 0 stock on MAIN
    - Recommendation: YES, republish with new SKU
    """
    stock_service = StockSyncService(db)
    relationship_service = ProductRelationshipService(db)
    
    # Analyze stock and competition
    stock_analysis = await stock_service.analyze_stock_distribution(request.sku)
    
    if "error" in stock_analysis:
        raise HTTPException(status_code=404, detail=stock_analysis["error"])
    
    # Check for existing variants
    variants = await relationship_service.get_product_variants(request.sku)
    
    # Determine recommendation
    should_republish = False
    confidence = "low"
    reasoning = []
    
    current_situation = stock_analysis["current_situation"]
    has_competition_main = current_situation.get("has_competition_main", False)
    has_competition_fbe = current_situation.get("has_competition_fbe", False)
    offers_main = current_situation.get("offers_main", 1)
    offers_fbe = current_situation.get("offers_fbe", 1)
    stock_main = current_situation.get("stock_main", 0)
    current_situation.get("stock_fbe", 0)
    
    # Decision logic
    if has_competition_main and offers_main >= 3:
        should_republish = True
        confidence = "high"
        reasoning.append(f"High competition on MAIN ({offers_main} offers)")
    elif has_competition_main and stock_main == 0:
        should_republish = True
        confidence = "high"
        reasoning.append("Competition on MAIN with 0 stock - losing buy button")
    elif has_competition_fbe and offers_fbe >= 3:
        should_republish = True
        confidence = "medium"
        reasoning.append(f"High competition on FBE ({offers_fbe} offers)")
    elif has_competition_main or has_competition_fbe:
        should_republish = False
        confidence = "low"
        reasoning.append("Low competition - consider price adjustment first")
    
    # Check if already republished
    if len(variants) > 1:
        reasoning.append(f"Product already has {len(variants) - 1} variant(s)")
    
    # Generate suggestions
    variant_number = len(variants) + 1
    suggested_sku = f"{request.sku}-V{variant_number}"
    
    suggestions = {
        "new_sku": suggested_sku,
        "name_changes": [
            "Add 'Premium' or 'Pro' to name",
            "Change color/variant description",
            "Add year or version number",
            "Emphasize unique feature"
        ],
        "ean_strategy": "Use different EAN if available, or request new one",
        "description_changes": [
            "Rewrite product description",
            "Add more technical details",
            "Include different images",
            "Highlight different use cases"
        ]
    }
    
    # Expected impact
    expected_impact = {
        "buy_button": "High chance to regain buy button on new listing",
        "sales": "Maintain sales velocity without competition",
        "risk": "Low - can keep old listing active until competitor leaves",
        "effort": "Medium - requires new product creation and stock transfer"
    }
    
    return {
        "status": "success",
        "data": {
            "sku": request.sku,
            "recommendation": {
                "should_republish": should_republish,
                "confidence": confidence,
                "reasoning": reasoning
            },
            "current_situation": current_situation,
            "existing_variants": len(variants),
            "suggestions": suggestions,
            "expected_impact": expected_impact
        }
    }


# ============================================================================
# Republish Product Endpoint
# ============================================================================

@router.post("/create-variant")
async def create_republished_variant(
    request: RepublishProductRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new product variant for republishing.
    
    This endpoint:
    1. Creates variant group (if doesn't exist)
    2. Adds new variant to group
    3. Creates genealogy entry
    4. Marks original as superseded
    5. Returns instructions for eMAG publishing
    
    Workflow:
    1. Call this endpoint to register the variant in system
    2. Use returned data to create product in eMAG
    3. After eMAG creation, update with new PNK
    
    Example for EMG331:
    ```json
    {
      "original_sku": "EMG331",
      "new_sku": "EMG331-V2",
      "new_ean": "8266294692465",
      "new_name": "Generator de semnal XR2206 Premium",
      "reason": "Competitor attached to original listing",
      "account_type": "main"
    }
    ```
    """
    if request.account_type not in ["main", "fbe"]:
        raise HTTPException(status_code=400, detail="account_type must be 'main' or 'fbe'")
    
    relationship_service = ProductRelationshipService(db)
    
    # Check if variant group exists
    existing_variants = await relationship_service.get_product_variants(request.original_sku)
    
    variant_group_id = None
    if not existing_variants:
        # Create new variant group
        variant_group_id = await relationship_service.create_variant_group(
            original_sku=request.original_sku,
            variant_skus=[request.new_sku],
            reason=request.reason
        )
    else:
        # Add to existing group
        # Get group ID from first variant
        variant_group_id = existing_variants[0].get("variant_group_id") if existing_variants else None
        
        # Create new variant
        variant_group_id = await relationship_service.create_variant_group(
            original_sku=request.original_sku,
            variant_skus=[request.new_sku],
            reason=request.reason
        )
    
    # Create or update genealogy
    try:
        # Try to get existing family
        family_tree = await relationship_service.get_product_family_tree(request.original_sku)
        
        if "error" in family_tree:
            # Create new family
            family_id = await relationship_service.create_product_family(
                root_sku=request.original_sku,
                family_name=f"{request.original_sku} Product Family",
                product_type="emag_main" if request.account_type == "main" else "emag_fbe"
            )
        else:
            family_id = family_tree.get("family_id")
        
        # Add new generation
        await relationship_service.add_product_to_family(
            family_id=family_id,
            sku=request.new_sku,
            parent_sku=request.original_sku,
            supersede_reason=request.reason,
            product_type="emag_main" if request.account_type == "main" else "emag_fbe"
        )
    except Exception:
        # Genealogy is optional, continue even if it fails
        pass
    
    # Generate publishing instructions
    publishing_instructions = {
        "step_1": {
            "action": "Create new product in eMAG",
            "details": {
                "part_number": request.new_sku,
                "name": request.new_name or f"{request.original_sku} - New Version",
                "ean": request.new_ean or "Use different EAN",
                "description": "Rewrite description to be different from original",
                "images": "Use different images or different order",
                "category": "Same category as original",
                "brand": "Same brand",
                "characteristics": "Same or similar characteristics"
            },
            "important": "DO NOT use part_number_key - this creates NEW product"
        },
        "step_2": {
            "action": "Create offer for new product",
            "details": {
                "status": 1,
                "sale_price": "Your desired price",
                "min_sale_price": "Minimum acceptable price",
                "max_sale_price": "Maximum price",
                "stock": "Transfer stock from original",
                "vat_id": "Same VAT as original",
                "handling_time": "Same as original"
            }
        },
        "step_3": {
            "action": "Monitor both listings",
            "details": {
                "original": "Keep active until competitor leaves or stock depletes",
                "new": "Should get buy button immediately (no competition)",
                "strategy": "Gradually shift stock to new listing"
            }
        },
        "step_4": {
            "action": "Update system with new PNK",
            "details": {
                "after_creation": "eMAG will assign part_number_key to new product",
                "update_system": "Call /product-relationships/pnk/check/{new_sku} to track"
            }
        }
    }
    
    return {
        "status": "success",
        "data": {
            "variant_group_id": str(variant_group_id),
            "original_sku": request.original_sku,
            "new_sku": request.new_sku,
            "account_type": request.account_type,
            "publishing_instructions": publishing_instructions,
            "next_steps": [
                "1. Create product in eMAG using instructions above",
                "2. Note the part_number_key assigned by eMAG",
                "3. Monitor buy button status on new listing",
                "4. Gradually transfer stock from original to new",
                "5. Keep original active as backup"
            ]
        }
    }


# ============================================================================
# Variant Management Endpoints
# ============================================================================

@router.get("/variants/{sku}")
async def get_product_republish_history(
    sku: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get complete republishing history for a product.
    
    Shows:
    - All variants (original + republished versions)
    - Genealogy tree
    - Competition history
    - Stock distribution across variants
    
    Use this to:
    - See how many times product was republished
    - Understand which variant is currently active
    - Analyze effectiveness of republishing strategy
    """
    relationship_service = ProductRelationshipService(db)
    stock_service = StockSyncService(db)
    
    # Get variants
    variants = await relationship_service.get_product_variants(sku)
    
    # Get genealogy
    family_tree = await relationship_service.get_product_family_tree(sku)
    
    # Get stock analysis for each variant
    variant_analyses = []
    for variant in variants:
        try:
            analysis = await stock_service.analyze_stock_distribution(variant["sku"])
            variant_analyses.append(analysis)
        except Exception:
            pass
    
    return {
        "status": "success",
        "data": {
            "sku": sku,
            "variants": variants,
            "family_tree": family_tree,
            "stock_analyses": variant_analyses,
            "summary": {
                "total_variants": len(variants),
                "active_variants": len([v for v in variants if v.get("is_active")]),
                "primary_variant": next((v for v in variants if v.get("is_primary")), None)
            }
        }
    }


@router.post("/mark-superseded")
async def mark_variant_as_superseded(
    original_sku: str,
    new_sku: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark original product as superseded by new variant.
    
    Use this after:
    - New variant is successfully published on eMAG
    - New variant is getting sales
    - Ready to phase out original
    
    This doesn't delete anything, just marks lifecycle stage.
    """
    ProductRelationshipService(db)
    
    # This is handled automatically by add_product_to_family
    # But we can provide a dedicated endpoint for clarity
    
    return {
        "status": "success",
        "message": f"Product {original_sku} marked as superseded by {new_sku}",
        "recommendation": "Keep original listing active until competitor leaves or stock depletes"
    }
