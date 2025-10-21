"""
Endpoint for promoting Google Sheets products to internal supplier products.

This allows converting ProductSupplierSheet entries (from Google Sheets imports)
into SupplierProduct entries (internal 1688-style products) for better management.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.product import Product
from app.models.product_supplier_sheet import ProductSupplierSheet
from app.models.supplier import Supplier, SupplierProduct

router = APIRouter()


@router.post("/sheets/{sheet_id}/promote")
async def promote_sheet_to_supplier_product(
    sheet_id: int,
    delete_sheet: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Promote a Google Sheets product to an internal supplier product.

    This endpoint:
    1. Clones the ProductSupplierSheet entry into a new SupplierProduct
    2. Copies all relevant fields (Chinese name, specs, price, URL)
    3. Links it to the correct supplier and local product
    4. Optionally deletes the sheet entry completely (recommended for clean migration)

    Args:
        sheet_id: ID of the ProductSupplierSheet to promote
        delete_sheet: Whether to delete the sheet entry after promotion (default: True)

    Returns:
        Success message with the new SupplierProduct ID
    """
    try:
        # Get the Google Sheets product
        sheet_query = select(ProductSupplierSheet).where(
            ProductSupplierSheet.id == sheet_id
        )
        sheet_result = await db.execute(sheet_query)
        sheet = sheet_result.scalar_one_or_none()

        if not sheet:
            raise HTTPException(status_code=404, detail="Google Sheets product not found")

        # Verify supplier exists
        if not sheet.supplier_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot promote: product has no supplier_id. Please set supplier_id first.",
            )

        supplier_query = select(Supplier).where(Supplier.id == sheet.supplier_id)
        supplier_result = await db.execute(supplier_query)
        supplier = supplier_result.scalar_one_or_none()

        if not supplier:
            raise HTTPException(
                status_code=404,
                detail=f"Supplier with ID {sheet.supplier_id} not found",
            )

        # Find local product by SKU
        product_query = select(Product).where(Product.sku == sheet.sku)
        product_result = await db.execute(product_query)
        local_product = product_result.scalar_one_or_none()

        if not local_product:
            raise HTTPException(
                status_code=404,
                detail=f"Local product with SKU {sheet.sku} not found. Please create it first.",
            )

        # Check if SupplierProduct already exists
        existing_query = select(SupplierProduct).where(
            SupplierProduct.supplier_id == sheet.supplier_id,
            SupplierProduct.local_product_id == local_product.id,
        )
        existing_result = await db.execute(existing_query)
        existing = existing_result.scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Supplier product already exists (ID: {existing.id}). Cannot promote duplicate.",
            )

        # Create new SupplierProduct from sheet data
        new_supplier_product = SupplierProduct(
            supplier_id=sheet.supplier_id,
            local_product_id=local_product.id,
            supplier_product_name=sheet.supplier_product_chinese_name or sheet.sku,
            supplier_product_chinese_name=sheet.supplier_product_chinese_name,
            supplier_product_specification=sheet.supplier_product_specification,
            supplier_product_url=sheet.supplier_url,
            supplier_price=sheet.price_cny,
            supplier_currency="CNY",
            exchange_rate=sheet.exchange_rate_cny_ron or 0.65,
            calculated_price_ron=sheet.calculated_price_ron,
            last_price_update=sheet.price_updated_at or datetime.now(UTC).replace(tzinfo=None),
            is_active=True,
            manual_confirmed=True,  # Mark as confirmed since it was manually promoted
            confidence_score=1.0,  # High confidence for manual promotion
            created_at=datetime.now(UTC).replace(tzinfo=None),
            updated_at=datetime.now(UTC).replace(tzinfo=None),
        )

        db.add(new_supplier_product)

        # Optionally delete sheet completely (recommended for clean migration)
        if delete_sheet:
            await db.delete(sheet)

        await db.commit()
        await db.refresh(new_supplier_product)

        return {
            "status": "success",
            "data": {
                "message": "Google Sheets product promoted and deleted successfully" if delete_sheet else "Google Sheets product promoted successfully",
                "sheet_id": sheet_id,
                "new_supplier_product_id": new_supplier_product.id,
                "sheet_deleted": delete_sheet,
                "supplier_name": supplier.name,
                "product_sku": local_product.sku,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error promoting product: {str(e)}"
        ) from e
