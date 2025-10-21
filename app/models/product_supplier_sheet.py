"""
Product Supplier Models for Google Sheets Integration
Maps products to their suppliers with pricing information from Google Sheets
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.supplier import Supplier

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class ProductSupplierSheet(Base, TimestampMixin):
    """
    Maps products to suppliers from Google Sheets Product_Suppliers tab

    This model stores supplier information imported from Google Sheets:
    - SKU reference to local product
    - Supplier name and pricing in CNY
    - Import tracking and metadata

    Multiple suppliers can exist for the same SKU (1-5 suppliers per product)
    """

    __tablename__ = "product_supplier_sheets"
    __table_args__ = (
        UniqueConstraint("sku", "supplier_name", name="uq_product_supplier_sku_name"),
        {"schema": "app", "extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Supplier reference (FK - added to sync with database migration)
    supplier_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("app.suppliers.id"),
        nullable=True,
        index=True,
        comment="Foreign key to supplier (replaces supplier_name text for better data integrity)",
    )

    # Product reference
    sku: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Product SKU from Google Sheets Products tab",
    )

    # Supplier information
    supplier_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Supplier name from Google Sheets Product_Suppliers tab",
    )

    price_cny: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Supplier price in Chinese Yuan (CNY)"
    )

    # Optional supplier details
    supplier_contact: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Supplier contact information"
    )

    supplier_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="Supplier product URL (e.g., 1688.com link)",
    )

    supplier_notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Additional notes about this supplier"
    )

    supplier_product_chinese_name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Product name in Chinese from supplier (for orders)",
    )

    supplier_product_specification: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Product specifications from supplier (specific to each supplier)",
    )

    # Pricing metadata
    price_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the price was last updated in Google Sheets",
    )

    exchange_rate_cny_ron: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Exchange rate CNY to RON at time of import"
    )

    calculated_price_ron: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Calculated price in RON using exchange rate"
    )

    # Import tracking
    google_sheet_row: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Row number in Google Sheets Product_Suppliers tab",
    )

    last_imported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time this supplier was imported from Google Sheets",
    )

    import_source: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default="google_sheets", comment="Source of import"
    )

    # Status flags
    is_active: Mapped[bool] = mapped_column(
        Boolean(),
        default=True,
        index=True,
        comment="Whether this supplier mapping is active",
    )

    is_preferred: Mapped[bool] = mapped_column(
        Boolean(),
        default=False,
        comment="Whether this is the preferred supplier for this SKU",
    )

    # Verification
    is_verified: Mapped[bool] = mapped_column(
        Boolean(),
        default=False,
        comment="Whether this supplier mapping has been manually verified",
    )

    verified_by: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="User who verified this mapping"
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When this mapping was verified"
    )

    # Relationships
    supplier: Mapped["Supplier | None"] = relationship(
        "Supplier",
        foreign_keys=[supplier_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<ProductSupplierSheet sku:{self.sku} supplier:{self.supplier_name} "
            f"price:{self.price_cny} CNY>"
        )

    def get_price_display(self) -> str:
        """Get formatted price display"""
        price_str = f"{self.price_cny:.2f} CNY"
        if self.calculated_price_ron:
            price_str += f" (~{self.calculated_price_ron:.2f} RON)"
        return price_str

    def calculate_ron_price(self, exchange_rate: float) -> float:
        """Calculate RON price using given exchange rate"""
        return self.price_cny * exchange_rate
