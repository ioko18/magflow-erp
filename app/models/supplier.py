"""Supplier management models for MagFlow ERP.

This module contains all database models for supplier management including:
- Supplier profiles and information
- Supplier-product mappings for 1688.com integration
- Supplier performance tracking
- Purchase orders and order management
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Table
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.product import Product

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class Supplier(Base, TimestampMixin):
    """Main supplier model for managing supplier information and relationships.

    This model stores comprehensive information about each supplier including:
    - Basic contact and company information
    - Commercial terms (lead time, payment terms, minimum orders)
    - Performance metrics and ratings
    - Specialization and product categories
    """

    __tablename__ = "suppliers"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Basic Information
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(100), default="China", index=True)
    contact_person: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    website: Mapped[Optional[str]] = mapped_column(String(500))

    # Commercial Terms
    lead_time_days: Mapped[int] = mapped_column(Integer, default=30)
    min_order_value: Mapped[float] = mapped_column(Float, default=0.0)
    min_order_qty: Mapped[int] = mapped_column(Integer, default=1)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    payment_terms: Mapped[str] = mapped_column(String(255), default="30 days")

    # Specializations and Products
    specializations: Mapped[Optional[dict]] = mapped_column(JSON)  # Detailed categories
    product_categories: Mapped[Optional[List[str]]] = mapped_column(JSON)  # Simple list

    # Performance Metrics
    rating: Mapped[float] = mapped_column(Float, default=5.0)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    on_time_delivery_rate: Mapped[float] = mapped_column(Float, default=0.0)
    quality_score: Mapped[float] = mapped_column(Float, default=5.0)

    # Status and Notes
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON)

    # Relationships
    products: Mapped[List["SupplierProduct"]] = relationship(
        "SupplierProduct",
        back_populates="supplier",
        cascade="all, delete-orphan"
    )

    performance_records: Mapped[List["SupplierPerformance"]] = relationship(
        "SupplierPerformance",
        back_populates="supplier",
        cascade="all, delete-orphan"
    )

    purchase_orders: Mapped[List["PurchaseOrder"]] = relationship(
        "PurchaseOrder",
        back_populates="supplier",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Supplier(id={self.id}, name='{self.name}', country='{self.country}')>"


class SupplierProduct(Base, TimestampMixin):
    """Mapping between local products and supplier's 1688.com products.

    This model enables the matching between:
    - Local product catalog (MagFlow products)
    - Supplier's product offerings from 1688.com scraping
    - Price and availability tracking
    """

    __tablename__ = "supplier_products"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Relationships
    supplier_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.suppliers.id"),
        nullable=False,
        index=True
    )
    local_product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.products.id"),
        nullable=False,
        index=True
    )

    # 1688.com Product Data
    supplier_product_name: Mapped[str] = mapped_column(String(1000))  # Chinese name
    supplier_product_url: Mapped[str] = mapped_column(String(1000))   # 1688.com URL
    supplier_image_url: Mapped[str] = mapped_column(String(1000))     # Product image
    supplier_price: Mapped[float] = mapped_column(Float)
    supplier_currency: Mapped[str] = mapped_column(String(3), default="CNY")
    supplier_specifications: Mapped[Optional[dict]] = mapped_column(JSON)

    # Matching Information
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    manual_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    confirmed_by: Mapped[Optional[int]] = mapped_column(Integer)  # User ID
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Status and Tracking
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_price_update: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    price_history: Mapped[Optional[List[dict]]] = mapped_column(JSON)  # Track price changes

    # Relationships
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="products")
    local_product: Mapped["Product"] = relationship("Product", back_populates="supplier_mappings")

    def __repr__(self) -> str:
        return f"<SupplierProduct(supplier={self.supplier_id}, product={self.local_product_id})>"


class SupplierPerformance(Base, TimestampMixin):
    """Track supplier performance metrics over time.

    Records various performance indicators for each supplier including:
    - Lead time performance
    - Quality metrics
    - Communication responsiveness
    - Order fulfillment accuracy
    """

    __tablename__ = "supplier_performance"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    supplier_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.suppliers.id"),
        nullable=False,
        index=True
    )

    # Performance Metrics
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)  # lead_time, quality, etc.
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    order_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    notes: Mapped[Optional[str]] = mapped_column(String(500))

    # Relationships
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="performance_records")

    def __repr__(self) -> str:
        return f"<SupplierPerformance(supplier={self.supplier_id}, type={self.metric_type}, value={self.metric_value})>"


class PurchaseOrder(Base, TimestampMixin):
    """Purchase orders sent to suppliers.

    Manages the complete lifecycle of purchase orders including:
    - Order creation and supplier assignment
    - Order confirmation and tracking
    - Delivery and quality control
    - Payment processing
    """

    __tablename__ = "purchase_orders"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Basic Information
    order_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    supplier_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.suppliers.id"),
        nullable=False,
        index=True
    )

    # Order Details
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        index=True
    )  # draft, sent, confirmed, shipped, delivered, cancelled
    order_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expected_delivery_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    actual_delivery_date: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Financial Information
    total_value: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    exchange_rate: Mapped[float] = mapped_column(Float, default=1.0)  # Rate la data comenzii

    # Order Items
    order_items: Mapped[Optional[List[dict]]] = mapped_column(JSON)  # List of product orders

    # Communication
    supplier_confirmation: Mapped[Optional[str]] = mapped_column(String(1000))
    internal_notes: Mapped[Optional[str]] = mapped_column(Text)
    attachments: Mapped[Optional[List[str]]] = mapped_column(JSON)  # File paths

    # Quality Control
    quality_check_passed: Mapped[Optional[bool]] = mapped_column(Boolean)
    quality_notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="purchase_orders")

    def __repr__(self) -> str:
        return f"<PurchaseOrder(order={self.order_number}, supplier={self.supplier_id}, status={self.status})>"


class PurchaseOrderItem(Base, TimestampMixin):
    """Individual items within a purchase order.

    Detailed tracking of each product ordered including:
    - Quantities and pricing
    - Expected vs actual delivery
    - Quality control per item
    """

    __tablename__ = "purchase_order_items"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    purchase_order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.purchase_orders.id"),
        nullable=False,
        index=True
    )
    supplier_product_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("app.supplier_products.id"),
        index=True
    )
    local_product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.products.id"),
        nullable=False,
        index=True
    )

    # Order Details
    quantity_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_received: Mapped[Optional[int]] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)

    # Delivery Tracking
    expected_delivery_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    actual_delivery_date: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Quality Control
    quality_status: Mapped[str] = mapped_column(
        String(20),
        default="pending"
    )  # pending, passed, failed, partial
    quality_notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder")
    supplier_product: Mapped[Optional["SupplierProduct"]] = relationship("SupplierProduct")
    local_product: Mapped["Product"] = relationship("Product")

    def __repr__(self) -> str:
        return f"<PurchaseOrderItem(order={self.purchase_order_id}, product={self.local_product_id}, qty={self.quantity_ordered})>"


# Association table for supplier categories if needed in the future
supplier_categories = Table(
    "supplier_categories",
    Base.metadata,
    Column("supplier_id", ForeignKey("app.suppliers.id"), primary_key=True),
    Column("category_id", ForeignKey("app.categories.id"), primary_key=True),
    schema="app"
)
