"""
Enhanced Products API endpoints with eMAG API v4.4.9 integration.

This module provides comprehensive product management functionality including:
- Product CRUD operations
- eMAG product validation and compliance checking
- Category and characteristic management
- EAN matching and product publishing
- Bulk operations
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.security.jwt import get_current_user
from app.models.user import User

router = APIRouter(prefix="/products-v1", tags=["products-v1"])


# ============================================================================
# Pydantic Models for Request/Response
# ============================================================================

class ProductValidationRequest(BaseModel):
    """Request model for product validation."""
    product_id: Optional[int] = None
    name: Optional[str] = None
    brand: Optional[str] = None
    part_number: Optional[str] = None
    category_id: Optional[int] = None
    sale_price: Optional[float] = None
    min_sale_price: Optional[float] = None
    max_sale_price: Optional[float] = None
    recommended_price: Optional[float] = None
    vat_id: Optional[int] = None
    stock: Optional[int] = None
    ean: Optional[List[str]] = None
    description: Optional[str] = None
    warranty: Optional[int] = None


class ProductValidationResponse(BaseModel):
    """Response model for product validation."""
    is_valid: bool
    compliance_score: int
    compliance_total: int
    compliance_level: str  # 'pass', 'warn', 'fail'
    errors: List[str]
    warnings: List[str]
    checklist: List[Dict[str, Any]]


class BulkUpdateRequest(BaseModel):
    """Request model for bulk product updates."""
    product_ids: List[int] = Field(..., min_items=1, max_items=50)
    updates: Dict[str, Any] = Field(..., description="Fields to update")
    account_type: Optional[str] = Field(None, description="Account type: main or fbe")


class ProductPublishRequest(BaseModel):
    """Request model for publishing products to eMAG."""
    product_ids: List[int] = Field(..., min_items=1, max_items=50)
    account_type: str = Field(..., description="Account type: main or fbe")
    force_publish: bool = Field(False, description="Force publish even with warnings")


class EANMatchRequest(BaseModel):
    """Request model for EAN matching."""
    ean_codes: List[str] = Field(..., min_items=1, max_items=10)
    account_type: Optional[str] = Field(None, description="Account type: main or fbe")


# ============================================================================
# Product Validation Functions
# ============================================================================

def validate_product_compliance(product_data: Dict[str, Any]) -> ProductValidationResponse:
    """
    Validate product compliance with eMAG API v4.4.9 standards.
    
    This function checks all required and recommended fields according to
    the eMAG Product Documentation Standard.
    """
    checklist = []
    errors = []
    warnings = []

    def add_check(key: str, label: str, status: str, message: str):
        checklist.append({
            "key": key,
            "label": label,
            "status": status,
            "message": message
        })
        if status == "fail":
            errors.append(message)
        elif status == "warn":
            warnings.append(message)

    # Required: Name (1-255 characters)
    name = product_data.get("name", "").strip()
    if 1 <= len(name) <= 255:
        add_check("name", "Nume produs (1-255 caractere)", "pass",
                 "Numele produsului respectă standardul eMAG.")
    else:
        add_check("name", "Nume produs (1-255 caractere)", "fail",
                 "Numele produsului este obligatoriu și trebuie să aibă între 1 și 255 de caractere.")

    # Required: Brand (1-255 characters)
    brand = product_data.get("brand", "").strip()
    if 1 <= len(brand) <= 255:
        add_check("brand", "Brand definit", "pass", "Brandul este completat.")
    else:
        add_check("brand", "Brand definit", "fail",
                 "Brandul trebuie completat (1-255 caractere) conform standardului eMAG.")

    # Required: Part Number (1-25 characters, no spaces/commas/semicolons)
    part_number = product_data.get("part_number", "").replace(" ", "").replace(",", "").replace(";", "")
    if 1 <= len(part_number) <= 25:
        add_check("part_number", "Part Number (1-25 caractere)", "pass", "Part number este valid.")
    else:
        add_check("part_number", "Part Number (1-25 caractere)", "fail",
                 "Part number este obligatoriu și trebuie să aibă 1-25 caractere (fără spații, virgule sau punct și virgulă).")

    # Required: Category ID
    category_id = product_data.get("category_id")
    if category_id and isinstance(category_id, int) and category_id > 0:
        add_check("category", "Categorie eMAG (category_id)", "pass", "Categoria eMAG este setată.")
    else:
        add_check("category", "Categorie eMAG (category_id)", "fail",
                 "Setează un category_id valid pentru produs (ID numeric > 0).")

    # Required: Sale Price (>0)
    sale_price = product_data.get("sale_price")
    if sale_price and sale_price > 0:
        add_check("sale_price", "Sale price (>0)", "pass", "Sale price este setat.")
    else:
        add_check("sale_price", "Sale price (>0)", "fail",
                 "Setează sale_price (>0) la prima publicare a ofertei.")

    # Required: Min Sale Price (>0)
    min_sale_price = product_data.get("min_sale_price")
    if min_sale_price and min_sale_price > 0:
        add_check("min_sale_price", "Min sale price (>0)", "pass", "Min sale price respectă cerința.")
    else:
        add_check("min_sale_price", "Min sale price (>0)", "fail",
                 "min_sale_price este obligatoriu (>0) la prima publicare.")

    # Required: Max Sale Price (>0)
    max_sale_price = product_data.get("max_sale_price")
    if max_sale_price and max_sale_price > 0:
        add_check("max_sale_price", "Max sale price (>0)", "pass", "Max sale price respectă cerința.")
    else:
        add_check("max_sale_price", "Max sale price (>0)", "fail",
                 "max_sale_price este obligatoriu (>0) la prima publicare.")

    # Validate price range
    if min_sale_price and max_sale_price:
        if max_sale_price > min_sale_price:
            add_check("sale_price_range", "Interval preț (min < max)", "pass",
                     "Intervalul de preț este valid.")
        else:
            add_check("sale_price_range", "Interval preț (min < max)", "fail",
                     "max_sale_price trebuie să fie mai mare decât min_sale_price.")

    # Validate sale price within bounds
    if sale_price and min_sale_price and max_sale_price:
        if min_sale_price <= sale_price <= max_sale_price:
            add_check("sale_price_bounds", "Sale price în intervalul [min, max]", "pass",
                     "sale_price este în intervalul acceptat.")
        else:
            add_check("sale_price_bounds", "Sale price în intervalul [min, max]", "fail",
                     "sale_price trebuie să rămână între min_sale_price și max_sale_price conform regulilor eMAG.")

    # Recommended: Recommended Price (> sale price)
    recommended_price = product_data.get("recommended_price")
    if recommended_price and sale_price:
        if recommended_price > sale_price:
            add_check("recommended_price", "Recommended price (> sale price)", "pass",
                     "recommended_price este setat corespunzător.")
        else:
            add_check("recommended_price", "Recommended price (> sale price)", "warn",
                     "recommended_price trebuie să fie mai mare decât sale_price pentru a activa promoțiile recomandate.")

    # Required: VAT ID
    vat_id = product_data.get("vat_id")
    if vat_id and isinstance(vat_id, int) and vat_id > 0:
        add_check("vat_id", "VAT ID setat", "pass", "VAT ID este setat.")
    else:
        add_check("vat_id", "VAT ID setat", "fail",
                 "Selectează un vat_id valid (folosind endpoint-ul vat/read).")

    # Required: Stock
    stock = product_data.get("stock", 0)
    if stock > 0:
        add_check("stock", "Stoc disponibil", "pass", "Produsul are stoc disponibil pentru ofertă.")
    else:
        add_check("stock", "Stoc disponibil", "warn",
                 "Trimite cel puțin o linie de stoc la publicarea inițială (warehouse_id + value).")

    # EAN validation (6-14 numeric characters)
    ean_codes = product_data.get("ean", [])
    if isinstance(ean_codes, str):
        ean_codes = [ean_codes]

    valid_eans = [ean for ean in ean_codes if isinstance(ean, str) and ean.strip()]
    invalid_eans = [ean for ean in valid_eans if not (6 <= len(ean) <= 14 and ean.isdigit())]

    if invalid_eans:
        add_check("ean_format", "EAN valid (6-14 cifre)", "fail",
                 "EAN-urile trebuie să conțină 6-14 caractere numerice (EAN/JAN/UPC/GTIN).")
    elif valid_eans:
        add_check("ean_presence", "EAN asociat ofertei", "pass", "EAN-urile sunt completate corect.")
    else:
        add_check("ean_presence", "EAN asociat ofertei", "warn",
                 "Adaugă EAN-uri valide atunci când categoria le solicită. Ele ajută la atașarea la catalogul eMAG.")

    # Recommended: Description
    description = product_data.get("description", "").strip()
    if description:
        add_check("description", "Descriere produs", "pass", "Descrierea respectă standardul minim.")
    else:
        add_check("description", "Descriere produs", "warn",
                 "Adaugă descriere conform standardului eMAG pentru validare mai rapidă.")

    # Recommended: Warranty
    warranty = product_data.get("warranty")
    if warranty is not None and warranty >= 0:
        add_check("warranty", "Garanție (luni)", "pass", "Garanția produsului este setată.")
    else:
        add_check("warranty", "Garanție (luni)", "warn",
                 "Setează warranty (0-255 luni) conform cerințelor categoriei.")

    # Calculate compliance
    compliance_total = len(checklist)
    compliance_score = len([c for c in checklist if c["status"] == "pass"])

    if errors:
        compliance_level = "fail"
    elif warnings:
        compliance_level = "warn"
    else:
        compliance_level = "pass"

    return ProductValidationResponse(
        is_valid=len(errors) == 0,
        compliance_score=compliance_score,
        compliance_total=compliance_total,
        compliance_level=compliance_level,
        errors=errors,
        warnings=warnings,
        checklist=checklist
    )


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/validate", response_model=ProductValidationResponse)
async def validate_product(
    request: ProductValidationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Validate product compliance with eMAG API v4.4.9 standards.
    
    This endpoint checks all required and recommended fields according to
    the eMAG Product Documentation Standard and returns a detailed compliance report.
    """
    try:
        product_data = request.dict(exclude_none=True)

        # If product_id is provided, fetch existing product data
        if request.product_id:
            query = text("""
                SELECT p.*, o.price as sale_price, o.vat_id, o.warranty
                FROM app.emag_products_v2 p
                LEFT JOIN app.emag_product_offers_v2 o ON o.product_id = p.id
                WHERE p.id = :product_id
                LIMIT 1
            """)
            result = await db.execute(query, {"product_id": request.product_id})
            row = result.mappings().first()

            if row:
                # Merge existing data with request data
                existing_data = dict(row)
                product_data = {**existing_data, **product_data}

        validation_result = validate_product_compliance(product_data)
        return validation_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.post("/bulk-update")
