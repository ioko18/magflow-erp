"""
eMAG Phase 2 API Endpoints for MagFlow ERP.

This module provides REST API endpoints for Phase 2 features:
- AWB Management
- EAN Product Matching
- Invoice Generation
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.user import User
from app.services.emag.emag_awb_service import EmagAWBService
from app.services.emag.emag_ean_matching_service import EmagEANMatchingService
from app.services.emag.emag_invoice_service import EmagInvoiceService

logger = get_logger(__name__)

router = APIRouter()


# ========== Request/Response Models ==========


class AWBGenerateRequest(BaseModel):
    """Request model for AWB generation."""

    account_type: str = Field(..., description="Account type (main or fbe)")
    courier_account_id: int = Field(..., description="Courier service ID")
    packages: list[dict[str, Any]] | None = Field(
        None, description="Package details"
    )


class AWBBulkGenerateRequest(BaseModel):
    """Request model for bulk AWB generation."""

    account_type: str = Field(..., description="Account type (main or fbe)")
    courier_account_id: int = Field(..., description="Courier service ID")
    orders: list[dict[str, Any]] = Field(
        ..., description="List of orders with order_id and optional packages"
    )


class EANSearchRequest(BaseModel):
    """Request model for EAN search."""

    account_type: str = Field(..., description="Account type (main or fbe)")
    ean: str = Field(..., description="EAN barcode to search")


class EANBulkSearchRequest(BaseModel):
    """Request model for bulk EAN search."""

    account_type: str = Field(..., description="Account type (main or fbe)")
    eans: list[str] = Field(..., description="List of EAN barcodes (max 100)")


class EANMatchRequest(BaseModel):
    """Request model for EAN matching."""

    account_type: str = Field(..., description="Account type (main or fbe)")
    ean: str = Field(..., description="EAN barcode")
    product_data: dict[str, Any] | None = Field(
        None, description="Optional local product data"
    )


class InvoiceGenerateRequest(BaseModel):
    """Request model for invoice generation."""

    account_type: str = Field(..., description="Account type (main or fbe)")
    invoice_url: str | None = Field(
        None, description="Optional pre-generated invoice URL"
    )


class InvoiceBulkGenerateRequest(BaseModel):
    """Request model for bulk invoice generation."""

    account_type: str = Field(..., description="Account type (main or fbe)")
    order_ids: list[int] = Field(..., description="List of order IDs")


# ========== AWB Management Endpoints ==========


@router.get("/awb/couriers", status_code=status.HTTP_200_OK)
async def get_courier_accounts(
    account_type: str = Query(..., description="Account type (main or fbe)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get available courier accounts for seller."""
    logger.info(
        "User %s fetching courier accounts for %s", current_user.email, account_type
    )

    try:
        async with EmagAWBService(account_type, db) as awb_service:
            result = await awb_service.get_courier_accounts()
            return result

    except Exception as e:
        logger.error("Failed to fetch courier accounts: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch courier accounts: {str(e)}",
        ) from e


