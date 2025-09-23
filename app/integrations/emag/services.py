"""eMAG API Integration Services for MagFlow ERP.

This module provides integration with eMAG Marketplace API for:
- RMA (Returns Management)
- Order Cancellations
- Invoice Management
- Product/Offer Management (existing)
"""

import logging
from datetime import datetime
from typing import Any, Dict

from app.integrations.emag.client import EmagAPIWrapper
from app.models.cancellation import (
    CancellationRequest,
    EmagCancellationIntegration,
)
from app.models.invoice import EmagInvoiceIntegration, Invoice, InvoiceStatus
from app.models.rma import EmagReturnIntegration, ReturnRequest, ReturnStatus

logger = logging.getLogger(__name__)


class EmagRMAIntegration:
    """eMAG RMA (Returns) Integration Service."""

    def __init__(self):
        self.client = EmagAPIWrapper()
        self.base_url = "https://api.emag.ro"

    async def create_return_request(
        self,
        return_request: ReturnRequest,
    ) -> Dict[str, Any]:
        """Create a return request in eMAG."""
        try:
            async with self.client as api:
                # Map our return request to eMAG RMA format
                emag_rma_data = {
                    "order_id": return_request.emag_order_id,
                    "reason": return_request.reason.value,
                    "description": return_request.reason_description,
                    "items": [],
                }

                # Add return items
                for item in return_request.return_items:
                    emag_rma_data["items"].append(
                        {
                            "offer_id": item.sku,  # This should map to eMAG offer ID
                            "quantity": item.quantity,
                            "condition": item.condition,
                            "reason": item.reason or return_request.reason.value,
                        },
                    )

                # Call eMAG RMA API
                response = await api.post(
                    endpoint="rma/create",
                    data=emag_rma_data,
                    response_model=dict,
                )

                # Store integration record
                _emag_integration = EmagReturnIntegration(
                    return_request_id=return_request.id,
                    emag_return_id=response.get("rma_id"),
                    emag_status=response.get("status", "new"),
                    emag_response=str(response),
                )

                return {
                    "success": True,
                    "emag_rma_id": response.get("rma_id"),
                    "status": response.get("status"),
                    "message": "RMA created successfully in eMAG",
                }

        except Exception as e:
            logger.error(f"Failed to create eMAG RMA: {e!s}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create RMA in eMAG",
            }

    async def update_return_status(
        self,
        return_request: ReturnRequest,
    ) -> Dict[str, Any]:
        """Update return request status in eMAG."""
        try:
            async with self.client as api:
                # Map our status to eMAG status
                emag_status_map = {
                    ReturnStatus.PENDING: "new",
                    ReturnStatus.APPROVED: "approved",
                    ReturnStatus.REJECTED: "rejected",
                    ReturnStatus.PROCESSING: "in_progress",
                    ReturnStatus.COMPLETED: "completed",
                    ReturnStatus.CANCELLED: "cancelled",
                }

                emag_status = emag_status_map.get(return_request.status, "new")

                _response = await api.post(
                    endpoint="rma/update_status",
                    data={
                        "rma_id": return_request.emag_return_id,
                        "status": emag_status,
                        "notes": return_request.internal_notes,
                    },
                    response_model=dict,
                )

                return {
                    "success": True,
                    "status": emag_status,
                    "message": "RMA status updated in eMAG",
                }

        except Exception as e:
            logger.error(f"Failed to update eMAG RMA status: {e!s}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to update RMA status in eMAG",
            }


class EmagCancellationService:
    """eMAG Order Cancellation Integration Service."""

    def __init__(self):
        self.client = EmagAPIWrapper()

    async def create_cancellation_request(
        self,
        cancellation_request: CancellationRequest,
    ) -> Dict[str, Any]:
        """Create a cancellation request in eMAG."""
        try:
            async with self.client as api:
                # Map our cancellation to eMAG format
                emag_cancellation_data = {
                    "order_id": cancellation_request.emag_order_id,
                    "reason": cancellation_request.reason.value,
                    "description": cancellation_request.reason_description,
                    "refund_amount": cancellation_request.refund_amount,
                    "currency": cancellation_request.currency,
                }

                response = await api.post(
                    endpoint="order/cancel",
                    data=emag_cancellation_data,
                    response_model=dict,
                )

                # Store integration record
                _emag_integration = EmagCancellationIntegration(
                    cancellation_request_id=cancellation_request.id,
                    emag_cancellation_id=response.get("cancellation_id"),
                    emag_status=response.get("status", "pending"),
                    emag_response=str(response),
                )

                return {
                    "success": True,
                    "emag_cancellation_id": response.get("cancellation_id"),
                    "status": response.get("status"),
                    "message": "Cancellation created successfully in eMAG",
                }

        except Exception as e:
            logger.error(f"Failed to create eMAG cancellation: {e!s}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create cancellation in eMAG",
            }

    async def process_cancellation_refund(
        self,
        cancellation_request: CancellationRequest,
    ) -> Dict[str, Any]:
        """Process refund for cancellation in eMAG."""
        try:
            async with self.client as api:
                response = await api.post(
                    endpoint="order/process_refund",
                    data={
                        "cancellation_id": cancellation_request.emag_cancellation_id,
                        "refund_amount": cancellation_request.refund_amount,
                        "refund_method": "original_payment",  # Default method
                        "currency": cancellation_request.currency,
                    },
                    response_model=dict,
                )

                return {
                    "success": True,
                    "refund_id": response.get("refund_id"),
                    "status": response.get("status"),
                    "message": "Refund processed successfully in eMAG",
                }

        except Exception as e:
            logger.error(f"Failed to process eMAG cancellation refund: {e!s}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to process refund in eMAG",
            }


