"""Supplier management models for MagFlow ERP.

This module contains all database models for supplier management including:
- Supplier profiles and information
- Supplier-product mappings for 1688.com integration
- Supplier performance tracking
- Purchase orders and order management
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.product_supplier_sheet import ProductSupplierSheet
    from app.models.purchase import PurchaseOrder

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
    code: Mapped[str | None] = mapped_column(
        String(20), unique=True, nullable=True, index=True
    )  # Supplier code for purchase management
    country: Mapped[str] = mapped_column(String(100), default="China", index=True)
    contact_person: Mapped[str | None] = mapped_column(String(255), index=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    website: Mapped[str | None] = mapped_column(String(500))
    address: Mapped[str | None] = mapped_column(Text)  # Full address
    city: Mapped[str | None] = mapped_column(String(50))
    tax_id: Mapped[str | None] = mapped_column(
        String(50)
    )  # Tax identification number

    # Commercial Terms
    lead_time_days: Mapped[int] = mapped_column(Integer, default=30)
    min_order_value: Mapped[float] = mapped_column(Float, default=0.0)
    min_order_qty: Mapped[int] = mapped_column(Integer, default=1)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    payment_terms: Mapped[str] = mapped_column(String(255), default="30 days")

    # Specializations and Products
    specializations: Mapped[dict | None] = mapped_column(JSON)  # Detailed categories
    product_categories: Mapped[list[str] | None] = mapped_column(JSON)  # Simple list

    # Performance Metrics
    rating: Mapped[float] = mapped_column(Float, default=5.0)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    on_time_delivery_rate: Mapped[float] = mapped_column(Float, default=0.0)
    quality_score: Mapped[float] = mapped_column(Float, default=5.0)

    # Status and Notes
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str] | None] = mapped_column(JSON)

    # Display Order for UI sorting (lower number = higher priority)
    display_order: Mapped[int] = mapped_column(Integer, default=999, index=True)

    # Relationships
    products: Mapped[list["SupplierProduct"]] = relationship(
        "SupplierProduct", back_populates="supplier", cascade="all, delete-orphan"
    )

    sheet_products: Mapped[list["ProductSupplierSheet"]] = relationship(
        "ProductSupplierSheet",
        back_populates="supplier",
        foreign_keys="[ProductSupplierSheet.supplier_id]",
    )

    performance_records: Mapped[list["SupplierPerformance"]] = relationship(
        "SupplierPerformance", back_populates="supplier", cascade="all, delete-orphan"
    )

    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(
        "PurchaseOrder", back_populates="supplier"
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
        Integer, ForeignKey("app.suppliers.id"), nullable=False, index=True
    )
    local_product_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("app.products.id"), nullable=True, index=True
    )

    # 1688.com Product Data
    supplier_product_name: Mapped[str] = mapped_column(String(1000))  # Chinese name
    supplier_product_url: Mapped[str] = mapped_column(String(1000))  # 1688.com URL
    supplier_image_url: Mapped[str] = mapped_column(String(1000))  # Product image
    supplier_price: Mapped[float] = mapped_column(Float)
    supplier_currency: Mapped[str] = mapped_column(String(3), default="CNY")
    supplier_specifications: Mapped[dict | None] = mapped_column(JSON)

    # Price calculation fields (for Google Sheets promotion compatibility)
    exchange_rate: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Exchange rate CNY to RON"
    )
    calculated_price_ron: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Calculated price in RON using exchange rate"
    )

    # Matching Information
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    manual_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    confirmed_by: Mapped[int | None] = mapped_column(Integer)  # User ID
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Status and Tracking
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_price_update: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    price_history: Mapped[list[dict] | None] = mapped_column(
        JSON
    )  # Track price changes

    # Import tracking
    import_source: Mapped[str | None] = mapped_column(
        String(50), default="manual", index=True
    )
    is_preferred: Mapped[bool | None] = mapped_column(Boolean, default=False)
    supplier_product_chinese_name: Mapped[str | None] = mapped_column(String(500))
    supplier_product_specification: Mapped[str | None] = mapped_column(String(1000))

    # Relationships
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="products")
    local_product: Mapped["Product | None"] = relationship(
        "Product", back_populates="supplier_mappings"
    )

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
        Integer, ForeignKey("app.suppliers.id"), nullable=False, index=True
    )

    # Performance Metrics
    metric_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # lead_time, quality, etc.
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    order_id: Mapped[int | None] = mapped_column(Integer, index=True)
    notes: Mapped[str | None] = mapped_column(String(500))

    # Relationships
    supplier: Mapped["Supplier"] = relationship(
        "Supplier", back_populates="performance_records"
    )

    def __repr__(self) -> str:
        return (
            f"<SupplierPerformance(supplier={self.supplier_id}, "
            f"type={self.metric_type}, value={self.metric_value})>"
        )


# PurchaseOrder and related models are now defined in app.models.purchase
# to avoid duplication and maintain better separation of concerns


# Association table for supplier categories if needed in the future
supplier_categories = Table(
    "supplier_categories",
    Base.metadata,
    Column("supplier_id", ForeignKey("app.suppliers.id"), primary_key=True),
    Column("category_id", ForeignKey("app.categories.id"), primary_key=True),
    schema="app",
)
