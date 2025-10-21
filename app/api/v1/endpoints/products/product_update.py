"""
Product Update API Endpoints
Handles importing and updating products from Google Sheets
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_database_session
from app.models.user import User
from app.services.product.product_update_service import ProductUpdateService

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic schemas
class ImportPreviewRequest(BaseModel):
    """Request to preview import changes"""

    pass


class ProductChange(BaseModel):
    """Represents a change to a product field"""

    field: str
    old_value: str | None = None
    new_value: str | None = None


class PreviewProduct(BaseModel):
    """Product in preview"""

    sku: str
    name: str
    price: float | None = None
    changes: list[ProductChange] | None = None


class ImportPreviewResponse(BaseModel):
    """Response from import preview"""

    total_rows: int
    new_products: list[PreviewProduct]
    updated_products: list[PreviewProduct]
    unchanged_products: list[PreviewProduct]
    errors: list[dict]


class ImportUpdateRequest(BaseModel):
    """Request to import and update products"""

    update_existing: bool = Field(
        default=True, description="Update existing products with new data"
    )
    create_new: bool = Field(
        default=True, description="Create new products from Google Sheets"
    )


class ImportUpdateResponse(BaseModel):
    """Response from import and update operation"""

    import_id: int
    status: str
    total_rows: int
    successful_imports: int
    failed_imports: int
    skipped_rows: int
    products_created: int
    products_updated: int
    duration_seconds: float | None = None
    error_message: str | None = None


class ProductStatistics(BaseModel):
    """Statistics about products"""

    total_products: int
    active_products: int
    inactive_products: int
    priced_products: int
    unpriced_products: int


class ProductResponse(BaseModel):
    """Product information"""

    id: int
    sku: str
    name: str
    base_price: float
    currency: str
    is_active: bool
    display_order: int | None = None
    image_url: str | None = None
    brand: str | None = None
    ean: str | None = None
    weight_kg: float | None = None
    manufacturer: str | None = None

    class Config:
        from_attributes = True


class ImportLogResponse(BaseModel):
    """Import log information"""

    id: int
    import_type: str
    source_name: str
    total_rows: int
    successful_imports: int
    failed_imports: int
    skipped_rows: int
    status: str
    started_at: str
    completed_at: str | None
    duration_seconds: float | None
    initiated_by: str | None

    class Config:
        from_attributes = True


@router.get("/preview", response_model=ImportPreviewResponse)
async def preview_import(
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
):
    """
    Preview what changes would be made by importing from Google Sheets

    This endpoint:
    1. Reads products from Google Sheets
    2. Compares with existing products in database
    3. Returns a preview of new, updated, and unchanged products

    **Does not make any changes to the database**
    """
    try:
        service = ProductUpdateService(db)
        preview = await service.preview_import()

        return ImportPreviewResponse(
            total_rows=preview["total_rows"],
            new_products=[PreviewProduct(**p) for p in preview["new_products"]],
            updated_products=[PreviewProduct(**p) for p in preview["updated_products"]],
            unchanged_products=[
                PreviewProduct(**p) for p in preview["unchanged_products"]
            ],
            errors=preview["errors"],
        )
    except Exception as e:
        logger.error(f"Preview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/import", response_model=ImportUpdateResponse)
async def import_and_update_products(
    request: ImportUpdateRequest,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
):
    """
    Import products from Google Sheets and update local database

    This endpoint:
    1. Reads products from Google Sheets
    2. Creates new products (if create_new=true)
    3. Updates existing products (if update_existing=true)
    4. Returns import statistics

    **Required files:**
    - `service_account.json` in the project root

    **Google Sheets structure:**
    - Sheet name: "eMAG Stock"
    - Tab: "Products"
    - Required columns: SKU, Romanian_Name, Emag_FBE_RO_Price_RON
    """
    try:
        service = ProductUpdateService(db)
        import_log = await service.import_and_update_products(
            user_email=current_user.email,
            update_existing=request.update_existing,
            create_new=request.create_new,
        )

        return ImportUpdateResponse(
            import_id=import_log.id,
            status=import_log.status,
            total_rows=import_log.total_rows,
            successful_imports=import_log.successful_imports,
            failed_imports=import_log.failed_imports,
            skipped_rows=import_log.skipped_rows,
            products_created=import_log.auto_mapped_main,  # Repurposed field
            products_updated=import_log.auto_mapped_fbe,  # Repurposed field
            duration_seconds=import_log.duration_seconds,
            error_message=import_log.error_message,
        )
    except Exception as e:
        logger.error(f"Import failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/statistics", response_model=ProductStatistics)
async def get_product_statistics(
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get statistics about products in the database

    Returns counts of:
    - Total products
    - Active products
    - Inactive products
    - Products with prices
    - Products without prices
    """
    try:
        service = ProductUpdateService(db)
        stats = await service.get_product_statistics()
        return ProductStatistics(**stats)
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/products")
async def get_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: str | None = Query(None, description="Search by SKU, name, EAN, brand, or old SKU"),
    status_filter: str | None = Query(None, description="Filter by status: 'all', 'active', 'inactive', 'discontinued'"),
    active_only: bool = Query(False, description="[Deprecated] Only return active products - use status_filter instead"),
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get products with pagination and filtering

    **Query parameters:**
    - `skip`: Number of records to skip (pagination)
    - `limit`: Maximum number of records to return
    - `search`: Search term for SKU, product name, EAN, brand, or old SKUs
    - `status_filter`: Filter by status ('all', 'active', 'inactive', 'discontinued')
    - `active_only`: [Deprecated] Filter to only active products - use status_filter instead

    **Note:** Products are always sorted by display_order (ascending, NULL values last)

    **Returns:**
    ```json
    {
        "data": {
            "products": [...],
            "pagination": {
                "total": 123,
                "skip": 0,
                "limit": 20
            }
        }
    }
    ```
    """
    try:
        service = ProductUpdateService(db)
        products, total = await service.get_all_products(
            skip=skip, limit=limit, search=search, status_filter=status_filter, active_only=active_only
        )

        return {
            "data": {
                "products": [
                    {
                        "id": p.id,
                        "sku": p.sku,
                        "name": p.name,
                        "base_price": p.base_price,
                        "currency": p.currency,
                        "is_active": p.is_active,
                        "display_order": p.display_order,
                        "image_url": p.image_url,
                        "brand": p.brand,
                        "ean": p.ean,
                        "weight_kg": p.weight_kg,
                        "manufacturer": p.manufacturer,
                        "is_discontinued": p.is_discontinued,
                        "recommended_price": p.recommended_price,
                        "chinese_name": p.chinese_name,
                        "description": p.description,
                        "short_description": p.short_description,
                        "suppliers": [
                            {
                                "id": sp.supplier.id,
                                "name": sp.supplier.name,
                                "country": sp.supplier.country,
                                "is_active": sp.supplier.is_active,
                                "supplier_price": sp.supplier_price,
                                "supplier_currency": sp.supplier_currency,
                            }
                            for sp in p.supplier_mappings
                            if sp.supplier
                        ] if p.supplier_mappings else [],
                        "created_at": p.created_at.isoformat() if p.created_at else None,
                        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                    }
                    for p in products
                ],
                "pagination": {
                    "total": total,
                    "skip": skip,
                    "limit": limit,
                }
            }
        }
    except Exception as e:
        logger.error(f"Failed to get products: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/history", response_model=list[ImportLogResponse])
async def get_import_history(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get recent import history

    Returns the most recent product import operations with statistics
    """
    try:
        service = ProductUpdateService(db)
        logs = await service.get_import_history(limit=limit)

        return [
            ImportLogResponse(
                id=log.id,
                import_type=log.import_type,
                source_name=log.source_name,
                total_rows=log.total_rows,
                successful_imports=log.successful_imports,
                failed_imports=log.failed_imports,
                skipped_rows=log.skipped_rows,
                status=log.status,
                started_at=log.started_at.isoformat(),
                completed_at=log.completed_at.isoformat() if log.completed_at else None,
                duration_seconds=log.duration_seconds,
                initiated_by=log.initiated_by,
            )
            for log in logs
        ]
    except Exception as e:
        logger.error(f"Failed to get import history: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/test-connection")
