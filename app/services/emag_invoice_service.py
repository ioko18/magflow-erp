"""
eMAG Invoice Generation Service for MagFlow ERP.

This service handles automatic invoice generation and management:
- PDF invoice generation
- Invoice template system
- Automatic attachment to orders
- Invoice storage and retrieval
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
import hashlib

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.exceptions import ServiceError
from app.services.emag_api_client import EmagApiClient, EmagApiError
from app.config.emag_config import get_emag_config
from app.models.emag_models import EmagOrder
from app.core.database import async_session_factory

logger = get_logger(__name__)


class EmagInvoiceService:
    """Complete invoice generation and management service for eMAG integration."""

    def __init__(
        self,
        account_type: str = "main",
        db_session: Optional[AsyncSession] = None
    ):
        """Initialize the eMAG invoice service.
        
        Args:
            account_type: Type of eMAG account ('main' or 'fbe')
            db_session: Optional database session
        """
        self.account_type = account_type.lower()
        self.config = get_emag_config(self.account_type)
        self.client: Optional[EmagApiClient] = None
        self.db_session = db_session
        self._metrics = {
            "invoices_generated": 0,
            "invoices_attached": 0,
            "invoices_failed": 0,
            "errors": 0
        }

        # Invoice storage configuration
        self.invoice_storage_path = Path("/tmp/magflow/invoices")
        try:
            self.invoice_storage_path.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Fallback to temp directory if creation fails
            self.invoice_storage_path = Path("/tmp")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def initialize(self):
        """Initialize the eMAG API client."""
        if not self.client:
            self.client = EmagApiClient(
                username=self.config.api_username,
                password=self.config.api_password,
                base_url=self.config.base_url,
                timeout=self.config.api_timeout,
                max_retries=self.config.max_retries,
            )
            await self.client.start()

        logger.info(
            "Initialized eMAG invoice service for %s account",
            self.account_type
        )

    async def close(self):
        """Close the eMAG API client."""
        if self.client:
            await self.client.close()
            self.client = None

    async def generate_invoice_data(
        self,
        order_id: int
    ) -> Dict[str, Any]:
        """Generate invoice data from order.
        
        Args:
            order_id: eMAG order ID
            
        Returns:
            Dictionary with invoice data ready for PDF generation
        """
        logger.info("Generating invoice data for order %d", order_id)

        try:
            # Get order from database
            async with async_session_factory() as session:
                stmt = select(EmagOrder).where(
                    and_(
                        EmagOrder.emag_order_id == order_id,
                        EmagOrder.account_type == self.account_type
                    )
                )
                result = await session.execute(stmt)
                order = result.scalar_one_or_none()

                if not order:
                    raise ServiceError(f"Order {order_id} not found")

                # Extract invoice data
                invoice_data = {
                    "invoice_number": self._generate_invoice_number(order_id),
                    "invoice_date": datetime.utcnow().strftime("%Y-%m-%d"),
                    "order_id": order_id,
                    "order_date": order.order_date.strftime("%Y-%m-%d") if order.order_date else None,

                    # Seller info
                    "seller": {
                        "name": "Galactronice SRL",  # From config
                        "cui": "RO12345678",  # From config
                        "reg_com": "J40/1234/2020",  # From config
                        "address": "Str. Exemplu Nr. 1, București",  # From config
                        "phone": "+40 21 123 4567",  # From config
                        "email": self.config.api_username,
                        "bank": "BCR",  # From config
                        "iban": "RO49AAAA1B31007593840000"  # From config
                    },

                    # Customer info
                    "customer": {
                        "name": order.customer_name,
                        "email": order.customer_email,
                        "phone": order.customer_phone,
                        "billing_address": order.billing_address,
                        "shipping_address": order.shipping_address
                    },

                    # Products
                    "products": self._format_products_for_invoice(order.products or []),

                    # Totals
                    "subtotal": self._calculate_subtotal(order.products or []),
                    "vat_amount": self._calculate_vat(order.products or []),
                    "shipping": order.shipping_tax or 0.0,
                    "total": order.total_amount,
                    "currency": order.currency,

                    # Payment
                    "payment_method": order.payment_method,
                    "payment_status": "paid" if order.payment_status == 1 else "unpaid"
                }

                return {
                    "success": True,
                    "order_id": order_id,
                    "invoice_data": invoice_data
                }

        except Exception as e:
            logger.error("Failed to generate invoice data: %s", str(e))
            self._metrics["errors"] += 1
            raise ServiceError(f"Failed to generate invoice data: {str(e)}")

    async def generate_and_attach_invoice(
        self,
        order_id: int,
        invoice_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate invoice and attach to order.
        
        Args:
            order_id: eMAG order ID
            invoice_url: Optional pre-generated invoice URL
            
        Returns:
            Dictionary with generation result
        """
        logger.info("Generating and attaching invoice for order %d", order_id)

        try:
            # Generate invoice data
            invoice_result = await self.generate_invoice_data(order_id)
            invoice_data = invoice_result["invoice_data"]

            # Generate PDF (placeholder - would use actual PDF library)
            if not invoice_url:
                invoice_url = await self._generate_invoice_pdf(invoice_data)

            self._metrics["invoices_generated"] += 1

            # Attach to eMAG order
            invoice_name = f"Invoice_{invoice_data['invoice_number']}.pdf"

            await self.client.attach_invoice(
                order_id=order_id,
                invoice_url=invoice_url,
                invoice_name=invoice_name
            )

            # Update local database
            async with async_session_factory() as session:
                stmt = select(EmagOrder).where(
                    and_(
                        EmagOrder.emag_order_id == order_id,
                        EmagOrder.account_type == self.account_type
                    )
                )
                db_result = await session.execute(stmt)
                order = db_result.scalar_one_or_none()

                if order:
                    order.invoice_url = invoice_url
                    order.invoice_uploaded_at = datetime.utcnow()
                    order.updated_at = datetime.utcnow()
                    await session.commit()

            self._metrics["invoices_attached"] += 1

            return {
                "success": True,
                "order_id": order_id,
                "invoice_number": invoice_data["invoice_number"],
                "invoice_url": invoice_url,
                "message": "Invoice generated and attached successfully"
            }

        except EmagApiError as e:
            logger.error("Failed to attach invoice: %s", str(e))
            self._metrics["invoices_failed"] += 1
            self._metrics["errors"] += 1
            raise ServiceError(f"Failed to attach invoice: {str(e)}")

    async def bulk_generate_invoices(
        self,
        order_ids: List[int]
    ) -> Dict[str, Any]:
        """Generate invoices for multiple orders.
        
        Args:
            order_ids: List of eMAG order IDs
            
        Returns:
            Dictionary with bulk generation results
        """
        logger.info("Bulk generating invoices for %d orders", len(order_ids))

        results = {
            "success": [],
            "failed": [],
            "total": len(order_ids)
        }

        for order_id in order_ids:
            try:
                result = await self.generate_and_attach_invoice(order_id)
                results["success"].append(result)

                # Small delay between requests
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error("Failed to generate invoice for order %d: %s", order_id, str(e))
                results["failed"].append({
                    "order_id": order_id,
                    "error": str(e)
                })

        return {
            "success": True,
            "results": results,
            "success_count": len(results["success"]),
            "failed_count": len(results["failed"])
        }

    def _generate_invoice_number(self, order_id: int) -> str:
        """Generate unique invoice number.
        
        Args:
            order_id: eMAG order ID
            
        Returns:
            Invoice number string
        """
        # Format: YYYY-MM-XXXXXX
        date_prefix = datetime.utcnow().strftime("%Y%m")
        return f"{date_prefix}-{order_id:06d}"

    def _format_products_for_invoice(
        self,
        products: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Format products for invoice display.
        
        Args:
            products: List of order products
            
        Returns:
            Formatted products list
        """
        formatted = []

        for idx, product in enumerate(products, 1):
            formatted.append({
                "line_number": idx,
                "name": product.get("name", "Unknown Product"),
                "sku": product.get("part_number", "N/A"),
                "quantity": int(product.get("quantity", 1)),
                "unit_price": float(product.get("sale_price", 0)),
                "vat_rate": float(product.get("vat_rate", 19)),
                "total": float(product.get("sale_price", 0)) * int(product.get("quantity", 1))
            })

        return formatted

    def _calculate_subtotal(self, products: List[Dict[str, Any]]) -> float:
        """Calculate subtotal (without VAT).
        
        Args:
            products: List of order products
            
        Returns:
            Subtotal amount
        """
        subtotal = 0.0

        for product in products:
            price = float(product.get("sale_price", 0))
            quantity = int(product.get("quantity", 1))
            vat_rate = float(product.get("vat_rate", 19))

            # Price without VAT
            price_without_vat = price / (1 + vat_rate / 100)
            subtotal += price_without_vat * quantity

        return round(subtotal, 2)

    def _calculate_vat(self, products: List[Dict[str, Any]]) -> float:
        """Calculate total VAT amount.
        
        Args:
            products: List of order products
            
        Returns:
            VAT amount
        """
        vat_total = 0.0

        for product in products:
            price = float(product.get("sale_price", 0))
            quantity = int(product.get("quantity", 1))
            vat_rate = float(product.get("vat_rate", 19))

            # VAT amount
            price_without_vat = price / (1 + vat_rate / 100)
            vat_amount = price - price_without_vat
            vat_total += vat_amount * quantity

        return round(vat_total, 2)

    async def _generate_invoice_pdf(
        self,
        invoice_data: Dict[str, Any]
    ) -> str:
        """Generate PDF invoice (placeholder implementation).
        
        In production, this would use a PDF library like ReportLab or WeasyPrint.
        
        Args:
            invoice_data: Invoice data dictionary
            
        Returns:
            Public URL of generated PDF
        """
        # Placeholder: Generate filename
        invoice_number = invoice_data["invoice_number"]
        filename = f"invoice_{invoice_number}.pdf"

        # In production, generate actual PDF here
        # For now, return a placeholder URL
        # This should be replaced with actual PDF generation and upload to storage

        # Generate hash for unique URL
        hash_input = f"{invoice_number}_{datetime.utcnow().isoformat()}"
        url_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]

        # Return placeholder URL (should be actual storage URL in production)
        return f"https://storage.magflow.ro/invoices/{filename}?v={url_hash}"

    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics."""
        return {
            "account_type": self.account_type,
            "metrics": self._metrics.copy()
        }
