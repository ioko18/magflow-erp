"""
Supplier Sheet Synchronization Endpoints.

Synchronizes verification status between SupplierProduct (1688) and
ProductSupplierSheet (Google Sheets).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models.product_supplier_sheet import ProductSupplierSheet
from app.models.supplier import SupplierProduct
from app.security.jwt import get_current_user

router = APIRouter(prefix="/suppliers", tags=["supplier-sync"])


@router.post("/{supplier_id}/products/{product_id}/sync-verification")
async def sync_supplier_verification(
    supplier_id: int,
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Synchronize verification status from SupplierProduct to ProductSupplierSheet.

    When a match is confirmed in SupplierProduct (1688), this endpoint updates
    the corresponding ProductSupplierSheet (Google Sheets) entry to mark it as verified.
    """

    # Get the SupplierProduct
    sp_query = (
        select(SupplierProduct)
        .options(selectinload(SupplierProduct.supplier))
        .options(selectinload(SupplierProduct.local_product))
        .where(
            and_(
                SupplierProduct.id == product_id,
                SupplierProduct.supplier_id == supplier_id,
            )
        )
    )
    sp_result = await db.execute(sp_query)
    supplier_product = sp_result.scalar_one_or_none()

    if not supplier_product:
        raise HTTPException(
            status_code=404,
            detail=f"Supplier product {product_id} not found for supplier {supplier_id}"
        )

    if not supplier_product.local_product:
        raise HTTPException(
            status_code=400,
            detail="Supplier product is not matched to a local product"
        )

    # Get the local product SKU
    local_product_sku = supplier_product.local_product.sku
    supplier_name = supplier_product.supplier.name if supplier_product.supplier else None

    if not supplier_name:
        raise HTTPException(
            status_code=400,
            detail="Supplier name not found"
        )

    # Find matching ProductSupplierSheet entry
    sheet_query = (
        select(ProductSupplierSheet)
        .where(
            and_(
                ProductSupplierSheet.sku == local_product_sku,
                ProductSupplierSheet.supplier_name.ilike(f"%{supplier_name}%"),
                ProductSupplierSheet.is_active.is_(True),
            )
        )
    )
    sheet_result = await db.execute(sheet_query)
    supplier_sheet = sheet_result.scalar_one_or_none()

    if not supplier_sheet:
        return {
            "status": "success",
            "message": (
                "No matching Google Sheets entry found - verification only in "
                "SupplierProduct"
            ),
            "supplier_product_verified": supplier_product.manual_confirmed,
            "sheet_entry_found": False,
        }

    # Sync verification status
    supplier_sheet.is_verified = supplier_product.manual_confirmed
    supplier_sheet.verified_by = str(current_user.id)
    supplier_sheet.verified_at = supplier_product.confirmed_at

    await db.commit()
    await db.refresh(supplier_sheet)

    return {
        "status": "success",
        "message": (
            "Verification status synchronized successfully. "
            "Supplier product verification status has been synced with "
            "the corresponding Google Sheets entry."
        ),
        "supplier_product_verified": supplier_product.manual_confirmed,
        "sheet_entry_verified": supplier_sheet.is_verified,
        "sheet_entry_found": True,
        "synced_data": {
            "sku": local_product_sku,
            "supplier_name": supplier_name,
            "verified_by": supplier_sheet.verified_by,
            "verified_at": (
                supplier_sheet.verified_at.isoformat()
                if supplier_sheet.verified_at
                else None
            ),
        }
    }


@router.post("/sync-all-verifications")
async def sync_all_verifications(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Bulk synchronize all verification statuses from SupplierProduct to ProductSupplierSheet.

    This is useful for initial setup or after bulk confirmations.
    """

    # Get all verified SupplierProducts
    sp_query = (
        select(SupplierProduct)
        .options(selectinload(SupplierProduct.supplier))
        .options(selectinload(SupplierProduct.local_product))
        .where(
            and_(
                SupplierProduct.manual_confirmed.is_(True),
                SupplierProduct.is_active.is_(True),
                SupplierProduct.local_product_id.isnot(None),
            )
        )
    )
    sp_result = await db.execute(sp_query)
    supplier_products = sp_result.scalars().all()

    synced_count = 0
    skipped_count = 0
    errors = []

    for sp in supplier_products:
        if not sp.local_product or not sp.supplier:
            skipped_count += 1
            continue

        local_product_sku = sp.local_product.sku
        supplier_name = sp.supplier.name

        # Find matching ProductSupplierSheet entry
        sheet_query = (
            select(ProductSupplierSheet)
            .where(
                and_(
                    ProductSupplierSheet.sku == local_product_sku,
                    ProductSupplierSheet.supplier_name.ilike(f"%{supplier_name}%"),
                    ProductSupplierSheet.is_active.is_(True),
                )
            )
        )
        sheet_result = await db.execute(sheet_query)
        supplier_sheet = sheet_result.scalar_one_or_none()

        if not supplier_sheet:
            skipped_count += 1
            continue

        try:
            # Sync verification status
            supplier_sheet.is_verified = True
            supplier_sheet.verified_by = str(current_user.id)
            supplier_sheet.verified_at = sp.confirmed_at
            synced_count += 1
        except Exception as e:
            errors.append({
                "sku": local_product_sku,
                "supplier": supplier_name,
                "error": str(e)
            })

    await db.commit()

    return {
        "status": "success",
        "message": f"Synchronized {synced_count} verification statuses",
        "synced_count": synced_count,
        "skipped_count": skipped_count,
        "total_processed": len(supplier_products),
        "errors": errors if errors else None,
    }
