"""Purchase Management models.

Note: This module uses the Supplier model from app.models.supplier
to avoid duplicate model definitions.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.supplier import Supplier


class SupplierProductPurchase(Base, TimestampMixin):
    """Supplier product model for tracking supplier-specific products in purchase orders.

    Note: This is different from SupplierProduct in supplier.py which is used for
    1688.com product matching. This model is specifically for purchase order management.
    """

    __tablename__ = "supplier_products_purchase"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    supplier_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.suppliers.id"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    supplier_product_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    supplier_product_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    unit_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    minimum_order_quantity: Mapped[int] = mapped_column(Integer, default=1)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=7)
    is_preferred: Mapped[bool] = mapped_column(Boolean(), default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    supplier: Mapped["Supplier"] = relationship(
        "Supplier",
        foreign_keys=[supplier_id],
    )

    def __repr__(self) -> str:
        return f"<SupplierProductPurchase supplier:{self.supplier_id} product:{self.product_id}>"


class PurchaseOrder(Base, TimestampMixin):
    """Purchase order model."""

    __tablename__ = "purchase_orders"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    supplier_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.suppliers.id"),
        nullable=False,
    )
    order_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expected_delivery_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        index=True,
    )  # draft, sent, confirmed, partially_received, received, cancelled
    # Financial fields - adapted to existing schema
    total_value: Mapped[float] = mapped_column(Float, nullable=False)  # existing field
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RON")
    exchange_rate: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )  # existing field

    # Existing fields from old schema
    order_items: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # existing field
    supplier_confirmation: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )  # existing
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # existing
    attachments: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # existing
    quality_check_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # existing
    quality_notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # existing

    # Enhanced tracking fields
    delivery_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    actual_delivery_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    supplier: Mapped["Supplier"] = relationship(
        "Supplier",
        back_populates="purchase_orders",
    )
    order_items_rel: Mapped[list["PurchaseOrderItem"]] = relationship(
        "PurchaseOrderItem",
        back_populates="purchase_order",
        foreign_keys="[PurchaseOrderItem.purchase_order_id]",
    )
    purchase_receipts: Mapped[list["PurchaseReceipt"]] = relationship(
        "PurchaseReceipt",
        back_populates="purchase_order",
    )
    unreceived_items: Mapped[list["PurchaseOrderUnreceivedItem"]] = relationship(
        "PurchaseOrderUnreceivedItem",
        back_populates="purchase_order",
        cascade="all, delete-orphan",
    )
    history: Mapped[list["PurchaseOrderHistory"]] = relationship(
        "PurchaseOrderHistory",
        back_populates="purchase_order",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<PurchaseOrder {self.order_number}>"

    @property
    def total_ordered_quantity(self) -> int:
        """Calculate total quantity ordered across all items."""
        return sum(item.quantity_ordered for item in self.order_items_rel)

    @property
    def total_received_quantity(self) -> int:
        """Calculate total quantity received across all items."""
        return sum(item.quantity_received or 0 for item in self.order_items_rel)

    @property
    def is_fully_received(self) -> bool:
        """Check if all items have been received."""
        return all(
            (item.quantity_received or 0) >= item.quantity_ordered
            for item in self.order_items_rel
        )

    @property
    def is_partially_received(self) -> bool:
        """Check if some items have been received."""
        return (
            any((item.quantity_received or 0) > 0 for item in self.order_items_rel)
            and not self.is_fully_received
        )

    # Compatibility properties for API
    @property
    def total_amount(self) -> float:
        """Alias for total_value for API compatibility."""
        return self.total_value

    @property
    def order_lines(self) -> list["PurchaseOrderItem"]:
        """Alias for order_items_rel for API compatibility."""
        return self.order_items_rel


class PurchaseOrderItem(Base, TimestampMixin):
    """Purchase order item model - adapted to existing DB schema."""

    __tablename__ = "purchase_order_items"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    purchase_order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.purchase_orders.id"),
        nullable=False,
        index=True,
    )
    supplier_product_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("app.supplier_products.id"),
        nullable=True,
        index=True,
    )
    local_product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.products.id"),
        nullable=False,
        index=True,
    )

    # Quantities - using existing DB column names
    quantity_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_received: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)

    # Prices - using existing DB column names
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)

    # Dates
    expected_delivery_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_delivery_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Quality
    quality_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quality_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    purchase_order: Mapped["PurchaseOrder"] = relationship(
        "PurchaseOrder",
        back_populates="order_items_rel",
    )

    def __repr__(self) -> str:
        return (
            f"<PurchaseOrderItem order:{self.purchase_order_id} "
            f"product:{self.local_product_id} qty:{self.quantity_ordered}>"
        )

    # Compatibility properties for API
    @property
    def product_id(self) -> int:
        """Alias for local_product_id."""
        return self.local_product_id

    @property
    def quantity(self) -> int:
        """Alias for quantity_ordered."""
        return self.quantity_ordered

    @property
    def received_quantity(self) -> int:
        """Alias for quantity_received."""
        return self.quantity_received or 0

    @property
    def unit_cost(self) -> float:
        """Alias for unit_price."""
        return self.unit_price

    @property
    def line_total(self) -> float:
        """Alias for total_price."""
        return self.total_price


# Legacy PurchaseOrderLine class - DISABLED to avoid conflicts
# The table purchase_order_lines exists in DB but is not used by the new system
# Use PurchaseOrderItem instead which maps to the existing purchase_order_items table

# NOTE: This class is commented out to prevent SQLAlchemy mapper conflicts
# If you need to access the purchase_order_lines table, create a new model without relationships

# class PurchaseOrderLine(Base, TimestampMixin):
#     """Purchase order line model - DEPRECATED, use PurchaseOrderItem instead."""
#     __tablename__ = "purchase_order_lines"
#     __table_args__ = {"schema": "app", "extend_existing": True}
#     # ... (fields omitted)


class PurchaseReceipt(Base, TimestampMixin):
    """Purchase receipt model."""

    __tablename__ = "purchase_receipts"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    receipt_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    purchase_order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.purchase_orders.id"),
        nullable=False,
    )
    receipt_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    supplier_invoice_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    supplier_invoice_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
    )  # draft, received, quality_check, completed
    total_received_quantity: Mapped[int] = mapped_column(Integer, default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RON")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quality_checked_by: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    purchase_order: Mapped["PurchaseOrder"] = relationship(
        "PurchaseOrder",
        back_populates="purchase_receipts",
    )
    # receipt_lines: Mapped[list["PurchaseReceiptLine"]] = relationship(
    #     "PurchaseReceiptLine",
    #     back_populates="purchase_receipt",
    # )  # DISABLED - PurchaseReceiptLine is commented out

    def __repr__(self) -> str:
        return f"<PurchaseReceipt {self.receipt_number}>"


# NOTE: This class is commented out to prevent SQLAlchemy mapper conflicts
# The purchase_order_lines table is deprecated, so we can't create foreign keys to it
# If you need to access the purchase_receipt_lines table, create a new model without
# the FK to purchase_order_lines

# class PurchaseReceiptLine(Base, TimestampMixin):
#     """Purchase receipt line model."""
#
#     __tablename__ = "purchase_receipt_lines"
#     __table_args__ = {"schema": "app", "extend_existing": True}
#
#     id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
#     purchase_receipt_id: Mapped[int] = mapped_column(
#         Integer,
#         ForeignKey("app.purchase_receipts.id"),
#         nullable=False,
#     )
#     purchase_order_line_id: Mapped[int] = mapped_column(
#         Integer,
#         ForeignKey("app.purchase_order_lines.id"),
#         nullable=False,
#     )
#     received_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
#     accepted_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
#     rejected_quantity: Mapped[int] = mapped_column(Integer, default=0)
#     unit_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
#     line_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
#     quality_status: Mapped[str] = mapped_column(
#         String(20),
#         default="pending",
#     )  # pending, accepted, rejected, partial
#     rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
#     notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
#
#     # Relationships
#     purchase_receipt: Mapped["PurchaseReceipt"] = relationship(
#         "PurchaseReceipt",
#         back_populates="receipt_lines",
#     )
#     # purchase_order_line: Mapped["PurchaseOrderLine"] = relationship(
#     #     "PurchaseOrderLine"
#     # )  # DISABLED
#
#     def __repr__(self) -> str:
#         return (
#             f"<PurchaseReceiptLine receipt:{self.purchase_receipt_id} "
#             f"qty:{self.received_quantity}>"
#         )


class SupplierPayment(Base, TimestampMixin):
    """Supplier payment model."""

    __tablename__ = "supplier_payments"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    payment_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    supplier_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.suppliers.id"),
        nullable=False,
    )
    purchase_receipt_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("app.purchase_receipts.id"),
        nullable=True,
    )
    payment_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # bank_transfer, check, cash, etc.
    reference: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )  # transaction ID, check number
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
    )  # pending, completed, failed
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    supplier: Mapped["Supplier"] = relationship("Supplier")
    purchase_receipt: Mapped[Optional["PurchaseReceipt"]] = relationship(
        "PurchaseReceipt",
    )

    def __repr__(self) -> str:
        return f"<SupplierPayment {self.payment_number} amount:{self.amount}>"


class PurchaseRequisition(Base, TimestampMixin):
    """Purchase requisition model for internal requests."""

    __tablename__ = "purchase_requisitions"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    requisition_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )
    requested_by: Mapped[int] = mapped_column(Integer, nullable=False)  # user_id
    department: Mapped[str | None] = mapped_column(String(50), nullable=True)
    required_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
    )  # draft, submitted, approved, rejected, completed
    priority: Mapped[str] = mapped_column(
        String(20),
        default="normal",
    )  # low, normal, high, urgent
    total_estimated_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RON")
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    requisition_lines: Mapped[list["PurchaseRequisitionLine"]] = relationship(
        "PurchaseRequisitionLine",
        back_populates="purchase_requisition",
    )

    def __repr__(self) -> str:
        return f"<PurchaseRequisition {self.requisition_number}>"


class PurchaseRequisitionLine(Base, TimestampMixin):
    """Purchase requisition line model."""

    __tablename__ = "purchase_requisition_lines"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    purchase_requisition_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.purchase_requisitions.id"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_unit_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    estimated_total_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    supplier_preference: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
    )  # pending, ordered, received, cancelled

    # Relationships
    purchase_requisition: Mapped["PurchaseRequisition"] = relationship(
        "PurchaseRequisition",
        back_populates="requisition_lines",
    )

    def __repr__(self) -> str:
        return (
            f"<PurchaseRequisitionLine req:{self.purchase_requisition_id} "
            f"product:{self.product_id}>"
        )


class PurchaseOrderUnreceivedItem(Base, TimestampMixin):
    """Track unreceived items from purchase orders."""

    __tablename__ = "purchase_order_unreceived_items"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    purchase_order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    purchase_order_item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.purchase_order_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ordered_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    received_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unreceived_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    follow_up_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
    )  # pending, partial, resolved, cancelled
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    purchase_order: Mapped["PurchaseOrder"] = relationship(
        "PurchaseOrder",
        back_populates="unreceived_items",
    )
    purchase_order_item: Mapped["PurchaseOrderItem"] = relationship(
        "PurchaseOrderItem",
    )

    def __repr__(self) -> str:
        return (
            f"<PurchaseOrderUnreceivedItem PO:{self.purchase_order_id} "
            f"Product:{self.product_id} Qty:{self.unreceived_quantity}>"
        )


class PurchaseOrderHistory(Base):
    """Audit trail for purchase order changes."""

    __tablename__ = "purchase_order_history"
    __table_args__ = {"schema": "app", "extend_existing": True}

    # Exclude created_at and updated_at from Base class (table doesn't have these columns)
    created_at = None  # type: ignore
    updated_at = None  # type: ignore

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    purchase_order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # created, sent, confirmed, received, cancelled, etc.
    old_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    purchase_order: Mapped["PurchaseOrder"] = relationship(
        "PurchaseOrder",
        back_populates="history",
    )

    def __repr__(self) -> str:
        return f"<PurchaseOrderHistory PO:{self.purchase_order_id} Action:{self.action}>"
