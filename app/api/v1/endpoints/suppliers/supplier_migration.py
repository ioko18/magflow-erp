"""
Supplier Migration API Endpoints
Handles migration from product_supplier_sheets to supplier_products
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_async_db
from app.models.user import User
from app.services.suppliers.supplier_migration_service import SupplierMigrationService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/migrate")
async def migrate_all_suppliers(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    Migrate all products from product_supplier_sheets to supplier_products

    This endpoint will:
    1. Find all products in product_supplier_sheets
    2. Match them with products and suppliers tables
    3. Insert into supplier_products (avoiding duplicates)
    """
    try:
        service = SupplierMigrationService(db)
        stats = await service.migrate_all()
        await db.commit()

        return {"status": "success", "data": stats}
    except Exception as e:
        await db.rollback()
        logger.error(f"Migration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/migrate/{supplier_name}")
async def migrate_supplier(
    supplier_name: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    Migrate products for a specific supplier

    Args:
        supplier_name: Name of the supplier to migrate
    """
    try:
        service = SupplierMigrationService(db)
        stats = await service.migrate_by_supplier(supplier_name)
        await db.commit()

        return {"status": "success", "supplier": supplier_name, "data": stats}
    except Exception as e:
        await db.rollback()
        logger.error(f"Migration failed for {supplier_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/unmigrated")
async def get_unmigrated_products(
    supplier_name: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get products that haven't been migrated yet

    Args:
        supplier_name: Optional supplier name filter
        limit: Maximum number of results (default: 100)
    """
    try:
        service = SupplierMigrationService(db)
        products = await service.get_unmigrated_products(supplier_name, limit)

        return {
            "status": "success",
            "data": {"products": products, "count": len(products)},
        }
    except Exception as e:
        logger.error(f"Failed to get unmigrated products: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/validate")
async def validate_migration_readiness(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """
    Validate if data is ready for migration

    Returns validation results including:
    - Products without SKU match
    - Products without supplier match
    - Overall readiness status
    """
    try:
        service = SupplierMigrationService(db)
        validation = await service.validate_migration_readiness()

        return {"status": "success", "data": validation}
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
