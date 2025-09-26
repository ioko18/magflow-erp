"""Catalog API routes.

Provides product, brand, and characteristic endpoints used by integration tests.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.catalog import (
    Brand,
    BrandListResponse,
    CharacteristicListResponse,
    Product,
    ProductCreate,
    ProductListResponse,
    ProductUpdate,
)
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/catalog", tags=["catalog"])


def get_service() -> CatalogService:
    # The tests override this dependency with a mock
    return CatalogService()


@router.get("/products", response_model=ProductListResponse)
async def list_products(
    q: Optional[str] = None,
    category_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    status: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock: Optional[bool] = None,
    limit: int = 20,
    sort_by: Optional[str] = None,
    sort_direction: Optional[str] = None,
    service: CatalogService = Depends(get_service),
) -> ProductListResponse:
    # Forward parameters via schema the service expects
    from app.schemas.catalog import ProductFilter, SortDirection, SortField

    sort_field = SortField.CREATED_AT
    if sort_by == "name":
        sort_field = SortField.NAME
    elif sort_by == "price":
        sort_field = SortField.PRICE
    elif sort_by == "updated_at":
        sort_field = SortField.UPDATED_AT

    sort_dir = SortDirection.DESC
    if sort_direction == "asc":
        sort_dir = SortDirection.ASC
    elif sort_direction == "desc":
        sort_dir = SortDirection.DESC

    filt = ProductFilter(
        q=q,
        category_id=category_id,
        brand_id=brand_id,
        status=status,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
        limit=limit,
        sort_by=sort_field,
        sort_direction=sort_dir,
    )
    return await service.list_products(filt)


@router.get("/products/{product_id}", response_model=Product)
async def get_product(
    product_id: UUID,
    service: CatalogService = Depends(get_service),
) -> Product:
    try:
        return await service.get_product_by_id(product_id)
    except HTTPException:
        # Let HTTPException bubble with its status and detail
        raise


@router.post("/products", response_model=Product, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    service: CatalogService = Depends(get_service),
) -> Product:
    return await service.create_product(payload)


@router.put("/products/{product_id}", response_model=Product)
async def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    service: CatalogService = Depends(get_service),
) -> Product:
    return await service.update_product(product_id, payload)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    service: CatalogService = Depends(get_service),
):
    await service.delete_product(product_id)
    # No return statement for 204 status code


@router.get("/brands", response_model=BrandListResponse)
async def list_brands(
    q: Optional[str] = None,
    limit: int = 20,
    cursor: Optional[str] = None,
    service: CatalogService = Depends(get_service),
) -> BrandListResponse:
    return await service.list_brands(q=q, limit=limit, cursor=cursor)


@router.get("/brands/{brand_id}", response_model=Brand)
async def get_brand(
    brand_id: int,
    service: CatalogService = Depends(get_service),
) -> Brand:
    return await service.get_brand_by_id(brand_id)


@router.get("/characteristics", response_model=CharacteristicListResponse)
async def list_characteristics(
    category_id: int,
    limit: int = 20,
    cursor: Optional[str] = None,
    service: CatalogService = Depends(get_service),
) -> CharacteristicListResponse:
    return await service.list_characteristics(
        category_id=category_id,
        limit=limit,
        cursor=cursor,
    )


@router.get("/characteristics/{characteristic_id}/values")
async def get_characteristic_values(
    category_id: int,
    characteristic_id: int,
    service: CatalogService = Depends(get_service),
):
    return await service.get_characteristic_values(
        category_id=category_id,
        characteristic_id=characteristic_id,
    )
