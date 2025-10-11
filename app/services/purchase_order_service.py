"""Purchase Order Service for managing purchase orders and tracking."""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.purchase import (
    PurchaseOrder,
    PurchaseOrderHistory,
    PurchaseOrderItem,  # Using PurchaseOrderItem instead of PurchaseOrderLine
    PurchaseOrderUnreceivedItem,
    PurchaseReceipt,
)
from app.models.supplier import Supplier

logger = logging.getLogger(__name__)


class PurchaseOrderService:
    """Service for managing purchase orders."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_purchase_order(
        self, order_data: dict[str, Any], user_id: int
    ) -> PurchaseOrder:
        """Create a new purchase order.

        Args:
            order_data: Dictionary containing order information
            user_id: ID of the user creating the order

        Returns:
            Created PurchaseOrder instance
        """
        # Generate order number
        order_number = await self._generate_order_number()

        # Create purchase order
        po = PurchaseOrder(
            order_number=order_number,
            supplier_id=order_data["supplier_id"],
            order_date=order_data.get("order_date", datetime.now(UTC).replace(tzinfo=None)),
            expected_delivery_date=order_data.get("expected_delivery_date"),
            status="draft",
            total_value=0,  # Will be calculated from order items
            currency=order_data.get("currency", "RON"),
            exchange_rate=order_data.get("exchange_rate", 1.0),
            internal_notes=order_data.get("notes"),
            delivery_address=order_data.get("delivery_address"),
        )

        self.db.add(po)
        await self.db.flush()  # Get the ID

        # Add order items (using PurchaseOrderItem model)
        total_value = 0
        for line_data in order_data.get("lines", []):
            item_total = line_data["quantity"] * line_data["unit_cost"]
            item = PurchaseOrderItem(
                purchase_order_id=po.id,
                local_product_id=line_data["product_id"],
                supplier_product_id=line_data.get("supplier_product_id"),
                quantity_ordered=line_data["quantity"],
                quantity_received=0,
                unit_price=line_data["unit_cost"],
                total_price=item_total,
                quality_status="pending",  # Default status for new items
                # Note: discount_percent and tax_percent not in DB, calculated separately
            )
            self.db.add(item)
            total_value += item_total

        po.total_value = total_value

        # Add history entry
        await self._add_history(
            po.id, "created", None, "draft", "Purchase order created", user_id
        )

        await self.db.flush()
        return po

    async def update_purchase_order_status(
        self,
        po_id: int,
        new_status: str,
        user_id: int,
        notes: str | None = None,
        metadata: dict | None = None,
    ) -> PurchaseOrder:
        """Update purchase order status.

        Args:
            po_id: Purchase order ID
            new_status: New status value
            user_id: ID of user making the change
            notes: Optional notes about the status change
            metadata: Optional metadata dictionary

        Returns:
            Updated PurchaseOrder instance
        """
        query = select(PurchaseOrder).where(PurchaseOrder.id == po_id)
        result = await self.db.execute(query)
        po = result.scalar_one_or_none()

        if not po:
            raise ValueError(f"Purchase order {po_id} not found")

        old_status = po.status
        po.status = new_status

        # Update specific fields based on status
        if new_status == "cancelled":
            po.cancelled_at = datetime.now(UTC)
            po.cancelled_by = user_id
            if notes:
                po.cancellation_reason = notes

        elif new_status == "received":
            po.actual_delivery_date = datetime.now(UTC)

        # Add history entry
        await self._add_history(
            po_id, f"status_changed_to_{new_status}", old_status, new_status, notes, user_id, extra_data=metadata
        )

        await self.db.flush()
        return po

    async def receive_purchase_order(
        self,
        po_id: int,
        receipt_data: dict[str, Any],
        user_id: int,
    ) -> PurchaseReceipt:
        """Record receipt of purchase order items.

        Args:
            po_id: Purchase order ID
            receipt_data: Receipt information including received quantities
            user_id: ID of user recording the receipt

        Returns:
            Created PurchaseReceipt instance
        """
        # Get purchase order with lines
        query = (
            select(PurchaseOrder)
            .options(selectinload(PurchaseOrder.order_lines))
            .where(PurchaseOrder.id == po_id)
        )
        result = await self.db.execute(query)
        po = result.scalar_one_or_none()

        if not po:
            raise ValueError(f"Purchase order {po_id} not found")

        # Generate receipt number
        receipt_number = await self._generate_receipt_number()

        # Create receipt
        receipt = PurchaseReceipt(
            receipt_number=receipt_number,
            purchase_order_id=po_id,
            receipt_date=receipt_data.get("receipt_date", datetime.now(UTC)),
            supplier_invoice_number=receipt_data.get("supplier_invoice_number"),
            supplier_invoice_date=receipt_data.get("supplier_invoice_date"),
            status="received",
            total_received_quantity=0,
            total_amount=0,
            currency=po.currency,
            notes=receipt_data.get("notes"),
            received_by=user_id,
        )

        self.db.add(receipt)
        await self.db.flush()

        # Process received items
        total_received = 0
        for line_data in receipt_data.get("lines", []):
            po_line_id = line_data["purchase_order_line_id"]
            received_qty = line_data["received_quantity"]

            # Get the PO line
            po_line = next((line for line in po.order_lines if line.id == po_line_id), None)
            if not po_line:
                continue

            # Update received quantity on PO line
            po_line.received_quantity += received_qty
            total_received += received_qty

            # Check for unreceived items
            unreceived_qty = po_line.quantity - po_line.received_quantity
            if unreceived_qty > 0:
                await self._track_unreceived_item(
                    po_id, po_line_id, po_line.product_id, po_line.quantity,
                    po_line.received_quantity, unreceived_qty
                )

        receipt.total_received_quantity = total_received

        # Update PO status based on receipt
        if po.is_fully_received:
            await self.update_purchase_order_status(
                po_id, "received", user_id, "All items received"
            )
        elif po.is_partially_received:
            await self.update_purchase_order_status(
                po_id, "partially_received", user_id, "Partial receipt recorded"
            )

        await self.db.flush()
        return receipt

    async def get_pending_orders_for_product(
        self, product_id: int
    ) -> list[dict[str, Any]]:
        """Get all pending purchase orders for a specific product.

        Args:
            product_id: Product ID to check

        Returns:
            List of pending order information
        """
        query = (
            select(PurchaseOrder, PurchaseOrderItem, Supplier)
            .join(PurchaseOrderItem, PurchaseOrder.id == PurchaseOrderItem.purchase_order_id)
            .join(Supplier, PurchaseOrder.supplier_id == Supplier.id)
            .where(
                and_(
                    PurchaseOrderItem.local_product_id == product_id,
                    PurchaseOrder.status.in_(["sent", "confirmed", "partially_received"]),
                    (PurchaseOrderItem.quantity_received or 0) < PurchaseOrderItem.quantity_ordered,
                )
            )
        )

        result = await self.db.execute(query)
        orders = result.all()

        pending_orders = []
        for po, item, supplier in orders:
            pending_qty = item.quantity_ordered - (item.quantity_received or 0)
            pending_orders.append({
                "purchase_order_id": po.id,
                "order_number": po.order_number,
                "supplier_id": supplier.id,
                "supplier_name": supplier.name,
                "ordered_quantity": item.quantity_ordered,
                "received_quantity": item.quantity_received or 0,
                "pending_quantity": pending_qty,
                "expected_delivery_date": po.expected_delivery_date.isoformat()
                if po.expected_delivery_date
                else None,
                "order_date": po.order_date.isoformat() if po.order_date else None,
                "status": po.status,
            })

        return pending_orders

    async def get_unreceived_items(
        self, status: str | None = None, supplier_id: int | None = None
    ) -> list[PurchaseOrderUnreceivedItem]:
        """Get unreceived items with optional filters.

        Args:
            status: Filter by status (pending, partial, resolved, cancelled)
            supplier_id: Filter by supplier

        Returns:
            List of unreceived items
        """
        query = (
            select(PurchaseOrderUnreceivedItem)
            .join(PurchaseOrder, PurchaseOrderUnreceivedItem.purchase_order_id == PurchaseOrder.id)
            .options(
                selectinload(PurchaseOrderUnreceivedItem.purchase_order),
                selectinload(PurchaseOrderUnreceivedItem.purchase_order_line),
            )
        )

        if status:
            query = query.where(PurchaseOrderUnreceivedItem.status == status)

        if supplier_id:
            query = query.where(PurchaseOrder.supplier_id == supplier_id)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def resolve_unreceived_item(
        self,
        unreceived_item_id: int,
        resolution_notes: str,
        user_id: int,
    ) -> PurchaseOrderUnreceivedItem:
        """Mark an unreceived item as resolved.

        Args:
            unreceived_item_id: ID of the unreceived item
            resolution_notes: Notes about the resolution
            user_id: ID of user resolving the item

        Returns:
            Updated unreceived item
        """
        query = select(PurchaseOrderUnreceivedItem).where(
            PurchaseOrderUnreceivedItem.id == unreceived_item_id
        )
        result = await self.db.execute(query)
        item = result.scalar_one_or_none()

        if not item:
            raise ValueError(f"Unreceived item {unreceived_item_id} not found")

        item.status = "resolved"
        item.resolution_notes = resolution_notes
        item.resolved_at = datetime.now(UTC)
        item.resolved_by = user_id

        await self.db.flush()
        return item

    async def get_purchase_order_history(
        self, po_id: int
    ) -> list[PurchaseOrderHistory]:
        """Get complete history for a purchase order.

        Args:
            po_id: Purchase order ID

        Returns:
            List of history entries
        """
        query = (
            select(PurchaseOrderHistory)
            .where(PurchaseOrderHistory.purchase_order_id == po_id)
            .order_by(PurchaseOrderHistory.changed_at.desc())
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_supplier_order_statistics(
        self, supplier_id: int
    ) -> dict[str, Any]:
        """Get order statistics for a supplier.

        Args:
            supplier_id: Supplier ID

        Returns:
            Dictionary with statistics
        """
        # Total orders
        total_query = select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.supplier_id == supplier_id
        )
        total_result = await self.db.execute(total_query)
        total_orders = total_result.scalar() or 0

        # Orders by status
        status_query = (
            select(PurchaseOrder.status, func.count(PurchaseOrder.id))
            .where(PurchaseOrder.supplier_id == supplier_id)
            .group_by(PurchaseOrder.status)
        )
        status_result = await self.db.execute(status_query)
        orders_by_status = dict(status_result.all())

        # Total amount
        amount_query = select(func.sum(PurchaseOrder.total_amount)).where(
            and_(
                PurchaseOrder.supplier_id == supplier_id,
                PurchaseOrder.status != "cancelled",
            )
        )
        amount_result = await self.db.execute(amount_query)
        total_amount = amount_result.scalar() or 0

        return {
            "total_orders": total_orders,
            "orders_by_status": orders_by_status,
            "total_amount": float(total_amount),
            "active_orders": orders_by_status.get("sent", 0)
            + orders_by_status.get("confirmed", 0)
            + orders_by_status.get("partially_received", 0),
        }

    # Private helper methods

    async def _generate_order_number(self) -> str:
        """Generate unique purchase order number."""
        # Get count of orders today
        today = datetime.now(UTC).date()
        query = select(func.count(PurchaseOrder.id)).where(
            func.date(PurchaseOrder.order_date) == today
        )
        result = await self.db.execute(query)
        count = result.scalar() or 0

        return f"PO-{today.strftime('%Y%m%d')}-{count + 1:04d}"

    async def _generate_receipt_number(self) -> str:
        """Generate unique receipt number."""
        today = datetime.now(UTC).date()
        query = select(func.count(PurchaseReceipt.id)).where(
            func.date(PurchaseReceipt.receipt_date) == today
        )
        result = await self.db.execute(query)
        count = result.scalar() or 0

        return f"RCP-{today.strftime('%Y%m%d')}-{count + 1:04d}"

    async def _add_history(
        self,
        po_id: int,
        action: str,
        old_status: str | None,
        new_status: str | None,
        notes: str | None,
        user_id: int,
        extra_data: dict | None = None,
    ) -> None:
        """Add history entry for purchase order."""
        history = PurchaseOrderHistory(
            purchase_order_id=po_id,
            action=action,
            old_status=old_status,
            new_status=new_status,
            notes=notes,
            changed_by=user_id,
            changed_at=datetime.now(UTC).replace(tzinfo=None),
            extra_data=extra_data,
        )
        self.db.add(history)

    async def _track_unreceived_item(
        self,
        po_id: int,
        po_line_id: int,
        product_id: int,
        ordered_qty: int,
        received_qty: int,
        unreceived_qty: int,
    ) -> None:
        """Track unreceived items."""
        # Check if already tracked
        query = select(PurchaseOrderUnreceivedItem).where(
            and_(
                PurchaseOrderUnreceivedItem.purchase_order_id == po_id,
                PurchaseOrderUnreceivedItem.purchase_order_line_id == po_line_id,
            )
        )
        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing record
            existing.received_quantity = received_qty
            existing.unreceived_quantity = unreceived_qty
            existing.status = "partial" if received_qty > 0 else "pending"
        else:
            # Create new record
            unreceived = PurchaseOrderUnreceivedItem(
                purchase_order_id=po_id,
                purchase_order_line_id=po_line_id,
                product_id=product_id,
                ordered_quantity=ordered_qty,
                received_quantity=received_qty,
                unreceived_quantity=unreceived_qty,
                status="partial" if received_qty > 0 else "pending",
            )
            self.db.add(unreceived)