async def test_google_sheets_connection(current_user: User = Depends(get_current_user)):
    """
    Test connection to Google Sheets

    Verifies:
    - Service account credentials are valid
    - Spreadsheet can be accessed
    - Required sheets exist
    """
    try:
        from app.services.google_sheets_service import GoogleSheetsService

        service = GoogleSheetsService()

        # Test authentication
        if not service.authenticate():
            raise HTTPException(
                status_code=500, detail="Failed to authenticate with Google Sheets API"
            )

        # Test opening spreadsheet
        if not service.open_spreadsheet():
            raise HTTPException(status_code=500, detail="Failed to open spreadsheet")

        # Get statistics
        stats = service.get_sheet_statistics()

        return {
            "status": "connected",
            "message": "Successfully connected to Google Sheets",
            "statistics": stats,
        }
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


class GoogleSheetsProductResponse(BaseModel):
    """Product from Google Sheets"""

    sku: str
    romanian_name: str
    emag_fbe_ro_price_ron: float | None = None
    row_number: int


@router.get("/google-sheets-products", response_model=list[GoogleSheetsProductResponse])
async def get_google_sheets_products(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of products to return"),
    current_user: User = Depends(get_current_user),
):
    """
    Get products directly from Google Sheets without importing

    This endpoint:
    1. Connects to Google Sheets
    2. Reads products from the "Products" tab
    3. Returns the raw data from Google Sheets

    **Does not access or modify the local database**

    Use this to preview what products are available in Google Sheets before importing.
    """
    try:
        from app.services.google_sheets_service import GoogleSheetsService

        service = GoogleSheetsService()

        # Authenticate and open spreadsheet
        if not service.authenticate():
            raise HTTPException(
                status_code=500, detail="Failed to authenticate with Google Sheets API"
            )

        if not service.open_spreadsheet():
            raise HTTPException(status_code=500, detail="Failed to open spreadsheet")

        # Get products from Google Sheets
        sheet_products = service.get_all_products()

        # Limit results
        limited_products = sheet_products[:limit]

        return [
            GoogleSheetsProductResponse(
                sku=p.sku,
                romanian_name=p.romanian_name,
                emag_fbe_ro_price_ron=p.emag_fbe_ro_price_ron,
                row_number=p.row_number,
            )
            for p in limited_products
        ]
    except Exception as e:
        logger.error(f"Failed to get Google Sheets products: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
