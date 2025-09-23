"""Database models for storing eMAG offer data and import operations."""

from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin


class EmagOfferStatus(str, Enum):
    """Status of an eMAG offer."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"
    PENDING = "pending"
    BLOCKED = "blocked"


class EmagOfferType(str, Enum):
    """Type of eMAG offer."""

    MAIN = "main"  # Seller-Fulfilled Network (SFN)
    FBE = "fbe"  # Fulfilled by eMAG


class EmagSyncStatus(str, Enum):
    """Status of import/sync operations."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class EmagProduct(Base, TimestampMixin):
    """Product information retrieved from eMAG."""

    __tablename__ = "emag_products"
    __table_args__ = ({"schema": "app"},)

    id = Column(Integer, primary_key=True, index=True)
    emag_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    part_number = Column(String(100), nullable=True, index=True)

    # Category and brand references (may not exist in internal system)
    emag_category_id = Column(Integer, nullable=True, index=True)
    emag_brand_id = Column(Integer, nullable=True, index=True)
    emag_category_name = Column(String(255), nullable=True)
    emag_brand_name = Column(String(255), nullable=True)

    # Product characteristics
    characteristics = Column(JSONB, default=dict, nullable=False)

    # Images
    images = Column(JSONB, default=list, nullable=False)

    # Status and metadata
    is_active = Column(Boolean, default=True, nullable=False)
    last_imported_at = Column(DateTime(timezone=True), nullable=True)
    emag_updated_at = Column(DateTime(timezone=True), nullable=True)

    # Raw data from eMAG API
    raw_data = Column(JSONB, nullable=True)

    # Relationships
    offers = relationship(
        "EmagProductOffer",
        back_populates="product",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<EmagProduct {self.emag_id}: {self.name}>"


class EmagProductOffer(Base, TimestampMixin):
    """Product offer information retrieved from eMAG."""

    __tablename__ = "emag_product_offers"
    __table_args__ = (
        Index("idx_emag_offer_product", "emag_product_id"),
        Index("idx_emag_offer_status", "status"),
        Index("idx_emag_offer_imported", "last_imported_at"),
        Index("idx_emag_offer_batch", "import_batch_id"),
        {"schema": "app"},
    )

    id = Column(Integer, primary_key=True, index=True)
    emag_product_id = Column(String(100), nullable=False, index=True)
    emag_offer_id = Column(Integer, nullable=False, index=True)

    # Foreign key to EmagProduct
    product_id = Column(Integer, ForeignKey("app.emag_products.id"), nullable=True)
    product = relationship("EmagProduct", back_populates="offers")

    # Pricing information
    price = Column(Float, nullable=True)
    sale_price = Column(Float, nullable=True)
    currency = Column(String(3), default="RON", nullable=False)

    # Stock information
    stock = Column(Integer, default=0, nullable=False)
    stock_status = Column(String(50), nullable=True)
    handling_time = Column(Integer, nullable=True)  # days

    # Status and availability
    status = Column(String(50), nullable=True)
    is_available = Column(Boolean, default=True, nullable=False)
    is_visible = Column(Boolean, default=True, nullable=False)

    # VAT information
    vat_rate = Column(Float, nullable=True)
    vat_included = Column(Boolean, default=True, nullable=False)

    # Warehouse information
    warehouse_id = Column(Integer, nullable=True)
    warehouse_name = Column(String(255), nullable=True)

    # Account type (MAIN/FBE)
    account_type = Column(String(10), nullable=False, default="main")

    # Warranty information
    warranty = Column(Integer, nullable=True)  # months

    # Import metadata
    last_imported_at = Column(DateTime(timezone=True), nullable=True)
    emag_updated_at = Column(DateTime(timezone=True), nullable=True)
    import_batch_id = Column(String(100), nullable=True, index=True)

    # Raw data from eMAG API
    raw_data = Column(JSONB, nullable=True)

    # Additional metadata
    metadata_ = Column("metadata", JSONB, default=dict, nullable=False)

    def __repr__(self):
        return f"<EmagProductOffer {self.emag_offer_id}: {self.emag_product_id}>"


class EmagOfferSync(Base, TimestampMixin):
    """Tracks import/sync operations for eMAG offers."""

    __tablename__ = "emag_offer_syncs"
    __table_args__ = (
        Index("idx_emag_sync_status", "status"),
        Index("idx_emag_sync_account", "account_type"),
        Index("idx_emag_sync_started", "started_at"),
        Index("idx_emag_sync_completed", "completed_at"),
        {"schema": "app"},
    )

    id = Column(Integer, primary_key=True, index=True)
    sync_id = Column(String(100), unique=True, nullable=False, index=True)

    # Sync configuration
    account_type = Column(String(10), nullable=False, default="main")
    operation_type = Column(
        String(50),
        nullable=False,
    )  # 'full_import', 'incremental', 'single_offer', etc.

    # Date range for sync (removed - not in DB table)

    # Status and progress
    status = Column(String(20), nullable=False, default="pending")
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Statistics
    total_offers_processed = Column(Integer, default=0, nullable=False)
    offers_created = Column(Integer, default=0, nullable=False)
    offers_updated = Column(Integer, default=0, nullable=False)
    offers_failed = Column(Integer, default=0, nullable=False)
    offers_skipped = Column(Integer, default=0, nullable=False)

    # Error tracking
    error_count = Column(Integer, default=0, nullable=False)
    errors = Column(JSONB, default=list, nullable=False)

    # Filters used for sync
    filters = Column(JSONB, default=dict, nullable=False)

    # User who initiated the sync
    initiated_by = Column(String(100), nullable=True)
    user_id = Column(Integer, nullable=True)

    # Additional metadata
    metadata_ = Column("metadata", JSONB, default=dict, nullable=False)

    @property
    def is_completed(self) -> bool:
        """Check if the sync operation is completed."""
        return self.status in ["completed", "failed", "partial"]

    @property
    def success_rate(self) -> float:
        """Calculate the success rate of the sync operation."""
        if self.total_offers_processed == 0:
            return 0.0
        successful = self.offers_created + self.offers_updated
        return (successful / self.total_offers_processed) * 100

    def __repr__(self):
        return f"<EmagOfferSync {self.sync_id}: {self.status} ({self.total_offers_processed} offers)>"


class EmagImportConflict(Base, TimestampMixin):
    """Tracks conflicts that occurred during import operations."""

    __tablename__ = "emag_import_conflicts"
    __table_args__ = ({"schema": "app"},)

    id = Column(Integer, primary_key=True, index=True)
    sync_id = Column(
        String(100),
        ForeignKey("app.emag_offer_syncs.sync_id"),
        nullable=False,
        index=True,
    )

    # Conflict details
    emag_offer_id = Column(Integer, nullable=False)
    emag_product_id = Column(String(100), nullable=False)
    conflict_type = Column(
        String(50),
        nullable=False,
    )  # 'duplicate_offer', 'price_mismatch', 'stock_discrepancy', etc.

    # Data comparison
    emag_data = Column(JSONB, nullable=False)
    internal_data = Column(JSONB, nullable=True)

    # Resolution
    resolution = Column(
        String(50),
        nullable=True,
    )  # 'skip', 'update', 'merge', 'manual_review'
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(100), nullable=True)

    # Status
    status = Column(
        String(20),
        default="pending",
        nullable=False,
    )  # 'pending', 'resolved', 'ignored'

    # Additional information
    notes = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSONB, default=dict, nullable=False)

    # Relationships
    sync = relationship("EmagOfferSync", backref="conflicts")

    def __repr__(self):
        return f"<EmagImportConflict {self.emag_offer_id}: {self.conflict_type}>"
