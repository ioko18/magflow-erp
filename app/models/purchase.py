"""Purchase Management models."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class Supplier(Base, TimestampMixin):
    """Supplier model for purchase management."""

    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tax_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    payment_terms: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=7)  # days
    minimum_order_value: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5 stars

    # Relationships
    purchase_orders: Mapped[List["PurchaseOrder"]] = relationship(
        "PurchaseOrder",
        back_populates="supplier",
    )
    supplier_products: Mapped[List["SupplierProduct"]] = relationship(
        "SupplierProduct",
        back_populates="supplier",
    )

    def __repr__(self) -> str:
        return f"<Supplier {self.name} ({self.code})>"


class SupplierProduct(Base, TimestampMixin):
    """Supplier product model for tracking supplier-specific products."""

    __tablename__ = "supplier_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    supplier_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("suppliers.id"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    supplier_product_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    supplier_product_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    unit_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    minimum_order_quantity: Mapped[int] = mapped_column(Integer, default=1)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=7)
    is_preferred: Mapped[bool] = mapped_column(Boolean(), default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    supplier: Mapped["Supplier"] = relationship(
        "Supplier",
        back_populates="supplier_products",
    )

    def __repr__(self) -> str:
        return (
            f"<SupplierProduct supplier:{self.supplier_id} product:{self.product_id}>"
        )


class PurchaseOrder(Base, TimestampMixin):
    """Purchase order model."""

    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    supplier_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("suppliers.id"),
        nullable=False,
    )
    order_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expected_delivery_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
    )  # draft, sent, confirmed, received, cancelled
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    discount_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    shipping_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="RON")
    payment_terms: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    approved_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    supplier: Mapped["Supplier"] = relationship(
        "Supplier",
        back_populates="purchase_orders",
    )
    order_lines: Mapped[List["PurchaseOrderLine"]] = relationship(
        "PurchaseOrderLine",
        back_populates="purchase_order",
    )
    purchase_receipts: Mapped[List["PurchaseReceipt"]] = relationship(
        "PurchaseReceipt",
        back_populates="purchase_order",
    )

    def __repr__(self) -> str:
        return f"<PurchaseOrder {self.order_number}>"


class PurchaseOrderLine(Base, TimestampMixin):
    """Purchase order line model."""

    __tablename__ = "purchase_order_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    purchase_order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("purchase_orders.id"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    supplier_product_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("supplier_products.id"),
        nullable=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    discount_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    tax_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=19)
    line_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    received_quantity: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    purchase_order: Mapped["PurchaseOrder"] = relationship(
        "PurchaseOrder",
        back_populates="order_lines",
    )
    supplier_product: Mapped[Optional["SupplierProduct"]] = relationship(
        "SupplierProduct",
    )

    def __repr__(self) -> str:
        return f"<PurchaseOrderLine order:{self.purchase_order_id} product:{self.product_id} qty:{self.quantity}>"


class PurchaseReceipt(Base, TimestampMixin):
    """Purchase receipt model."""

    __tablename__ = "purchase_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    receipt_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    purchase_order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("purchase_orders.id"),
        nullable=False,
    )
    receipt_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    supplier_invoice_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    supplier_invoice_date: Mapped[Optional[datetime]] = mapped_column(
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
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    received_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quality_checked_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    purchase_order: Mapped["PurchaseOrder"] = relationship(
        "PurchaseOrder",
        back_populates="purchase_receipts",
    )
    receipt_lines: Mapped[List["PurchaseReceiptLine"]] = relationship(
        "PurchaseReceiptLine",
        back_populates="purchase_receipt",
    )

    def __repr__(self) -> str:
        return f"<PurchaseReceipt {self.receipt_number}>"


class PurchaseReceiptLine(Base, TimestampMixin):
    """Purchase receipt line model."""

    __tablename__ = "purchase_receipt_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    purchase_receipt_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("purchase_receipts.id"),
        nullable=False,
    )
    purchase_order_line_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("purchase_order_lines.id"),
        nullable=False,
    )
    received_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    accepted_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    rejected_quantity: Mapped[int] = mapped_column(Integer, default=0)
    unit_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    line_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    quality_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
    )  # pending, accepted, rejected, partial
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    purchase_receipt: Mapped["PurchaseReceipt"] = relationship(
        "PurchaseReceipt",
        back_populates="receipt_lines",
    )
    purchase_order_line: Mapped["PurchaseOrderLine"] = relationship("PurchaseOrderLine")

    def __repr__(self) -> str:
        return f"<PurchaseReceiptLine receipt:{self.purchase_receipt_id} qty:{self.received_quantity}>"


class SupplierPayment(Base, TimestampMixin):
    """Supplier payment model."""

    __tablename__ = "supplier_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    payment_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    supplier_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("suppliers.id"),
        nullable=False,
    )
    purchase_receipt_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("purchase_receipts.id"),
        nullable=True,
    )
    payment_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # bank_transfer, check, cash, etc.
    reference: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )  # transaction ID, check number
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
    )  # pending, completed, failed
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    requisition_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )
    requested_by: Mapped[int] = mapped_column(Integer, nullable=False)  # user_id
    department: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
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
    justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    requisition_lines: Mapped[List["PurchaseRequisitionLine"]] = relationship(
        "PurchaseRequisitionLine",
        back_populates="purchase_requisition",
    )

    def __repr__(self) -> str:
        return f"<PurchaseRequisition {self.requisition_number}>"


class PurchaseRequisitionLine(Base, TimestampMixin):
    """Purchase requisition line model."""

    __tablename__ = "purchase_requisition_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    purchase_requisition_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("purchase_requisitions.id"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_unit_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    estimated_total_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    supplier_preference: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
        return f"<PurchaseRequisitionLine req:{self.purchase_requisition_id} product:{self.product_id}>"
