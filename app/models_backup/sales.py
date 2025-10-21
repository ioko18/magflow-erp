"""Sales Management models."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class Customer(Base, TimestampMixin):
    """Customer model for sales management."""

    __tablename__ = "customers"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(50), nullable=True)
    country: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(String(100), nullable=True)
    credit_limit: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True)

    # Relationships
    sales_orders: Mapped[list["SalesOrder"]] = relationship(
        "SalesOrder",
        back_populates="customer",
    )

    def __repr__(self) -> str:
        return f"<Customer {self.name} ({self.code})>"


class SalesOrder(Base, TimestampMixin):
    """Sales order model."""

    __tablename__ = "sales_orders"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.customers.id"),
        nullable=False,
    )
    order_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    delivery_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
    )  # draft, confirmed, processing, shipped, delivered, cancelled
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    discount_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    shipping_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="RON")
    fulfillment_channel: Mapped[str] = mapped_column(String(20), default="main")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="sales_orders",
    )
    order_lines: Mapped[list["SalesOrderLine"]] = relationship(
        "SalesOrderLine",
        back_populates="sales_order",
    )

    def __repr__(self) -> str:
        return f"<SalesOrder {self.order_number}>"


class SalesOrderLine(Base, TimestampMixin):
    """Sales order line model."""

    __tablename__ = "sales_order_lines"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sales_order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.sales_orders.id"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    discount_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    tax_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=19)
    line_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    sales_order: Mapped["SalesOrder"] = relationship(
        "SalesOrder",
        back_populates="order_lines",
    )

    def __repr__(self) -> str:
        return (
            f"<SalesOrderLine order:{self.sales_order_id} product:{self.product_id} "
            f"qty:{self.quantity}>"
        )


class SalesQuote(Base, TimestampMixin):
    """Sales quote model."""

    __tablename__ = "sales_quotes"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    quote_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.customers.id"),
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
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer")
    quote_lines: Mapped[list["SalesQuoteLine"]] = relationship(
        "SalesQuoteLine",
        back_populates="sales_quote",
    )

    def __repr__(self) -> str:
        return f"<SalesQuote {self.quote_number}>"


class SalesQuoteLine(Base, TimestampMixin):
    """Sales quote line model."""

    __tablename__ = "sales_quote_lines"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sales_quote_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.sales_quotes.id"),
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
