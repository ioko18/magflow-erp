"""Invoice Management models for MagFlow ERP."""

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class InvoiceStatus(str, enum.Enum):
    """Status of an invoice."""

    DRAFT = "draft"
    ISSUED = "issued"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class InvoiceType(str, enum.Enum):
    """Type of invoice."""

    SALES_INVOICE = "sales_invoice"
    CREDIT_NOTE = "credit_note"
    PROFORMA_INVOICE = "proforma_invoice"
    CORRECTED_INVOICE = "corrected_invoice"


class PaymentMethod(str, enum.Enum):
    """Payment method used."""

    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    CARD = "card"
    ONLINE_PAYMENT = "online_payment"
    CHECK = "check"
    OTHER = "other"


class TaxCategory(str, enum.Enum):
    """Tax categories for VAT calculation."""

    STANDARD = "standard"  # 19%
    REDUCED = "reduced"  # 9%
    SUPER_REDUCED = "super_reduced"  # 5%
    ZERO = "zero"  # 0%
    EXEMPT = "exempt"  # Exempt from VAT


class Invoice(Base, TimestampMixin):
    """Invoice model for managing customer invoices."""

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    # Related entities
    order_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    customer_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Invoice details
    invoice_type: Mapped[InvoiceType] = mapped_column(
        SQLEnum(InvoiceType),
        nullable=False,
        default=InvoiceType.SALES_INVOICE,
    )
    status: Mapped[InvoiceStatus] = mapped_column(
        SQLEnum(InvoiceStatus),
        default=InvoiceStatus.DRAFT,
    )

    # Dates
    invoice_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Customer information
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    customer_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    customer_tax_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Company information
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    company_tax_id: Mapped[str] = mapped_column(String(50), nullable=False)
    company_registration: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    # Financial information
    subtotal: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="RON")

    # Payment information
    payment_method: Mapped[Optional[PaymentMethod]] = mapped_column(
        SQLEnum(PaymentMethod),
        nullable=True,
    )
    payment_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    paid_amount: Mapped[float] = mapped_column(Float, default=0.0)

    # eMAG integration
    emag_invoice_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    account_type: Mapped[str] = mapped_column(String(10), default="main")  # main/fbe

    # Processing information
    issued_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # user_id
    issued_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sent_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # user_id
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Additional information
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # PDF and attachments
    pdf_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    pdf_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    pdf_generated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    # Relationships
    invoice_items: Mapped[List["InvoiceItem"]] = relationship(
        "InvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )
    payments: Mapped[List["InvoicePayment"]] = relationship(
        "InvoicePayment",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Invoice {self.invoice_number}: {self.total_amount} {self.currency}>"


class InvoiceItem(Base, TimestampMixin):
    """Individual items within an invoice."""

    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("invoices.id"),
        nullable=False,
    )

    # Item details
    product_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Quantity and pricing
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    discount_amount: Mapped[float] = mapped_column(Float, default=0.0)
    line_total: Mapped[float] = mapped_column(Float, nullable=False)

    # Tax information
    tax_category: Mapped[TaxCategory] = mapped_column(
        SQLEnum(TaxCategory),
        nullable=False,
    )
    tax_rate: Mapped[float] = mapped_column(Float, nullable=False)  # e.g., 19.0 for 19%
    tax_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # eMAG integration
    emag_item_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="invoice_items")

    def __repr__(self) -> str:
        return f"<InvoiceItem {self.sku}: {self.quantity} x {self.unit_price}>"


class InvoicePayment(Base, TimestampMixin):
    """Payment records for invoices."""

    __tablename__ = "invoice_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    payment_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    # Related entities
    invoice_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("invoices.id"),
        nullable=False,
    )
    order_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Payment details
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RON")
    payment_method: Mapped[PaymentMethod] = mapped_column(
        SQLEnum(PaymentMethod),
        nullable=False,
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )  # pending, processing, completed, failed
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Payment gateway information
    gateway_transaction_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    gateway_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Additional information
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="payments")

    def __repr__(self) -> str:
        return f"<InvoicePayment {self.payment_id}: {self.amount} {self.currency}>"


class EmagInvoiceIntegration(Base, TimestampMixin):
    """Tracks integration with eMAG invoice system."""

    __tablename__ = "emag_invoice_integrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("invoices.id"),
        nullable=False,
    )

    # eMAG invoice details
    emag_invoice_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    emag_status: Mapped[str] = mapped_column(String(50), nullable=False)

    # Invoice type in eMAG
    emag_invoice_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # invoice, credit_note, etc.

    # Sync information
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sync_attempts: Mapped[int] = mapped_column(Integer, default=0)

    # eMAG response data
    emag_response: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )  # JSON response from eMAG
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Account type
    account_type: Mapped[str] = mapped_column(String(10), default="main")  # main/fbe

    def __repr__(self) -> str:
        return f"<EmagInvoiceIntegration {self.emag_invoice_id}: {self.emag_status}>"


class TaxCalculation(Base, TimestampMixin):
    """Tracks tax calculations for invoices."""

    __tablename__ = "tax_calculations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("invoices.id"),
        nullable=False,
    )

    # Tax details
    tax_category: Mapped[TaxCategory] = mapped_column(
        SQLEnum(TaxCategory),
        nullable=False,
    )
    tax_rate: Mapped[float] = mapped_column(Float, nullable=False)  # e.g., 19.0
    base_amount: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )  # Amount before tax
    tax_amount: Mapped[float] = mapped_column(Float, nullable=False)  # Calculated tax

    # Item breakdown
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    item_ids: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )  # JSON array of item IDs

    def __repr__(self) -> str:
        return f"<TaxCalculation {self.tax_category}: {self.tax_amount} ({self.tax_rate}%)>"