@router.post("/awb/{order_id}/generate", status_code=status.HTTP_200_OK)
async def generate_awb(
    order_id: int,
    request: AWBGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate AWB for order shipment."""
    logger.info("User %s generating AWB for order %d", current_user.email, order_id)

    try:
        async with EmagAWBService(request.account_type, db) as awb_service:
            result = await awb_service.generate_awb(
                order_id=order_id,
                courier_account_id=request.courier_account_id,
                packages=request.packages,
            )
            return result

    except Exception as e:
        logger.error("Failed to generate AWB: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate AWB: {str(e)}",
        ) from e


@router.get("/awb/{awb_number}", status_code=status.HTTP_200_OK)
async def get_awb_details(
    awb_number: str,
    account_type: str = Query(..., description="Account type (main or fbe)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get AWB tracking details."""
    logger.info("User %s fetching AWB details for %s", current_user.email, awb_number)

    try:
        async with EmagAWBService(account_type, db) as awb_service:
            result = await awb_service.get_awb_details(awb_number)
            return result

    except Exception as e:
        logger.error("Failed to fetch AWB details: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch AWB details: {str(e)}",
        ) from e


@router.post("/awb/bulk-generate", status_code=status.HTTP_200_OK)
async def bulk_generate_awbs(
    request: AWBBulkGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate AWBs for multiple orders."""
    logger.info(
        "User %s bulk generating AWBs for %d orders",
        current_user.email,
        len(request.orders),
    )

    try:
        async with EmagAWBService(request.account_type, db) as awb_service:
            result = await awb_service.bulk_generate_awbs(
                orders=request.orders, courier_account_id=request.courier_account_id
            )
            return result

    except Exception as e:
        logger.error("Failed to bulk generate AWBs: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk generate AWBs: {str(e)}",
        ) from e


# ========== EAN Product Matching Endpoints ==========


@router.post("/ean/search", status_code=status.HTTP_200_OK)
async def search_product_by_ean(
    request: EANSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Search for products on eMAG by EAN code."""
    logger.info("User %s searching EAN: %s", current_user.email, request.ean)

    try:
        async with EmagEANMatchingService(request.account_type, db) as ean_service:
            result = await ean_service.find_products_by_ean(request.ean)
            return result

    except Exception as e:
        logger.error("Failed to search EAN: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search EAN: {str(e)}",
        ) from e


@router.post("/ean/bulk-search", status_code=status.HTTP_200_OK)
async def bulk_search_products_by_ean(
    request: EANBulkSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Search for multiple products by EAN codes."""
    logger.info("User %s bulk searching %d EANs", current_user.email, len(request.eans))

    try:
        async with EmagEANMatchingService(request.account_type, db) as ean_service:
            result = await ean_service.bulk_find_products_by_eans(request.eans)
            return result

    except Exception as e:
        logger.error("Failed to bulk search EANs: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk search EANs: {str(e)}",
        ) from e


@router.post("/ean/match", status_code=status.HTTP_200_OK)
async def match_or_suggest_product(
    request: EANMatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Smart product matching: find existing or suggest new product creation."""
    logger.info("User %s matching EAN: %s", current_user.email, request.ean)

    try:
        async with EmagEANMatchingService(request.account_type, db) as ean_service:
            result = await ean_service.match_or_suggest_product(
                ean=request.ean, product_data=request.product_data
            )
            return result

    except Exception as e:
        logger.error("Failed to match EAN: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to match EAN: {str(e)}",
        ) from e


@router.get("/ean/validate/{ean}", status_code=status.HTTP_200_OK)
async def validate_ean(
    ean: str,
    account_type: str = Query(..., description="Account type (main or fbe)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Validate EAN format and checksum."""
    logger.info("User %s validating EAN: %s", current_user.email, ean)

    try:
        async with EmagEANMatchingService(account_type, db) as ean_service:
            result = await ean_service.validate_ean_format(ean)
            return result

    except Exception as e:
        logger.error("Failed to validate EAN: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate EAN: {str(e)}",
        ) from e


# ========== Invoice Generation Endpoints ==========


@router.get("/invoice/{order_id}/data", status_code=status.HTTP_200_OK)
async def get_invoice_data(
    order_id: int,
    account_type: str = Query(..., description="Account type (main or fbe)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate invoice data from order."""
    logger.info(
        "User %s generating invoice data for order %d", current_user.email, order_id
    )

    try:
        async with EmagInvoiceService(account_type, db) as invoice_service:
            result = await invoice_service.generate_invoice_data(order_id)
            return result

    except Exception as e:
        logger.error("Failed to generate invoice data: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate invoice data: {str(e)}",
        ) from e


@router.post("/invoice/{order_id}/generate", status_code=status.HTTP_200_OK)
async def generate_and_attach_invoice(
    order_id: int,
    request: InvoiceGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate invoice PDF and attach to order."""
    logger.info("User %s generating invoice for order %d", current_user.email, order_id)

    try:
        async with EmagInvoiceService(request.account_type, db) as invoice_service:
            result = await invoice_service.generate_and_attach_invoice(
                order_id=order_id, invoice_url=request.invoice_url
            )
            return result

    except Exception as e:
        logger.error("Failed to generate invoice: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate invoice: {str(e)}",
        ) from e


@router.post("/invoice/bulk-generate", status_code=status.HTTP_200_OK)
async def bulk_generate_invoices(
    request: InvoiceBulkGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate invoices for multiple orders."""
    logger.info(
        "User %s bulk generating invoices for %d orders",
        current_user.email,
        len(request.order_ids),
    )

    try:
        async with EmagInvoiceService(request.account_type, db) as invoice_service:
            result = await invoice_service.bulk_generate_invoices(request.order_ids)
            return result

    except Exception as e:
        logger.error("Failed to bulk generate invoices: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk generate invoices: {str(e)}",
        ) from e