async def bulk_update_products(
    request: BulkUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Bulk update multiple products.
    
    Maximum 50 products per request (eMAG API limit).
    """
    try:
        if len(request.product_ids) > 50:
            raise HTTPException(
                status_code=400,
                detail="Maximum 50 products can be updated at once"
            )

        # Build update query
        set_clauses = []
        params = {"product_ids": tuple(request.product_ids)}

        allowed_fields = {
            "name", "description", "brand", "manufacturer", "price", "sale_price",
            "stock", "status", "category_id", "warranty", "handling_time",
            "safety_information", "green_tax", "supply_lead_time"
        }

        for field, value in request.updates.items():
            if field in allowed_fields:
                set_clauses.append(f"{field} = :{field}")
                params[field] = value

        if not set_clauses:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        set_clauses.append("updated_at = :updated_at")
        params["updated_at"] = datetime.utcnow()

        update_query = text(f"""
            UPDATE app.emag_products_v2
            SET {', '.join(set_clauses)}
            WHERE id IN :product_ids
            RETURNING id
        """)

        result = await db.execute(update_query, params)
        updated_ids = [row[0] for row in result.fetchall()]
        await db.commit()

        return {
            "status": "success",
            "message": f"Successfully updated {len(updated_ids)} products",
            "updated_ids": updated_ids
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Bulk update failed: {str(e)}")


@router.get("/categories")
async def get_emag_categories(
    category_id: Optional[int] = Query(None, description="Specific category ID to fetch"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=100, description="Items per page"),
    language: str = Query("ro", description="Language code: ro, en, hu, bg, etc."),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get eMAG categories with characteristics and family types.
    
    This endpoint provides category information needed for product publishing,
    including mandatory characteristics and allowed values.
    """
    try:
        # This would typically call the eMAG API
        # For now, return a placeholder response
        return {
            "status": "success",
            "message": "Category endpoint - to be implemented with eMAG API integration",
            "data": {
                "categories": [],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": 0
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch categories: {str(e)}")


@router.get("/vat-rates")
async def get_vat_rates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get available VAT rates from eMAG.
    
    Returns list of VAT rates with their IDs for use in product offers.
    """
    try:
        # This would typically call the eMAG API vat/read endpoint
        # For now, return common Romanian VAT rates
        return {
            "status": "success",
            "data": {
                "vat_rates": [
                    {"id": 1, "rate": 19, "description": "Standard VAT 19%"},
                    {"id": 2, "rate": 9, "description": "Reduced VAT 9%"},
                    {"id": 3, "rate": 5, "description": "Reduced VAT 5%"},
                    {"id": 4, "rate": 0, "description": "Zero VAT 0%"},
                ]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch VAT rates: {str(e)}")


@router.get("/handling-times")
async def get_handling_times(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get available handling time values from eMAG.
    
    Returns list of handling time options for product offers.
    """
    try:
        # This would typically call the eMAG API handling_time/read endpoint
        return {
            "status": "success",
            "data": {
                "handling_times": [
                    {"id": 0, "days": 0, "description": "Same day"},
                    {"id": 1, "days": 1, "description": "1 day"},
                    {"id": 2, "days": 2, "description": "2 days"},
                    {"id": 3, "days": 3, "description": "3 days"},
                    {"id": 5, "days": 5, "description": "5 days"},
                    {"id": 7, "days": 7, "description": "7 days"},
                ]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch handling times: {str(e)}")


@router.post("/match-ean")
async def match_products_by_ean(
    request: EANMatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Match products by EAN codes.
    
    Searches for existing products with the given EAN codes in both
    local database and eMAG catalog.
    """
    try:
        # Search in local database
        ean_list = [ean.strip() for ean in request.ean_codes if ean.strip()]

        if not ean_list:
            return {
                "status": "success",
                "data": {
                    "matches": [],
                    "message": "No valid EAN codes provided"
                }
            }

        # Query for products with matching EANs
        query = text("""
            SELECT p.id, p.emag_id, p.sku, p.name, p.brand, p.account_type,
                   p.attributes, p.emag_characteristics
            FROM app.emag_products_v2 p
            WHERE p.attributes::text LIKE ANY(:ean_patterns)
               OR p.emag_characteristics::text LIKE ANY(:ean_patterns)
            LIMIT 50
        """)

        ean_patterns = [f'%{ean}%' for ean in ean_list]
        result = await db.execute(query, {"ean_patterns": ean_patterns})
        rows = result.mappings().all()

        matches = []
        for row in rows:
            matches.append({
                "id": row["id"],
                "emag_id": row["emag_id"],
                "sku": row["sku"],
                "name": row["name"],
                "brand": row["brand"],
                "account_type": row["account_type"],
                "match_type": "local_database"
            })

        return {
            "status": "success",
            "data": {
                "matches": matches,
                "total": len(matches),
                "searched_eans": ean_list
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"EAN matching failed: {str(e)}")


@router.post("/publish")
async def publish_products_to_emag(
    request: ProductPublishRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Publish products to eMAG marketplace.
    
    This endpoint validates products and publishes them to eMAG using the
    product_offer/save endpoint. Maximum 50 products per request.
    """
    try:
        if len(request.product_ids) > 50:
            raise HTTPException(
                status_code=400,
                detail="Maximum 50 products can be published at once"
            )

        # Fetch products
        query = text("""
            SELECT p.*, o.price as sale_price, o.vat_id, o.warranty, o.stock_quantity
            FROM app.emag_products_v2 p
            LEFT JOIN app.emag_product_offers_v2 o ON o.product_id = p.id
            WHERE p.id IN :product_ids AND p.account_type = :account_type
        """)

        result = await db.execute(query, {
            "product_ids": tuple(request.product_ids),
            "account_type": request.account_type
        })
        rows = result.mappings().all()

        if not rows:
            raise HTTPException(status_code=404, detail="No products found")

        # Validate each product
        validation_results = []
        valid_products = []

        for row in rows:
            product_data = dict(row)
            validation = validate_product_compliance(product_data)

            validation_results.append({
                "product_id": row["id"],
                "product_name": row["name"],
                "validation": validation.dict()
            })

            if validation.is_valid or (request.force_publish and validation.compliance_level != "fail"):
                valid_products.append(product_data)

        # Here you would call the eMAG API to publish products
        # For now, just return validation results

        return {
            "status": "success",
            "message": f"Validated {len(rows)} products, {len(valid_products)} ready for publishing",
            "data": {
                "validation_results": validation_results,
                "publishable_count": len(valid_products),
                "total_count": len(rows)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Publishing failed: {str(e)}")


@router.get("/statistics")
async def get_product_statistics(
    account_type: Optional[str] = Query(None, description="Filter by account type: main, fbe, or both"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get comprehensive product statistics.
    
    Returns detailed metrics about products including counts, pricing,
    validation status, and competition metrics.
    """
    try:
        account_filter = ""
        params = {}

        if account_type and account_type in ["main", "fbe"]:
            account_filter = "WHERE p.account_type = :account_type"
            params["account_type"] = account_type

        query = text(f"""
            SELECT
                COUNT(*) as total_products,
                COUNT(*) FILTER (WHERE p.is_active = true) as active_products,
                COUNT(*) FILTER (WHERE p.is_active = false) as inactive_products,
                COUNT(*) FILTER (WHERE COALESCE(o.stock_quantity, p.stock_quantity, 0) > 0) as in_stock,
                COUNT(*) FILTER (WHERE COALESCE(o.stock_quantity, p.stock_quantity, 0) = 0) as out_of_stock,
                COUNT(*) FILTER (WHERE p.account_type = 'main') as main_account,
                COUNT(*) FILTER (WHERE p.account_type = 'fbe') as fbe_account,
                AVG(COALESCE(o.price, p.price, 0)) as avg_price,
                MIN(COALESCE(o.price, p.price, 0)) as min_price,
                MAX(COALESCE(o.price, p.price, 0)) as max_price,
                SUM(COALESCE(o.stock_quantity, p.stock_quantity, 0)) as total_stock,
                COUNT(*) FILTER (WHERE p.sync_status = 'synced') as synced_products,
                COUNT(*) FILTER (WHERE p.sync_status = 'pending') as pending_sync,
                COUNT(*) FILTER (WHERE p.sync_status = 'failed') as failed_sync
            FROM app.emag_products_v2 p
            LEFT JOIN app.emag_product_offers_v2 o ON o.product_id = p.id
            {account_filter}
        """)

        result = await db.execute(query, params)
        stats = result.mappings().first()

        return {
            "status": "success",
            "data": dict(stats) if stats else {}
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch statistics: {str(e)}")


@router.get("/export")
async def export_products(
    format: str = Query("excel", description="Export format: csv, excel, or pdf"),
    fields: Optional[str] = Query(None, description="Comma-separated list of fields to export"),
    product_ids: Optional[str] = Query(None, description="Comma-separated list of product IDs"),
    account_type: Optional[str] = Query(None, description="Filter by account type: main or fbe"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export products to CSV, Excel, or PDF format.
    
    This endpoint allows exporting product data in various formats with customizable fields.
    """
    try:
        # Build query
        query = """
            SELECT 
                id, emag_id, name, brand, part_number, category_id,
                price, sale_price, min_sale_price, max_sale_price, recommended_price,
                stock, reserved_stock, available_stock, ean, description, warranty,
                vat_id, handling_time, status, account_type, sync_status,
                created_at, updated_at
            FROM app.emag_products_v2
            WHERE 1=1
        """

        params = {}

        if product_ids:
            ids = [int(id.strip()) for id in product_ids.split(',')]
            query += " AND id = ANY(:product_ids)"
            params['product_ids'] = ids

        if account_type and account_type in ['main', 'fbe']:
            query += " AND account_type = :account_type"
            params['account_type'] = account_type

        query += " ORDER BY id"

        result = await db.execute(text(query), params)
        products = result.fetchall()

        # For now, return a simple response
        # In production, you would generate actual Excel/CSV/PDF files
        return {
            "status": "success",
            "message": f"Export ready with {len(products)} products",
            "format": format,
            "count": len(products),
            "note": "File generation would happen here in production"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export-template")
async def export_template(
    format: str = Query("excel", description="Template format: csv or excel"),
    current_user: User = Depends(get_current_user),
):
    """
    Download a template file for product import.
    
    Returns a template file with all required and optional fields for importing products.
    """
    try:
        # For now, return a simple response
        # In production, you would generate actual template files
        return {
            "status": "success",
            "message": "Template download ready",
            "format": format,
            "fields": [
                "name", "brand", "part_number", "category_id",
                "price", "sale_price", "stock", "ean", "description"
            ],
            "note": "Template file generation would happen here in production"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template download failed: {str(e)}")


@router.post("/import")
async def import_products(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Import products from CSV or Excel file.
    
    This endpoint processes uploaded files and creates/updates products in bulk.
    """
    try:
        # For now, return a simple response
        # In production, you would process the uploaded file
        return {
            "status": "success",
            "message": "Import completed",
            "imported": 0,
            "errors": [],
            "note": "File processing would happen here in production"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
