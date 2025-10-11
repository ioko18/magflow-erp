"""eMAG Integration endpoints for RMA, Cancellations, and Invoices."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_async_session
from app.db.models import User
from app.emag.client import EmagAccountType, EmagAPIWrapper

router = APIRouter(prefix="/integration", tags=["emag-integration"])


@router.get("/status")
async def get_emag_integration_status(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Get eMAG integration status for all flows."""
    try:
        async with EmagAPIWrapper(account_type=EmagAccountType.MAIN) as client:
            result = await client.test_connection()

        return {
            "status": "success",
            "integration_status": {
                "connected": result.get("status") == "connected",
                "account_type": "main",
                "supported_flows": [
                    "product_offers",
                    "rma_management",
                    "order_cancellations",
                    "invoice_management",
                ],
            },
            "connection_test": result,
            "message": "eMAG integration status retrieved",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check eMAG integration: {e!s}",
        )


@router.post("/test-connection")
async def test_emag_connection(
    account_type: str = "main",
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Test connection to eMAG API."""
    try:
        async with EmagAPIWrapper(account_type=EmagAccountType(account_type)) as client:
            result = await client.test_connection()

        return {
            "status": "success",
            "connection_test": result,
            "message": "eMAG connection test completed",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"eMAG connection test failed: {e!s}",
        )


@router.get("/flows")
async def get_supported_flows(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Get list of supported eMAG integration flows."""
    return {
        "status": "success",
        "supported_flows": {
            "rma_management": {
                "description": "Returns Management (RMA)",
                "endpoints": [
                    "POST /rma/create",
                    "POST /rma/update_status",
                    "GET /rma/{rma_id}",
                ],
                "status": "ready",
            },
            "order_cancellations": {
                "description": "Order Cancellation Processing",
                "endpoints": ["POST /order/cancel", "POST /order/process_refund"],
                "status": "ready",
            },
            "invoice_management": {
                "description": "Invoice Creation and Management",
                "endpoints": [
                    "POST /invoice/create",
                    "POST /invoice/update_payment",
                    "GET /invoice/{invoice_id}",
                ],
                "status": "ready",
            },
        },
        "message": "Supported eMAG integration flows retrieved",
    }


@router.get("/configuration")
async def get_emag_configuration(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """Get eMAG integration configuration details."""
    return {
        "status": "success",
        "configuration": {
            "api_base_url": "https://marketplace.emag.ro/api-3",
            "supported_account_types": ["main", "fbe"],
            "rate_limits": {
                "orders": "12 requests/second",
                "offers": "3 requests/second",
                "rma": "5 requests/second",
                "invoices": "3 requests/second",
                "other": "3 requests/second",
            },
            "features": {
                "product_offers": True,
                "rma_management": True,
                "order_cancellations": True,
                "invoice_management": True,
                "automatic_retry": True,
                "rate_limiting": True,
                "error_handling": True,
            },
            "authentication": {"method": "placeholder", "status": "configured"},
        },
        "message": "eMAG integration configuration retrieved",
    }
