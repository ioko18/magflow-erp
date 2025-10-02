"""Product models for MagFlow ERP with clear SKU semantics."""

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Table, Text, desc
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.inventory import Category, InventoryItem
    from app.models.supplier import SupplierProduct

from app.models.product_history import ProductSKUHistory, ProductChangeLog
from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class Product(Base, TimestampMixin):
    """Product model with clear SKU semantics for eMAG integration.

    SKU SEMANTICS:
    - sku: Seller's internal SKU (part_number in eMAG API)
    - emag_part_number_key: eMAG's unique product identifier (part_number_key in eMAG API)
    - ean: European Article Number for product identification
    """

    __tablename__ = "products"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Basic product information
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    chinese_name: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        index=True,
        comment="Chinese product name for supplier matching (1688.com integration)",
    )
    image_url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        comment="Primary product image URL",
    )
    
    # Invoice-specific names (for customs and VAT documentation)
    invoice_name_ro: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Product name for Romanian invoices (shorter, customs-friendly)",
    )
    invoice_name_en: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Product name for English invoices (customs declarations, VAT)",
    )
    
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    short_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # SKU SEMANTICS - Clearly defined
    sku: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Seller's internal SKU (part_number in eMAG API)",
    )

    # eMAG-specific identifiers
    emag_part_number_key: Mapped[Optional[str]] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
        index=True,
        comment="eMAG's unique product identifier (part_number_key in eMAG API)",
    )

    ean: Mapped[Optional[str]] = mapped_column(
        String(18),
        nullable=True,
        index=True,
        comment="European Article Number (EAN/UPC) - alternative to part_number_key",
    )

    # Product details
    brand: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Pricing
    base_price: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        comment="Base price before taxes",
    )
    recommended_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="RON")

    # Dimensions and weight
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    length_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    width_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    height_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Status and flags
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True)
    is_discontinued: Mapped[bool] = mapped_column(Boolean(), default=False)

    # eMAG specific fields
    emag_category_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    emag_brand_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    emag_warranty_months: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Metadata
    characteristics: Mapped[Optional[dict]] = mapped_column(
        Text,
        nullable=True,
    )  # JSON as text
    images: Mapped[Optional[dict]] = mapped_column(Text, nullable=True)  # JSON as text
    attachments: Mapped[Optional[dict]] = mapped_column(
        Text,
        nullable=True,
    )  # JSON as text

    # Relationships
    categories: Mapped[List["Category"]] = relationship(
        "Category",
        secondary="app.product_categories",
        back_populates="products",
        lazy="selectin",
    )

    inventory_items: Mapped[List["InventoryItem"]] = relationship(
        "InventoryItem",
        back_populates="product",
        lazy="selectin",
    )

    # Supplier mappings for 1688.com integration (defined after SupplierProduct class)
    supplier_mappings: Mapped[List["SupplierProduct"]] = relationship(
        "SupplierProduct",
        back_populates="local_product",
        lazy="selectin",
    )

    # History tracking
    sku_history: Mapped[List["ProductSKUHistory"]] = relationship(
        "ProductSKUHistory",
        back_populates="product",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by=lambda: desc(ProductSKUHistory.changed_at)
    )
    
    change_logs: Mapped[List["ProductChangeLog"]] = relationship(
        "ProductChangeLog",
        back_populates="product",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by=lambda: desc(ProductChangeLog.changed_at)
    )

    def __repr__(self) -> str:
        return f"<Product sku:{self.sku} name:{self.name[:50]}...>"

    # SKU semantic methods
    def get_seller_sku(self) -> str:
        """Get seller's internal SKU."""
        return self.sku

    def get_emag_identifier(self) -> Optional[str]:
        """Get eMAG product identifier (part_number_key or EAN)."""
        return self.emag_part_number_key or self.ean

    def is_mapped_to_emag(self) -> bool:
        """Check if product is mapped to eMAG."""
        return self.emag_part_number_key is not None or self.ean is not None

    def get_display_sku(self) -> str:
        """Get SKU for display purposes (seller SKU or eMAG key)."""
        return self.emag_part_number_key or self.sku


# Association table for Product<->Category many-to-many
product_categories = Table(
    "product_categories",
    Base.metadata,
    Column("product_id", ForeignKey("app.products.id"), primary_key=True),
    Column("category_id", ForeignKey("app.categories.id"), primary_key=True),
    schema="app",
    extend_existing=True,
)
