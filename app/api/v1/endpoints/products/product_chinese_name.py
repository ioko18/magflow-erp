"""
Product Chinese Name Update Endpoint
Allows updating local product chinese name from supplier data
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_async_db
from app.models.product import Product
from app.models.supplier import SupplierProduct
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


class UpdateChineseNameRequest(BaseModel):
    supplier_product_id: int


class UpdateChineseNameResponse(BaseModel):
    status: str
    message: str
    data: dict | None = None


@router.post("/update-from-supplier", response_model=UpdateChineseNameResponse)
async def update_chinese_name_from_supplier(
    request: UpdateChineseNameRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update local product chinese name from supplier product data

    This endpoint copies the chinese name from supplier_product to the local product.
    Useful when supplier has chinese name but local product doesn't.

    Args:
        supplier_product_id: ID of the supplier product

    Returns:
        Success message with updated product info
    """
    try:
        # Get supplier product
        sp_query = select(SupplierProduct).where(
            SupplierProduct.id == request.supplier_product_id
        )
        sp_result = await db.execute(sp_query)
        supplier_product = sp_result.scalar_one_or_none()

        if not supplier_product:
            raise HTTPException(
                status_code=404,
                detail=f"Supplier product {request.supplier_product_id} not found",
            )

        # Check if supplier product has chinese name
        if not supplier_product.supplier_product_chinese_name:
            raise HTTPException(
                status_code=400, detail="Supplier product does not have a chinese name"
            )

        # Check if supplier product has local product
        if not supplier_product.local_product_id:
            raise HTTPException(
                status_code=400,
                detail="Supplier product is not linked to a local product",
            )

        # Get local product
        product_query = select(Product).where(
            Product.id == supplier_product.local_product_id
        )
        product_result = await db.execute(product_query)
        local_product = product_result.scalar_one_or_none()

        if not local_product:
            raise HTTPException(
                status_code=404,
                detail=f"Local product {supplier_product.local_product_id} not found",
            )

        # Store old value for logging
        old_chinese_name = local_product.chinese_name

        # Update chinese name
        local_product.chinese_name = supplier_product.supplier_product_chinese_name

        await db.commit()
        await db.refresh(local_product)

        logger.info(
            f"Updated chinese name for product {local_product.sku}: "
            f"'{old_chinese_name}' -> '{local_product.chinese_name}'"
        )

        return UpdateChineseNameResponse(
            status="success",
            message=f"Chinese name updated successfully for SKU {local_product.sku}",
            data={
                "product_id": local_product.id,
                "sku": local_product.sku,
                "old_chinese_name": old_chinese_name,
                "new_chinese_name": local_product.chinese_name,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update chinese name: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update chinese name: {str(e)}"
        )
