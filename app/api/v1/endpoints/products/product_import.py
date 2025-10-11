"""
Product Import API Endpoints
Handles importing products from Google Sheets and managing mappings
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_database_session
from app.models.user import User
from app.services.product.product_import_service import ProductImportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/import")


# Pydantic schemas
class ImportRequest(BaseModel):
    """Request to import products from Google Sheets"""

    auto_map: bool = Field(
        default=True, description="Automatically map products to eMAG accounts"
    )
    import_suppliers: bool = Field(
        default=True, description="Import supplier data from Product_Suppliers tab"
    )


class ImportResponse(BaseModel):
    """Response from import operation"""

    import_id: int
    status: str
    total_rows: int
    successful_imports: int
    failed_imports: int
    auto_mapped_main: int
    auto_mapped_fbe: int
    unmapped_products: int
    duration_seconds: float | None = None
    error_message: str | None = None


class MappingStatistics(BaseModel):
    """Statistics about product mappings"""

    total_products: int
    fully_mapped: int
    main_only: int
    fbe_only: int
    unmapped: int
    mapping_percentage: float


class ProductMappingResponse(BaseModel):
    """Product mapping information"""

    id: int
    local_sku: str
    local_product_name: str
    local_price: float | None
    emag_main_id: int | None
    emag_main_part_number: str | None
    emag_main_status: str | None
    emag_fbe_id: int | None
    emag_fbe_part_number: str | None
    emag_fbe_status: str | None
    mapping_status: str
    mapping_confidence: float | None
    mapping_method: str | None
    is_verified: bool
    has_conflicts: bool
    notes: str | None

    class Config:
        from_attributes = True


class ManualMappingRequest(BaseModel):
    """Request to manually map a product"""

    local_sku: str
    emag_main_id: int | None = None
    emag_fbe_id: int | None = None
    notes: str | None = None


class ImportLogResponse(BaseModel):
    """Import log information"""

    id: int
    import_type: str
    source_name: str
    total_rows: int
    successful_imports: int
    failed_imports: int
    status: str
    started_at: str
    completed_at: str | None
    duration_seconds: float | None
    initiated_by: str | None

    class Config:
        from_attributes = True


class ProductLookupMatch(BaseModel):
    """Match information for eMAG product lookup by SKU"""

    account_type: str
    emag_product_id: str
    part_number: str
    part_number_key: str | None = None
    name: str | None = None
    status: str | None = None


class ProductLookupResponse(BaseModel):
    """Response payload for SKU lookup"""

    sku: str
    matches: dict[str, ProductLookupMatch | None]


class RemapRequest(BaseModel):
    """Request payload for remapping unmapped products"""

    limit: int | None = Field(default=100, ge=1, le=1000)
    dry_run: bool = False


class RemapSummary(BaseModel):
    """Response summary for remapping operation"""

    processed: int
    updated: int
    mapped_main: int
    mapped_fbe: int
    still_unmapped: int


class ProductSupplierResponse(BaseModel):
    """Supplier information for a product"""

    id: int
    sku: str
    supplier_name: str
    price_cny: float
    calculated_price_ron: float | None
    exchange_rate_cny_ron: float | None
    supplier_contact: str | None
    supplier_url: str | None
    supplier_notes: str | None
    is_preferred: bool
    is_verified: bool
    last_imported_at: str | None

    class Config:
        from_attributes = True


class SupplierStatistics(BaseModel):
    """Statistics about imported suppliers"""

    total_supplier_entries: int
    unique_skus_with_suppliers: int
    unique_supplier_names: int
    avg_suppliers_per_sku: float


@router.post("/google-sheets", response_model=ImportResponse)
async def import_from_google_sheets(
    request: ImportRequest,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
):
    """
    Import products from Google Sheets

    This endpoint:
    1. Connects to Google Sheets using service account credentials
    2. Reads products from the configured sheet
    3. Creates/updates product mappings in the database
    4. Optionally auto-maps products to eMAG MAIN and FBE accounts by SKU

    **Required files:**
    - `service_account.json` in the project root

    **Google Sheets structure:**
    - Sheet name: "eMAG Stock"
    - Tab: "Products"
    - Required columns: SKU, Romanian_Name, Emag_FBE_RO_Price_RON
    """
    try:
        service = ProductImportService(db)
        import_log = await service.import_from_google_sheets(
            user_email=current_user.email,
            auto_map=request.auto_map,
            import_suppliers=request.import_suppliers,
        )

        return ImportResponse(
            import_id=import_log.id,
            status=import_log.status,
            total_rows=import_log.total_rows,
            successful_imports=import_log.successful_imports,
            failed_imports=import_log.failed_imports,
            auto_mapped_main=import_log.auto_mapped_main,
            auto_mapped_fbe=import_log.auto_mapped_fbe,
            unmapped_products=import_log.unmapped_products,
            duration_seconds=import_log.duration_seconds,
            error_message=import_log.error_message,
        )
    except Exception as e:
        logger.error(f"Import failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mappings/statistics", response_model=MappingStatistics)
async def get_mapping_statistics(
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get statistics about product mappings

    Returns counts of:
    - Total products
    - Fully mapped (both MAIN and FBE)
    - MAIN only
    - FBE only
    - Unmapped
    - Overall mapping percentage
    """
    try:
        service = ProductImportService(db)
        stats = await service.get_mapping_statistics()
        return MappingStatistics(**stats)
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mappings", response_model=list[ProductMappingResponse])
async def get_product_mappings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    filter_status: str | None = Query(
        None,
        description="Filter by status: fully_mapped, partially_mapped, unmapped, conflict",
    ),
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get product mappings with pagination and filtering

    **Filter options:**
    - `fully_mapped`: Products mapped to both MAIN and FBE
    - `partially_mapped`: Products mapped to only one account
    - `unmapped`: Products not mapped to any account
    - `conflict`: Products with mapping conflicts
    """
    try:
        service = ProductImportService(db)
        mappings, total = await service.get_all_mappings(
            skip=skip, limit=limit, filter_status=filter_status
        )

        return [
            ProductMappingResponse(
                id=m.id,
                local_sku=m.local_sku,
                local_product_name=m.local_product_name,
                local_price=m.local_price,
                emag_main_id=m.emag_main_id,
                emag_main_part_number=m.emag_main_part_number,
                emag_main_status=m.emag_main_status,
                emag_fbe_id=m.emag_fbe_id,
                emag_fbe_part_number=m.emag_fbe_part_number,
                emag_fbe_status=m.emag_fbe_status,
                mapping_status=m.get_mapping_status(),
                mapping_confidence=m.mapping_confidence,
                mapping_method=m.mapping_method,
                is_verified=m.is_verified,
                has_conflicts=m.has_conflicts,
                notes=m.notes,
            )
            for m in mappings
        ]
    except Exception as e:
        logger.error(f"Failed to get mappings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mappings/lookup", response_model=ProductLookupResponse)
async def lookup_emag_products_by_sku(
    sku: str = Query(
        ..., description="SKU / part number to match against eMAG products"
    ),
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
):
    """Lookup eMAG MAIN and FBE products by SKU (part_number)."""
    normalized_sku = sku.strip()
    if not normalized_sku:
        raise HTTPException(status_code=400, detail="SKU must be provided")

    service = ProductImportService(db)
    matches = await service.get_emag_matches_by_sku(normalized_sku)

    formatted_matches: dict[str, ProductLookupMatch | None] = {}
    for account, product in matches.items():
        if product is None:
            formatted_matches[account] = None
        else:
            formatted_matches[account] = ProductLookupMatch(
                account_type=account,
                emag_product_id=product["id"],
                part_number=product["part_number"],
                part_number_key=product.get("part_number_key"),
                name=product.get("name"),
                status=product.get("status"),
            )

    return ProductLookupResponse(sku=normalized_sku, matches=formatted_matches)


@router.post("/mappings/remap", response_model=RemapSummary)
async def remap_unmapped_products(
    request: RemapRequest,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
):
    """Batch remap unmapped products by re-running SKU lookups."""
    service = ProductImportService(db)
    summary = await service.remap_unmapped_products(
        limit=request.limit, dry_run=request.dry_run
    )
    return RemapSummary(**summary)


@router.post("/mappings/manual", response_model=ProductMappingResponse)
async def create_manual_mapping(
    request: ManualMappingRequest,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
):
    """
    Manually map a product to eMAG accounts

    Use this endpoint to:
    - Correct automatic mappings
    - Map products that couldn't be auto-mapped
    - Link products with different SKUs

    **Note:** At least one of `emag_main_id` or `emag_fbe_id` must be provided
    """
    if not request.emag_main_id and not request.emag_fbe_id:
        raise HTTPException(
            status_code=400,
            detail="At least one of emag_main_id or emag_fbe_id must be provided",
        )

    try:
        service = ProductImportService(db)
        mapping = await service.manual_map_product(
            local_sku=request.local_sku,
            emag_main_id=request.emag_main_id,
            emag_fbe_id=request.emag_fbe_id,
            notes=request.notes,
        )

        return ProductMappingResponse(
            id=mapping.id,
            local_sku=mapping.local_sku,
            local_product_name=mapping.local_product_name,
            local_price=mapping.local_price,
            emag_main_id=mapping.emag_main_id,
            emag_main_part_number=mapping.emag_main_part_number,
            emag_main_status=mapping.emag_main_status,
            emag_fbe_id=mapping.emag_fbe_id,
            emag_fbe_part_number=mapping.emag_fbe_part_number,
            emag_fbe_status=mapping.emag_fbe_status,
            mapping_status=mapping.get_mapping_status(),
            mapping_confidence=mapping.mapping_confidence,
            mapping_method=mapping.mapping_method,
            is_verified=mapping.is_verified,
            has_conflicts=mapping.has_conflicts,
            notes=mapping.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create manual mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=list[ImportLogResponse])
async def get_import_history(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get recent import history

    Returns the most recent import operations with statistics
    """
    try:
        service = ProductImportService(db)
        logs = await service.get_import_history(limit=limit)

        return [
            ImportLogResponse(
                id=log.id,
                import_type=log.import_type,
                source_name=log.source_name,
                total_rows=log.total_rows,
                successful_imports=log.successful_imports,
                failed_imports=log.failed_imports,
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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suppliers/{sku}", response_model=list[ProductSupplierResponse])
async def get_product_suppliers(
    sku: str,
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get all suppliers for a specific product SKU

    Returns list of suppliers with pricing information from Google Sheets
    """
    try:
        service = ProductImportService(db)
        suppliers = await service.get_suppliers_for_sku(sku)

        return [
            ProductSupplierResponse(
                id=s.id,
                sku=s.sku,
                supplier_name=s.supplier_name,
                price_cny=s.price_cny,
                calculated_price_ron=s.calculated_price_ron,
                exchange_rate_cny_ron=s.exchange_rate_cny_ron,
                supplier_contact=s.supplier_contact,
                supplier_url=s.supplier_url,
                supplier_notes=s.supplier_notes,
                is_preferred=s.is_preferred,
                is_verified=s.is_verified,
                last_imported_at=s.last_imported_at.isoformat()
                if s.last_imported_at
                else None,
            )
            for s in suppliers
        ]
    except Exception as e:
        logger.error(f"Failed to get suppliers for SKU {sku}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suppliers-statistics", response_model=SupplierStatistics)
async def get_supplier_statistics(
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get statistics about imported suppliers

    Returns:
    - Total supplier entries
    - Unique SKUs with suppliers
    - Unique supplier names
    - Average suppliers per SKU
    """
    try:
        service = ProductImportService(db)
        stats = await service.get_supplier_statistics()
        return SupplierStatistics(**stats)
    except Exception as e:
        logger.error(f"Failed to get supplier statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/supplier-products")
async def get_all_supplier_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    sku: str | None = Query(None, description="Filter by SKU"),
    supplier_name: str | None = Query(None, description="Filter by supplier name"),
    db: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get all supplier products from Google Sheets import

    Returns paginated list of supplier products with filters
    """
    try:
        service = ProductImportService(db)
        products = await service.get_all_supplier_products(
            skip=skip, limit=limit, sku=sku, supplier_name=supplier_name
        )

        total = await service.count_supplier_products(
            sku=sku, supplier_name=supplier_name
        )

        return {"data": products, "total": total, "skip": skip, "limit": limit}
    except Exception as e:
        logger.error(f"Failed to get supplier products: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sheets/test-connection")
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
        raise HTTPException(status_code=500, detail=str(e))
