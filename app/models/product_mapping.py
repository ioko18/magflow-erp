"""
Product Mapping Models for Google Sheets and eMAG Integration
Maps local products to eMAG MAIN and FBE accounts
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class ProductMapping(Base, TimestampMixin):
    """
    Maps local products from Google Sheets to eMAG products (MAIN and FBE accounts)
    
    This table creates a unified view of products across:
    - Local database (Google Sheets import)
    - eMAG MAIN account
    - eMAG FBE account
    """
    
    __tablename__ = "product_mappings"
    __table_args__ = (
        UniqueConstraint('local_sku', name='uq_product_mapping_local_sku'),
        {"schema": "app", "extend_existing": True}
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Local product information (from Google Sheets)
    local_sku: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="SKU from local database/Google Sheets"
    )
    local_product_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Romanian product name from Google Sheets"
    )
    local_price: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Price from Google Sheets (Emag_FBE_RO_Price_RON)"
    )
    
    # eMAG MAIN account mapping
    emag_main_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        comment="ID from emag_products_v2 table for MAIN account"
    )
    emag_main_part_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Part number from eMAG MAIN account"
    )
    emag_main_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Sync status for MAIN account (mapped, not_found, conflict)"
    )
    
    # eMAG FBE account mapping
    emag_fbe_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        comment="ID from emag_products_v2 table for FBE account"
    )
    emag_fbe_part_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Part number from eMAG FBE account"
    )
    emag_fbe_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Sync status for FBE account (mapped, not_found, conflict)"
    )
    
    # Mapping metadata
    mapping_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Confidence score for automatic mapping (0.0-1.0)"
    )
    mapping_method: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Method used for mapping (exact_sku, fuzzy_name, manual)"
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean(),
        default=False,
        comment="Whether mapping has been manually verified"
    )
    
    # Google Sheets metadata
    google_sheet_row: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Row number in Google Sheets"
    )
    google_sheet_data: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Raw data from Google Sheets (JSON)"
    )
    
    # Import tracking
    last_imported_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Last time data was imported from Google Sheets"
    )
    import_source: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Source of import (google_sheets, manual, api)"
    )
    
    # Notes and flags
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Additional notes about the mapping"
    )
    has_conflicts: Mapped[bool] = mapped_column(
        Boolean(),
        default=False,
        comment="Whether there are conflicts in the mapping"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean(),
        default=True,
        comment="Whether this mapping is active"
    )
    
    def __repr__(self) -> str:
        return f"<ProductMapping sku:{self.local_sku} main:{self.emag_main_status} fbe:{self.emag_fbe_status}>"
    
    def get_mapping_status(self) -> str:
        """Get overall mapping status"""
        if self.emag_main_status == "mapped" and self.emag_fbe_status == "mapped":
            return "fully_mapped"
        elif self.emag_main_status == "mapped" or self.emag_fbe_status == "mapped":
            return "partially_mapped"
        elif self.has_conflicts:
            return "conflict"
        else:
            return "unmapped"
    
    def is_fully_mapped(self) -> bool:
        """Check if product is mapped to both MAIN and FBE"""
        return self.emag_main_status == "mapped" and self.emag_fbe_status == "mapped"
    
    def get_mapped_accounts(self) -> list:
        """Get list of accounts where product is mapped"""
        accounts = []
        if self.emag_main_status == "mapped":
            accounts.append("MAIN")
        if self.emag_fbe_status == "mapped":
            accounts.append("FBE")
        return accounts


class ImportLog(Base, TimestampMixin):
    """
    Tracks imports from Google Sheets
    """
    
    __tablename__ = "import_logs"
    __table_args__ = {"schema": "app", "extend_existing": True}
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Import details
    import_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of import (google_sheets, csv, manual)"
    )
    source_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Name of source (sheet name, file name, etc.)"
    )
    
    # Statistics
    total_rows: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Total rows processed"
    )
    successful_imports: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of successful imports"
    )
    failed_imports: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of failed imports"
    )
    skipped_rows: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of skipped rows"
    )
    
    # Mapping statistics
    auto_mapped_main: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Products automatically mapped to MAIN"
    )
    auto_mapped_fbe: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Products automatically mapped to FBE"
    )
    unmapped_products: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Products that couldn't be mapped"
    )
    
    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    duration_seconds: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    
    # Status and errors
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="in_progress",
        comment="Status: in_progress, completed, failed, cancelled"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # User tracking
    initiated_by: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="User who initiated the import"
    )
    
    def __repr__(self) -> str:
        return f"<ImportLog {self.import_type} {self.status} {self.successful_imports}/{self.total_rows}>"