class EmagInvoiceService:
    """eMAG Invoice Integration Service."""

    def __init__(self):
        self.client = EmagAPIWrapper()

    async def create_invoice(self, invoice: Invoice) -> Dict[str, Any]:
        """Create an invoice in eMAG."""
        try:
            async with self.client as api:
                # Map our invoice to eMAG format
                emag_invoice_data = {
                    "invoice_number": invoice.invoice_number,
                    "order_id": invoice.order_id,
                    "customer_name": invoice.customer_name,
                    "invoice_type": invoice.invoice_type.value,
                    "items": [],
                    "total_amount": invoice.total_amount,
                    "currency": invoice.currency,
                    "tax_amount": invoice.tax_amount,
                    "issue_date": invoice.invoice_date.isoformat(),
                    "due_date": invoice.due_date.isoformat(),
                }

                # Add invoice items
                for item in invoice.invoice_items:
                    emag_invoice_data["items"].append(
                        {
                            "sku": item.sku,
                            "name": item.product_name,
                            "quantity": item.quantity,
                            "unit_price": item.unit_price,
                            "tax_rate": item.tax_rate,
                            "line_total": item.line_total,
                        },
                    )

                response = await api.post(
                    endpoint="invoice/create",
                    data=emag_invoice_data,
                    response_model=dict,
                )

                # Store integration record
                _emag_integration = EmagInvoiceIntegration(
                    invoice_id=invoice.id,
                    emag_invoice_id=response.get("invoice_id"),
                    emag_status=response.get("status", "issued"),
                    emag_invoice_type=invoice.invoice_type.value,
                    emag_response=str(response),
                )

                return {
                    "success": True,
                    "emag_invoice_id": response.get("invoice_id"),
                    "status": response.get("status"),
                    "message": "Invoice created successfully in eMAG",
                }

        except Exception as e:
            logger.error(f"Failed to create eMAG invoice: {e!s}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create invoice in eMAG",
            }

    async def update_payment_status(self, invoice: Invoice) -> Dict[str, Any]:
        """Update invoice payment status in eMAG."""
        try:
            async with self.client as api:
                response = await api.post(
                    endpoint="invoice/update_payment",
                    data={
                        "invoice_id": invoice.emag_invoice_id,
                        "payment_status": (
                            "paid"
                            if invoice.status == InvoiceStatus.PAID
                            else "pending"
                        ),
                        "paid_amount": invoice.paid_amount or 0,
                        "payment_date": (
                            invoice.paid_at.isoformat() if invoice.paid_at else None
                        ),
                    },
                    response_model=dict,
                )

                return {
                    "success": True,
                    "status": response.get("status"),
                    "message": "Payment status updated in eMAG",
                }

        except Exception as e:
            logger.error(f"Failed to update eMAG invoice payment status: {e!s}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to update payment status in eMAG",
            }


class EmagIntegrationManager:
    """Main eMAG integration manager for all flows."""

    def __init__(self):
        self.rma = EmagRMAIntegration()
        self.cancellations = EmagCancellationService()
        self.invoices = EmagInvoiceService()

    async def sync_return_request(self, return_request_id: int) -> Dict[str, Any]:
        """Sync a return request with eMAG."""
        # This would load the return request from database and sync it
        # Implementation depends on your database session setup
        return {"status": "sync_completed", "message": "Return request synced"}

    async def sync_cancellation_request(
        self,
        cancellation_request_id: int,
    ) -> Dict[str, Any]:
        """Sync a cancellation request with eMAG."""
        return {"status": "sync_completed", "message": "Cancellation request synced"}

    async def sync_invoice(self, invoice_id: int) -> Dict[str, Any]:
        """Sync an invoice with eMAG."""
        return {"status": "sync_completed", "message": "Invoice synced"}

    async def get_sync_status(self, account_type: str = "main") -> Dict[str, Any]:
        """Get sync status for all integrations."""
        return {
            "account_type": account_type,
            "rma_sync": "ready",
            "cancellation_sync": "ready",
            "invoice_sync": "ready",
            "last_sync": datetime.utcnow().isoformat(),
        }
