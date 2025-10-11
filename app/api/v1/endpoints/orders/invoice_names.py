"""
Invoice Names Management API.

Manages product names specifically for invoices (Romanian and English).
Used for customs declarations and VAT documentation.

Use Case:
- eMAG product names are often too long for invoices
- Need shorter, customs-friendly names
- Separate names for Romanian and English invoices
"""


from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.product import Product
from app.models.user import User
from app.security.jwt import get_current_user

router = APIRouter(prefix="/invoice-names", tags=["invoice-names"])


# ============================================================================
# Request/Response Models
# ============================================================================


class UpdateInvoiceNamesRequest(BaseModel):
    """Request to update invoice names for a product."""

    sku: str = Field(..., description="Product SKU")
    invoice_name_ro: str | None = Field(
        None, max_length=200, description="Romanian invoice name"
    )
    invoice_name_en: str | None = Field(
        None, max_length=200, description="English invoice name"
    )


class BulkUpdateInvoiceNamesRequest(BaseModel):
    """Request to update invoice names for multiple products."""

    updates: list[UpdateInvoiceNamesRequest] = Field(..., description="List of updates")


class InvoiceNameResponse(BaseModel):
    """Response with invoice names."""

    sku: str
    name: str  # Original eMAG name
    invoice_name_ro: str | None
    invoice_name_en: str | None
    has_invoice_names: bool


class GenerateInvoiceNameRequest(BaseModel):
    """Request to auto-generate invoice names."""

    sku: str
    max_length: int = Field(
        50, ge=20, le=200, description="Maximum length for generated names"
    )


# ============================================================================
# Get Invoice Names
# ============================================================================


