"""Supplier product matching models for 1688.com product comparison.

This module handles the intelligent matching of similar products from multiple
Chinese suppliers to enable price comparison and best supplier selection.
"""

from datetime import datetime
from typing import List, Optional
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Index,
    UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class MatchingStatus(str, Enum):
    """Status of product matching."""
    PENDING = "pending"  # Awaiting matching
    AUTO_MATCHED = "auto_matched"  # Automatically matched by algorithm
    MANUAL_MATCHED = "manual_matched"  # Manually confirmed by user
    REJECTED = "rejected"  # User rejected the match
    NEEDS_REVIEW = "needs_review"  # Low confidence, needs manual review


class SupplierRawProduct(Base, TimestampMixin):
    """Raw product data scraped from 1688.com suppliers.
    
    This stores the original Excel data from supplier scraping:
    - Chinese product name
    - Price in CNY
    - Product URL from supplier's 1688.com store
    - Image URL
    """

    __tablename__ = "supplier_raw_products"
    __table_args__ = (
        Index('idx_supplier_raw_name', 'chinese_name'),
        Index('idx_supplier_raw_supplier', 'supplier_id'),
        Index('idx_supplier_raw_status', 'matching_status'),
        Index('idx_supplier_raw_active', 'is_active'),
        {"schema": "app", "extend_existing": True}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Supplier Reference
    supplier_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.suppliers.id"),
        nullable=False,
        index=True
    )

    # Raw Data from Excel (1688.com scraping)
    chinese_name: Mapped[str] = mapped_column(String(1000), nullable=False)
    price_cny: Mapped[float] = mapped_column(Float, nullable=False)
    product_url: Mapped[str] = mapped_column(String(2000), nullable=False)
    image_url: Mapped[str] = mapped_column(String(2000), nullable=False)

    # Processed Data
    english_name: Mapped[Optional[str]] = mapped_column(String(1000))  # Auto-translated
    normalized_name: Mapped[Optional[str]] = mapped_column(String(1000))  # For matching

    # Image Analysis
    image_hash: Mapped[Optional[str]] = mapped_column(String(64))  # Perceptual hash
    image_features: Mapped[Optional[dict]] = mapped_column(JSON)  # ML features
    image_downloaded: Mapped[bool] = mapped_column(Boolean, default=False)
    image_local_path: Mapped[Optional[str]] = mapped_column(String(500))

    # Matching Status
    matching_status: Mapped[str] = mapped_column(
        String(20),
        default=MatchingStatus.PENDING,
        index=True
    )
    product_group_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("app.product_matching_groups.id"),
        index=True
    )

    # Metadata
    import_batch_id: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    import_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_price_check: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Additional scraped data
    specifications: Mapped[Optional[dict]] = mapped_column(JSON)
    supplier_sku: Mapped[Optional[str]] = mapped_column(String(100))
    moq: Mapped[Optional[int]] = mapped_column(Integer)  # Minimum Order Quantity

    # Relationships
    supplier = relationship("Supplier")
    product_group: Mapped[Optional["ProductMatchingGroup"]] = relationship(
        "ProductMatchingGroup",
        back_populates="raw_products"
    )

    def __repr__(self) -> str:
        return f"<SupplierRawProduct(id={self.id}, supplier={self.supplier_id}, name='{self.chinese_name[:30]}...')>"


