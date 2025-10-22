"""
Product Chinese Name Update Endpoint
Allows updating local product chinese name from supplier data
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_async_db
from app.models.product import Product
from app.models.supplier import SupplierProduct
from app.models.user import User
from app.services.jieba_matching_service import JiebaMatchingService

router = APIRouter()
logger = logging.getLogger(__name__)


class SupplierMatch(BaseModel):
    supplier_product_id: int
    supplier_id: int
    supplier_name: str | None = None
    supplier_product_name: str | None = None
    supplier_product_chinese_name: str | None = None
    supplier_product_specification: str | None = None
    supplier_product_url: str | None = None
    supplier_image_url: str | None = None
    supplier_price: float | None = None
    supplier_currency: str | None = None
    similarity_score: float
    similarity_percent: float | None = None
    local_product_id: int | None = None
    local_product: dict[str, Any] | None = None
    manual_confirmed: bool | None = None
    confidence_score: float | None = None


class LocalProductMatch(BaseModel):
    id: int
    name: str
    chinese_name: str | None = None
    sku: str
    brand: str | None = None
    image_url: str | None = None
    similarity_score: float
    similarity_percent: float | None = None
    supplier_match_count: int = Field(default=0, description="Number of supplier products linked to this product")


class ChineseNameSearchData(BaseModel):
    supplier_matches: list[SupplierMatch]
    local_matches: list[LocalProductMatch]
    search_term: str
    min_similarity: float


class ChineseNameSearchResponse(BaseModel):
    status: str
    data: ChineseNameSearchData


class UpdateChineseNameRequest(BaseModel):
    supplier_product_id: int


class UpdateChineseNameResponse(BaseModel):
    status: str
    message: str
    data: dict | None = None


class UpdateLocalChineseNameRequest(BaseModel):
    chinese_name: str | None = Field(default=None, max_length=500)


class UpdateLocalChineseNameResponse(BaseModel):
    status: str
    message: str
    data: dict[str, Any]


class LinkSupplierProductRequest(BaseModel):
    supplier_product_id: int
    local_product_id: int
    confirm: bool = True


class LinkSupplierProductResponse(BaseModel):
    status: str
    message: str
    data: dict[str, Any]


@router.get("/search-by-chinese-name", response_model=ChineseNameSearchResponse)
async def search_products_by_chinese_name(
    chinese_name: str = Query(..., min_length=1, description="Chinese name or keywords to search"),
    min_similarity: float = Query(0.85, ge=0.0, le=1.0, description="Minimum similarity threshold"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results to return"),
    supplier_id: int | None = Query(None, description="Optional supplier filter"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    try:
        jieba_service = JiebaMatchingService(db)

        matches = await jieba_service.search_supplier_products(
            search_term=chinese_name,
            threshold=min_similarity,
            limit=limit,
            supplier_id=supplier_id,
        )

        local_matches = await jieba_service.search_local_products(
            search_term=chinese_name,
            threshold=min_similarity,
            limit=limit,
        )

        return {
            "status": "success",
            "data": {
                "supplier_matches": matches,
                "local_matches": local_matches,
                "search_term": chinese_name,
                "min_similarity": min_similarity,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to search products by Chinese name: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to search products by Chinese name") from exc


@router.post("/link", response_model=LinkSupplierProductResponse)
async def link_supplier_product_to_local(
    request: LinkSupplierProductRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    sp_query = select(SupplierProduct).where(
        SupplierProduct.id == request.supplier_product_id
    )
    sp_result = await db.execute(sp_query)
    supplier_product = sp_result.scalar_one_or_none()

    if not supplier_product:
        raise HTTPException(status_code=404, detail="Supplier product not found")

    product_query = select(Product).where(Product.id == request.local_product_id)
    product_result = await db.execute(product_query)
    local_product = product_result.scalar_one_or_none()

    if not local_product:
        raise HTTPException(status_code=404, detail="Local product not found")

    supplier_name = supplier_product.supplier_product_chinese_name or supplier_product.supplier_product_name
    local_name = local_product.chinese_name or local_product.name

    supplier_tokens = set(JiebaMatchingService.tokenize_clean(supplier_name)) if supplier_name else set()
    local_tokens = set(JiebaMatchingService.tokenize_clean(local_name)) if local_name else set()

    similarity, common_tokens = JiebaMatchingService.calculate_similarity(
        supplier_tokens, local_tokens
    )

    supplier_product.local_product_id = local_product.id
    supplier_product.confidence_score = similarity
    supplier_product.manual_confirmed = request.confirm
    supplier_product.confirmed_by = current_user.id
    supplier_product.confirmed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(supplier_product)

    return {
        "status": "success",
        "message": "Supplier product linked successfully",
        "data": {
            "supplier_product_id": supplier_product.id,
            "local_product_id": local_product.id,
            "similarity_score": similarity,
            "similarity_percent": round(similarity * 100, 2) if similarity else 0.0,
            "common_tokens": list(common_tokens),
        },
    }


@router.patch("/local/{product_id}", response_model=UpdateLocalChineseNameResponse)
async def update_local_product_chinese_name(
    product_id: int,
    request: UpdateLocalChineseNameRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    product_query = select(Product).where(Product.id == product_id)
    product_result = await db.execute(product_query)
    product = product_result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Local product not found")

    new_chinese_name = request.chinese_name.strip() if request.chinese_name else None

    product.chinese_name = new_chinese_name
    product.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(product)

    logger.info(
        "User %s updated chinese name for product %s to '%s'",
        current_user.id,
        product.sku,
        new_chinese_name,
    )

    return {
        "status": "success",
        "message": "Chinese name updated successfully",
        "data": {
            "product_id": product.id,
            "sku": product.sku,
            "chinese_name": product.chinese_name,
        },
    }


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
        ) from e
