"""
Endpoint for setting supplier_id on Google Sheets products.

This allows associating a ProductSupplierSheet entry with a specific Supplier
before promoting it to an internal SupplierProduct.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.product_supplier_sheet import ProductSupplierSheet
from app.models.supplier import Supplier

router = APIRouter()


class SetSupplierRequest(BaseModel):
    """Request body for setting supplier"""

    supplier_id: int


@router.post("/sheets/{sheet_id}/set-supplier")
async def set_sheet_supplier(
    sheet_id: int,
    request: SetSupplierRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Set supplier_id for a Google Sheets product.

    This endpoint allows associating a ProductSupplierSheet entry with a specific
    Supplier by setting the supplier_id foreign key. This is required before
    promoting the sheet product to an internal SupplierProduct.

    Args:
        sheet_id: ID of the ProductSupplierSheet to update
        request: Request body containing supplier_id

    Returns:
        Success message with updated sheet product info
    """
    try:
        # Get the Google Sheets product
        sheet_query = select(ProductSupplierSheet).where(
            ProductSupplierSheet.id == sheet_id
        )
        sheet_result = await db.execute(sheet_query)
        sheet = sheet_result.scalar_one_or_none()

        if not sheet:
            raise HTTPException(
                status_code=404, detail="Google Sheets product not found"
            )

        # Verify supplier exists
        supplier_query = select(Supplier).where(Supplier.id == request.supplier_id)
        supplier_result = await db.execute(supplier_query)
        supplier = supplier_result.scalar_one_or_none()

        if not supplier:
            raise HTTPException(
                status_code=404,
                detail=f"Supplier with ID {request.supplier_id} not found",
            )

        # Check if supplier is active
        if not supplier.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"Supplier '{supplier.name}' is not active. Please activate it first.",
            )

        # Set supplier_id
        old_supplier_id = sheet.supplier_id
        sheet.supplier_id = request.supplier_id
        sheet.updated_at = datetime.now(UTC).replace(tzinfo=None)

        await db.commit()
        await db.refresh(sheet)

        return {
            "status": "success",
            "data": {
                "message": "Supplier set successfully",
                "sheet_id": sheet_id,
                "sku": sheet.sku,
                "old_supplier_id": old_supplier_id,
                "new_supplier_id": request.supplier_id,
                "supplier_name": supplier.name,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error setting supplier: {str(e)}"
        ) from e


@router.delete("/sheets/{sheet_id}/remove-supplier")
async def remove_sheet_supplier(
    sheet_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Remove supplier_id from a Google Sheets product.

    This endpoint removes the supplier association from a ProductSupplierSheet entry
    by setting supplier_id to NULL.

    Args:
        sheet_id: ID of the ProductSupplierSheet to update

    Returns:
        Success message
    """
    try:
        # Get the Google Sheets product
        sheet_query = select(ProductSupplierSheet).where(
            ProductSupplierSheet.id == sheet_id
        )
        sheet_result = await db.execute(sheet_query)
        sheet = sheet_result.scalar_one_or_none()

        if not sheet:
            raise HTTPException(
                status_code=404, detail="Google Sheets product not found"
            )

        # Remove supplier_id
        old_supplier_id = sheet.supplier_id
        sheet.supplier_id = None
        sheet.updated_at = datetime.now(UTC).replace(tzinfo=None)

        await db.commit()

        return {
            "status": "success",
            "data": {
                "message": "Supplier removed successfully",
                "sheet_id": sheet_id,
                "sku": sheet.sku,
                "old_supplier_id": old_supplier_id,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error removing supplier: {str(e)}"
        ) from e
