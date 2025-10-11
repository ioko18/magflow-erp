"""API endpoints for eMAG product mappings."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.models import User
from app.integrations.emag.schemas.mapping import (
    BulkMappingResult,
    ProductMappingCreate,
    ProductMappingResponse,
    ProductMappingUpdate,
    SyncHistoryResponse,
)
from app.integrations.emag.services.product_mapping_service import ProductMappingService
from app.models.mapping import MappingStatus

router = APIRouter()


@router.get("/mappings", response_model=list[ProductMappingResponse])
async def list_product_mappings(
    skip: int = 0,
    limit: int = 100,
    status: MappingStatus | None = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """List all product mappings with optional filtering."""
    service = ProductMappingService(db)
    return await service.list_mappings(skip=skip, limit=limit, status=status)


@router.post(
    "/mappings",
    response_model=ProductMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product_mapping(
    mapping_in: ProductMappingCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Create a new product mapping."""
    service = ProductMappingService(db)

    # Check if mapping already exists
    existing = await service.get_product_mapping(
        internal_id=mapping_in.internal_id,
        emag_id=mapping_in.emag_id,
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A mapping with these IDs already exists",
        )

    return await service.create_mapping(mapping_in.dict())


@router.get("/mappings/{mapping_id}", response_model=ProductMappingResponse)
async def get_product_mapping(
    mapping_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Get a product mapping by ID."""
    service = ProductMappingService(db)
    mapping = await service.get_mapping(mapping_id)
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found",
        )
    return mapping


@router.put("/mappings/{mapping_id}", response_model=ProductMappingResponse)
async def update_product_mapping(
    mapping_id: int,
    mapping_in: ProductMappingUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Update a product mapping."""
    service = ProductMappingService(db)

    # Check if mapping exists
    mapping = await service.get_mapping(mapping_id)
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found",
        )

    return await service.update_mapping(mapping_id, mapping_in.dict(exclude_unset=True))


@router.delete("/mappings/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_mapping(
    mapping_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Response:
    """Delete a product mapping and return a 204 No Content response."""
    service = ProductMappingService(db)

    # Check if mapping exists
    mapping = await service.get_mapping(mapping_id)
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found",
        )

    await service.delete_mapping(mapping_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/mappings/sync", response_model=BulkMappingResult)
async def sync_products(
    product_ids: list[str],
    force: bool = False,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Synchronize products to eMAG."""
    service = ProductMappingService(db)

    # TODO: Fetch actual product data from the database
    # For now, just create a list of product data with the provided IDs
    products_data = [{"id": pid} for pid in product_ids]

    return await service.bulk_sync_products(products_data)


@router.get("/mappings/{mapping_id}/history", response_model=list[SyncHistoryResponse])
async def get_mapping_sync_history(
    mapping_id: int,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Get sync history for a product mapping."""
    service = ProductMappingService(db)

    # Check if mapping exists
    mapping = await service.get_mapping(mapping_id)
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found",
        )

    return await service.get_sync_history(mapping_id, skip=skip, limit=limit)