@router.get("/{sku}", response_model=InvoiceNameResponse)
async def get_invoice_names(
    sku: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get invoice names for a product.

    Returns:
    - Original eMAG product name
    - Romanian invoice name (if set)
    - English invoice name (if set)
    - Flag indicating if custom invoice names are set
    """
    query = select(Product).where(Product.sku == sku)
    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail=f"Product {sku} not found")

    return InvoiceNameResponse(
        sku=product.sku,
        name=product.name,
        invoice_name_ro=product.invoice_name_ro,
        invoice_name_en=product.invoice_name_en,
        has_invoice_names=bool(product.invoice_name_ro or product.invoice_name_en),
    )


@router.get("/", response_model=list[InvoiceNameResponse])
async def list_products_with_invoice_names(
    has_invoice_names: bool | None = Query(
        None, description="Filter by presence of invoice names"
    ),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List products with their invoice names.

    Filters:
    - has_invoice_names=true: Only products with custom invoice names
    - has_invoice_names=false: Only products without custom invoice names
    - has_invoice_names=null: All products
    """
    query = select(Product).where(Product.is_active)

    if has_invoice_names is True:
        query = query.where(
            (Product.invoice_name_ro.isnot(None))
            | (Product.invoice_name_en.isnot(None))
        )
    elif has_invoice_names is False:
        query = query.where(
            (Product.invoice_name_ro.is_(None)) & (Product.invoice_name_en.is_(None))
        )

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    products = result.scalars().all()

    return [
        InvoiceNameResponse(
            sku=p.sku,
            name=p.name,
            invoice_name_ro=p.invoice_name_ro,
            invoice_name_en=p.invoice_name_en,
            has_invoice_names=bool(p.invoice_name_ro or p.invoice_name_en),
        )
        for p in products
    ]


# ============================================================================
# Update Invoice Names
# ============================================================================


@router.patch("/{sku}")
async def update_invoice_names(
    sku: str,
    invoice_name_ro: str | None = Query(None, max_length=200),
    invoice_name_en: str | None = Query(None, max_length=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update invoice names for a product.

    Example:
    ```
    PATCH /invoice-names/EMG331?invoice_name_ro=Generator%20XR2206&invoice_name_en=Signal%20Generator%20XR2206
    ```

    Use cases:
    - Shorten long eMAG names for invoices
    - Create customs-friendly descriptions
    - Standardize product names across invoices
    """
    query = select(Product).where(Product.sku == sku)
    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail=f"Product {sku} not found")

    if invoice_name_ro is not None:
        product.invoice_name_ro = invoice_name_ro

    if invoice_name_en is not None:
        product.invoice_name_en = invoice_name_en

    await db.commit()
    await db.refresh(product)

    return {
        "status": "success",
        "message": f"Invoice names updated for {sku}",
        "data": InvoiceNameResponse(
            sku=product.sku,
            name=product.name,
            invoice_name_ro=product.invoice_name_ro,
            invoice_name_en=product.invoice_name_en,
            has_invoice_names=bool(product.invoice_name_ro or product.invoice_name_en),
        ),
    }


@router.post("/bulk-update")
async def bulk_update_invoice_names(
    request: BulkUpdateInvoiceNamesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update invoice names for multiple products at once.

    Example:
    ```json
    {
      "updates": [
        {
          "sku": "EMG331",
          "invoice_name_ro": "Generator XR2206",
          "invoice_name_en": "Signal Generator XR2206"
        },
        {
          "sku": "EMG332",
          "invoice_name_ro": "Modul amplificator",
          "invoice_name_en": "Amplifier module"
        }
      ]
    }
    ```
    """
    results = []

    for update_req in request.updates:
        try:
            query = select(Product).where(Product.sku == update_req.sku)
            result = await db.execute(query)
            product = result.scalar_one_or_none()

            if not product:
                results.append(
                    {
                        "sku": update_req.sku,
                        "status": "error",
                        "message": "Product not found",
                    }
                )
                continue

            if update_req.invoice_name_ro is not None:
                product.invoice_name_ro = update_req.invoice_name_ro

            if update_req.invoice_name_en is not None:
                product.invoice_name_en = update_req.invoice_name_en

            results.append(
                {"sku": update_req.sku, "status": "success", "message": "Updated"}
            )

        except Exception as e:
            results.append(
                {"sku": update_req.sku, "status": "error", "message": str(e)}
            )

    await db.commit()

    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = sum(1 for r in results if r["status"] == "error")

    return {
        "status": "success",
        "message": f"Updated {success_count} products, {error_count} errors",
        "data": {
            "results": results,
            "summary": {
                "total": len(results),
                "success": success_count,
                "errors": error_count,
            },
        },
    }


# ============================================================================
# Auto-Generate Invoice Names
# ============================================================================


@router.post("/generate/{sku}")
async def generate_invoice_names(
    sku: str,
    max_length: int = Query(50, ge=20, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Auto-generate invoice names from original product name.

    Algorithm:
    1. Take original eMAG name
    2. Remove unnecessary words (cu, pentru, de, etc.)
    3. Truncate to max_length
    4. Keep essential information (brand, model, key features)

    Example:
    - Original: "Generator de semnal de inalta precizie XR2206 cu carcasa, 1Hz-1Mhz"
    - Generated RO: "Generator XR2206 1Hz-1MHz"
    - Generated EN: "Signal Generator XR2206 1Hz-1MHz"
    """
    query = select(Product).where(Product.sku == sku)
    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail=f"Product {sku} not found")

    original_name = product.name

    # Simple algorithm to shorten name
    # Remove common Romanian filler words
    ro_stopwords = [" de ", " cu ", " pentru ", " din ", " la ", " si ", " sau "]
    name_ro = original_name
    for word in ro_stopwords:
        name_ro = name_ro.replace(word, " ")

    # Clean up multiple spaces
    name_ro = " ".join(name_ro.split())

    # Truncate if needed
    if len(name_ro) > max_length:
        name_ro = name_ro[:max_length].rsplit(" ", 1)[0]  # Cut at last space

    # Generate English version (basic translation of common terms)
    translations = {
        "Generator": "Generator",
        "Modul": "Module",
        "Placa": "Board",
        "Senzor": "Sensor",
        "Display": "Display",
        "Cablu": "Cable",
        "Adaptor": "Adapter",
    }

    name_en = name_ro
    for ro, en in translations.items():
        name_en = name_en.replace(ro, en)

    # Update product
    product.invoice_name_ro = name_ro
    product.invoice_name_en = name_en

    await db.commit()
    await db.refresh(product)

    return {
        "status": "success",
        "message": "Invoice names generated",
        "data": {
            "sku": product.sku,
            "original_name": original_name,
            "generated_ro": name_ro,
            "generated_en": name_en,
            "length_ro": len(name_ro),
            "length_en": len(name_en),
        },
    }


# ============================================================================
# Clear Invoice Names
# ============================================================================


@router.delete("/{sku}")
async def clear_invoice_names(
    sku: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Clear invoice names for a product (revert to using original eMAG name).
    """
    query = select(Product).where(Product.sku == sku)
    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail=f"Product {sku} not found")

    product.invoice_name_ro = None
    product.invoice_name_en = None

    await db.commit()

    return {
        "status": "success",
        "message": f"Invoice names cleared for {sku}",
        "note": "Product will use original eMAG name on invoices",
    }
