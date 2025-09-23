"""Sales Management models."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class Customer(Base, TimestampMixin):
    """Customer model for sales management."""

    __tablename__ = "customers"

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
    credit_limit: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True)

    # Relationships
    sales_orders: Mapped[List["SalesOrder"]] = relationship(
        "SalesOrder",
        back_populates="customer",
    )
    invoices: Mapped[List["Invoice"]] = relationship(
        "Invoice",
        back_populates="customer",
    )

    def __repr__(self) -> str:
        return f"<Customer {self.name} ({self.code})>"


class SalesOrder(Base, TimestampMixin):
    """Sales order model."""

    __tablename__ = "sales_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("customers.id"),
        nullable=False,
    )
    order_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    delivery_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
    )  # draft, confirmed, processing, shipped, delivered, cancelled
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    discount_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    shipping_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="RON")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    approved_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="sales_orders",
    )
    order_lines: Mapped[List["SalesOrderLine"]] = relationship(
        "SalesOrderLine",
        back_populates="sales_order",
    )
    invoices: Mapped[List["Invoice"]] = relationship(
        "Invoice",
        back_populates="sales_order",
    )

    def __repr__(self) -> str:
        return f"<SalesOrder {self.order_number}>"


class SalesOrderLine(Base, TimestampMixin):
    """Sales order line model."""

    __tablename__ = "sales_order_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sales_order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sales_orders.id"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    discount_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    tax_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=19)
    line_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    sales_order: Mapped["SalesOrder"] = relationship(
        "SalesOrder",
        back_populates="order_lines",
    )

    def __repr__(self) -> str:
        return f"<SalesOrderLine order:{self.sales_order_id} product:{self.product_id} qty:{self.quantity}>"


class Invoice(Base, TimestampMixin):
    """Invoice model."""

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("customers.id"),
        nullable=False,
    )
    sales_order_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("sales_orders.id"),
        nullable=True,
    )
    invoice_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
    )  # draft, sent, paid, overdue, cancelled
    subtotal_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    discount_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RON")
    payment_terms: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="invoices")
    sales_order: Mapped[Optional["SalesOrder"]] = relationship(
        "SalesOrder",
        back_populates="invoices",
    )
    invoice_lines: Mapped[List["InvoiceLine"]] = relationship(
        "InvoiceLine",
        back_populates="invoice",
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment",
        back_populates="invoice",
    )

    def __repr__(self) -> str:
        return f"<Invoice {self.invoice_number}>"


class InvoiceLine(Base, TimestampMixin):
    """Invoice line model."""

    __tablename__ = "invoice_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("invoices.id"),
        nullable=False,
    )
    sales_order_line_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("sales_order_lines.id"),
        nullable=True,
    )
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    discount_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    tax_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=19)
    line_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # Relationships
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="invoice_lines")
    sales_order_line: Mapped[Optional["SalesOrderLine"]] = relationship(
        "SalesOrderLine",
    )

    def __repr__(self) -> str:
        return f"<InvoiceLine invoice:{self.invoice_id} product:{self.product_id}>"


class Payment(Base, TimestampMixin):
    """Payment model."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    payment_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    invoice_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("invoices.id"),
        nullable=False,
    )
    payment_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # cash, bank_transfer, card, etc.
    reference: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )  # check number, transaction ID
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
    )  # pending, completed, failed, refunded
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment {self.payment_number} amount:{self.amount}>"


class SalesQuote(Base, TimestampMixin):
    """Sales quote model."""

    __tablename__ = "sales_quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    quote_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("customers.id"),
        nullable=False,
    )
    valid_until: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
    )  # draft, sent, accepted, rejected, expired
    subtotal_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    discount_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RON")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer")
    quote_lines: Mapped[List["SalesQuoteLine"]] = relationship(
        "SalesQuoteLine",
        back_populates="sales_quote",
    )

    def __repr__(self) -> str:
        return f"<SalesQuote {self.quote_number}>"


class SalesQuoteLine(Base, TimestampMixin):
    """Sales quote line model."""

    __tablename__ = "sales_quote_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sales_quote_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sales_quotes.id"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    discount_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    tax_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=19)
    line_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # Relationships
    sales_quote: Mapped["SalesQuote"] = relationship(
        "SalesQuote",
        back_populates="quote_lines",
    )

    def __repr__(self) -> str:
        return f"<SalesQuoteLine quote:{self.sales_quote_id} product:{self.product_id}>"