class ProductMatchingGroup(Base, TimestampMixin):
    """Group of similar products from different suppliers.
    
    This represents a cluster of products that are considered the same item
    from different suppliers, enabling price comparison.
    """

    __tablename__ = "product_matching_groups"
    __table_args__ = (
        Index('idx_group_status', 'status'),
        Index('idx_group_confidence', 'confidence_score'),
        {"schema": "app", "extend_existing": True}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Group Information
    group_name: Mapped[str] = mapped_column(String(500), nullable=False)  # Representative name
    group_name_en: Mapped[Optional[str]] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Representative Image (from best quality source)
    representative_image_url: Mapped[Optional[str]] = mapped_column(String(2000))
    representative_image_hash: Mapped[Optional[str]] = mapped_column(String(64))

    # Matching Metadata
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)  # Average confidence
    matching_method: Mapped[str] = mapped_column(String(50))  # text, image, hybrid, manual

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default=MatchingStatus.AUTO_MATCHED,
        index=True
    )
    verified_by: Mapped[Optional[int]] = mapped_column(Integer)  # User ID
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Price Analysis
    min_price_cny: Mapped[Optional[float]] = mapped_column(Float)
    max_price_cny: Mapped[Optional[float]] = mapped_column(Float)
    avg_price_cny: Mapped[Optional[float]] = mapped_column(Float)
    best_supplier_id: Mapped[Optional[int]] = mapped_column(Integer)  # Supplier with best price

    # Product Count
    product_count: Mapped[int] = mapped_column(Integer, default=0)

    # Local Product Mapping (if matched to catalog)
    local_product_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("app.products.id"),
        index=True
    )

    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    raw_products: Mapped[List["SupplierRawProduct"]] = relationship(
        "SupplierRawProduct",
        back_populates="product_group"
    )
    local_product = relationship("Product")

    def __repr__(self) -> str:
        return f"<ProductMatchingGroup(id={self.id}, name='{self.group_name[:30]}...', products={self.product_count})>"


class ProductMatchingScore(Base, TimestampMixin):
    """Detailed matching scores between products.
    
    Stores the similarity scores between pairs of products for transparency
    and debugging of the matching algorithm.
    """

    __tablename__ = "product_matching_scores"
    __table_args__ = (
        Index('idx_matching_products', 'product_a_id', 'product_b_id'),
        Index('idx_matching_score', 'total_score'),
        UniqueConstraint('product_a_id', 'product_b_id', name='uq_product_pair'),
        {"schema": "app", "extend_existing": True}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Product Pair
    product_a_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.supplier_raw_products.id"),
        nullable=False
    )
    product_b_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.supplier_raw_products.id"),
        nullable=False
    )

    # Similarity Scores (0.0 to 1.0)
    text_similarity: Mapped[float] = mapped_column(Float, default=0.0)
    image_similarity: Mapped[Optional[float]] = mapped_column(Float)
    price_similarity: Mapped[Optional[float]] = mapped_column(Float)
    total_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Matching Details
    matching_algorithm: Mapped[str] = mapped_column(String(50))  # cosine, jaccard, perceptual_hash, etc.
    matching_features: Mapped[Optional[dict]] = mapped_column(JSON)  # Detailed breakdown

    # Status
    is_match: Mapped[bool] = mapped_column(Boolean, default=False)
    threshold_used: Mapped[float] = mapped_column(Float, default=0.7)

    # Relationships
    product_a = relationship(
        "SupplierRawProduct",
        foreign_keys=[product_a_id]
    )
    product_b = relationship(
        "SupplierRawProduct",
        foreign_keys=[product_b_id]
    )

    def __repr__(self) -> str:
        return f"<ProductMatchingScore(a={self.product_a_id}, b={self.product_b_id}, score={self.total_score:.2f})>"


class SupplierPriceHistory(Base, TimestampMixin):
    """Historical price tracking for supplier products.
    
    Tracks price changes over time to identify trends and best buying opportunities.
    """

    __tablename__ = "supplier_price_history"
    __table_args__ = (
        Index('idx_price_history_product', 'raw_product_id'),
        Index('idx_price_history_date', 'recorded_at'),
        {"schema": "app", "extend_existing": True}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    raw_product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.supplier_raw_products.id"),
        nullable=False,
        index=True
    )

    # Price Data
    price_cny: Mapped[float] = mapped_column(Float, nullable=False)
    price_change: Mapped[Optional[float]] = mapped_column(Float)  # Change from previous
    price_change_percent: Mapped[Optional[float]] = mapped_column(Float)

    # Timestamp
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Context
    source: Mapped[str] = mapped_column(String(50), default="scraping")  # scraping, manual, api
    notes: Mapped[Optional[str]] = mapped_column(String(500))

    # Relationships
    raw_product = relationship("SupplierRawProduct")

    def __repr__(self) -> str:
        return f"<SupplierPriceHistory(product={self.raw_product_id}, price={self.price_cny} CNY, date={self.recorded_at})>"
