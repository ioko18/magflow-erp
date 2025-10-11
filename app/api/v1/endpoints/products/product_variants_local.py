"""
Local Product Variants Management.

Handles creation and management of product variants in local database
BEFORE they are published to eMAG.

Use Case:
- You want to track EMG331-V2 before publishing to eMAG
- Create local record with variant relationship
- After eMAG publish, sync will update with real data
"""


from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.product import Product
from app.models.user import User
from app.security.jwt import get_current_user
from app.services.product.product_relationship_service import ProductRelationshipService

router = APIRouter(prefix="/product-variants-local", tags=["product-variants-local"])


# ============================================================================
# Request/Response Models
# ============================================================================


class CreateLocalVariantRequest(BaseModel):
    """Request to create a local product variant before eMAG publishing."""

    original_sku: str = Field(..., description="Original product SKU (e.g., EMG331)")
    new_sku: str = Field(..., description="New variant SKU (e.g., EMG331-V2)")
    new_name: str = Field(..., description="Product name for new variant")
    new_ean: str | None = Field(None, description="EAN code (if different)")
    base_price: float = Field(..., description="Base price")
    brand: str | None = Field(None, description="Brand name")
    manufacturer: str | None = Field(None, description="Manufacturer")
    description: str | None = Field(None, description="Product description")
    reason: str = Field(..., description="Reason for creating variant")
    account_type: str = Field("main", description="Target account: main or fbe")


class LocalVariantResponse(BaseModel):
    """Response after creating local variant."""

    local_product_id: int
    sku: str
    name: str
    variant_group_id: str
    status: str
    next_steps: list[str]


# ============================================================================
# Create Local Variant Endpoint
# ============================================================================


@router.post("/create", response_model=LocalVariantResponse)
async def create_local_variant(
    request: CreateLocalVariantRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a local product variant BEFORE publishing to eMAG.

    This allows you to:
    1. Track the variant relationship immediately
    2. See it in Products page alongside original
    3. Have a record ready for when you publish to eMAG

    Workflow:
    1. Call this endpoint to create local variant
    2. Publish to eMAG manually
    3. Run sync - system will match by SKU and update
    4. Variant relationship is maintained

    Example for EMG331:
    ```json
    {
      "original_sku": "EMG331",
      "new_sku": "EMG331-V2",
      "new_name": "Generator XR2206 Premium",
      "new_ean": "8266294692465",
      "base_price": 45.00,
      "brand": "Generic",
      "description": "Premium version...",
      "reason": "Competitor attached to original",
      "account_type": "main"
    }
    ```
    """
    # Check if SKU already exists
    existing_query = select(Product).where(Product.sku == request.new_sku)
    result = await db.execute(existing_query)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Product with SKU {request.new_sku} already exists (ID: {existing.id})",
        )

    # Get original product for reference
    original_query = select(Product).where(Product.sku == request.original_sku)
    original_result = await db.execute(original_query)
    original = original_result.scalar_one_or_none()

    # Create new local product
    new_product = Product(
        sku=request.new_sku,
        name=request.new_name,
        ean=request.new_ean,
        base_price=request.base_price,
        brand=request.brand or (original.brand if original else None),
        manufacturer=request.manufacturer
        or (original.manufacturer if original else None),
        description=request.description,
        currency="RON",
        is_active=True,
        # Copy some fields from original if available
        emag_category_id=original.emag_category_id if original else None,
        emag_warranty_months=original.emag_warranty_months if original else None,
    )

    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)

    # Create variant relationship
    relationship_service = ProductRelationshipService(db)

    try:
        variant_group_id = await relationship_service.create_variant_group(
            original_sku=request.original_sku,
            variant_skus=[request.new_sku],
            reason=request.reason,
        )

        # Try to create genealogy
        try:
            # Check if family exists
            family_tree = await relationship_service.get_product_family_tree(
                request.original_sku
            )

            if "error" in family_tree:
                # Create new family
                family_id = await relationship_service.create_product_family(
                    root_sku=request.original_sku,
                    family_name=f"{request.original_sku} Product Family",
                    product_type="local",
                )
            else:
                family_id = family_tree.get("family_id")

            # Add to family
            await relationship_service.add_product_to_family(
                family_id=family_id,
                sku=request.new_sku,
                parent_sku=request.original_sku,
                supersede_reason=request.reason,
                product_type="local",
            )
        except Exception:
            # Genealogy is optional
            pass

    except Exception as e:
        # Rollback product creation if variant creation fails
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to create variant relationship: {str(e)}"
        )

    return LocalVariantResponse(
        local_product_id=new_product.id,
        sku=new_product.sku,
        name=new_product.name,
        variant_group_id=str(variant_group_id),
        status="created_locally",
        next_steps=[
            f"1. Local product created with ID {new_product.id}",
            "2. Product visible in Products page",
            "3. Publish to eMAG manually with this SKU",
            "4. Run sync to update with eMAG data",
            "5. Variant relationship will be maintained",
        ],
    )


# ============================================================================
# List Local Variants Endpoint
# ============================================================================


@router.get("/list")
async def list_local_variants(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all local products that are variants (not yet on eMAG).

    Shows products that:
    - Exist in local database
    - Are part of a variant group
    - May or may not be synced to eMAG yet
    """
    relationship_service = ProductRelationshipService(db)

    # Get all products
    query = select(Product).where(Product.is_active)
    result = await db.execute(query)
    products = result.scalars().all()

    # Check which are variants
    local_variants = []
    for product in products:
        variants = await relationship_service.get_product_variants(product.sku)
        if len(variants) > 1:  # Is part of a variant group
            local_variants.append(
                {
                    "id": product.id,
                    "sku": product.sku,
                    "name": product.name,
                    "base_price": product.base_price,
                    "is_active": product.is_active,
                    "variant_count": len(variants),
                    "variants": variants,
                }
            )

    return {
        "status": "success",
        "data": {"local_variants": local_variants, "total": len(local_variants)},
    }


# ============================================================================
# Update Local Variant After eMAG Publish
# ============================================================================


@router.patch("/{sku}/after-emag-publish")
async def update_after_emag_publish(
    sku: str,
    emag_part_number_key: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update local variant after it's been published to eMAG.

    Use this to:
    - Add the part_number_key that eMAG assigned
    - Mark that it's been published
    - Prepare for sync to update full data

    After calling this, run sync to get complete eMAG data.
    """
    query = select(Product).where(Product.sku == sku)
    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail=f"Product {sku} not found")

    if emag_part_number_key:
        product.emag_part_number_key = emag_part_number_key

    await db.commit()
    await db.refresh(product)

    return {
        "status": "success",
        "message": f"Product {sku} updated with eMAG data",
        "data": {
            "sku": product.sku,
            "emag_part_number_key": product.emag_part_number_key,
            "next_step": "Run sync to get complete eMAG data",
        },
    }


# ============================================================================
# Delete Local Variant (if not published)
# ============================================================================


@router.delete("/{sku}")
async def delete_local_variant(
    sku: str,
    force: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a local variant if you decide not to publish it.

    Safety:
    - Won't delete if emag_part_number_key exists (already on eMAG)
    - Use force=true to delete anyway
    """
    query = select(Product).where(Product.sku == sku)
    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail=f"Product {sku} not found")

    if product.emag_part_number_key and not force:
        raise HTTPException(
            status_code=400,
            detail=f"Product has eMAG PNK ({product.emag_part_number_key}). Use force=true to delete anyway.",
        )

    await db.delete(product)
    await db.commit()

    return {
        "status": "success",
        "message": f"Product {sku} deleted",
        "warning": "Variant relationship still exists in tracking tables",
    }
