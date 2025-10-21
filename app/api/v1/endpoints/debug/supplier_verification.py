"""
Debug endpoint to check supplier product verification status.
This helps diagnose why verified suppliers might not appear in Low Stock Products page.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models.product import Product
from app.models.supplier import SupplierProduct
from app.security.jwt import get_current_user

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/supplier-verification/{sku}")
async def check_supplier_verification_for_sku(
    sku: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Debug endpoint to check supplier verification status for a specific SKU.

    Returns detailed information about:
    - The local product
    - All matched supplier products
    - Verification status for each supplier
    - Why a supplier might not appear as verified
    """

    # Find the local product
    product_query = select(Product).where(Product.sku == sku)
    product_result = await db.execute(product_query)
    product = product_result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Product with SKU={sku} not found"
        )

    # Find all supplier products matched to this product
    sp_query = (
        select(SupplierProduct)
        .options(selectinload(SupplierProduct.supplier))
        .where(SupplierProduct.local_product_id == product.id)
        .where(SupplierProduct.is_active)
    )
    sp_result = await db.execute(sp_query)
    supplier_products = sp_result.scalars().all()

    # Format response
    suppliers_info = []
    for sp in supplier_products:
        supplier_info = {
            "supplier_product_id": sp.id,
            "supplier_id": sp.supplier_id,
            "supplier_name": sp.supplier.name if sp.supplier else "Unknown",
            "supplier_product_name": sp.supplier_product_name,
            "supplier_product_chinese_name": sp.supplier_product_chinese_name,
            "price": sp.supplier_price,
            "currency": sp.supplier_currency,
            "confidence_score": sp.confidence_score,
            "manual_confirmed": sp.manual_confirmed,
            "is_verified": sp.manual_confirmed,  # This is what appears in Low Stock API
            "is_preferred": sp.is_preferred,
            "is_active": sp.is_active,
            "confirmed_by": sp.confirmed_by,
            "confirmed_at": sp.confirmed_at.isoformat() if sp.confirmed_at else None,
            "last_price_update": sp.last_price_update.isoformat() if sp.last_price_update else None,
            "import_source": sp.import_source,
            "supplier_product_url": sp.supplier_product_url,
            "will_show_as_verified_in_low_stock": sp.manual_confirmed,
            "verification_issues": []
        }

        # Check for potential issues
        if not sp.manual_confirmed:
            supplier_info["verification_issues"].append(
                "manual_confirmed is False - supplier will NOT show as verified"
            )

        if not sp.is_active:
            supplier_info["verification_issues"].append(
                "is_active is False - supplier will NOT appear at all"
            )

        if sp.local_product_id != product.id:
            supplier_info["verification_issues"].append(
                f"Matched to different product ID: {sp.local_product_id}"
            )

        suppliers_info.append(supplier_info)

    return {
        "status": "success",
        "data": {
            "product": {
                "id": product.id,
                "sku": product.sku,
                "name": product.name,
                "chinese_name": product.chinese_name,
                "is_active": product.is_active,
            },
            "total_suppliers": len(suppliers_info),
            "verified_suppliers": sum(1 for s in suppliers_info if s["manual_confirmed"]),
            "suppliers": suppliers_info,
            "summary": {
                "has_verified_suppliers": any(s["manual_confirmed"] for s in suppliers_info),
                "all_suppliers_active": all(s["is_active"] for s in suppliers_info),
                "issues_found": any(s["verification_issues"] for s in suppliers_info),
            }
        }
    }
