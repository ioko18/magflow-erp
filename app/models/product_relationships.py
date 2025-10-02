"""
Product Relationships and Variant Tracking Models.

This module handles complex product relationships including:
- Product variants (same physical product, different SKU/EAN/name)
- Competition tracking (when other sellers attach to your products)
- PNK consistency tracking between MAIN and FBE accounts
- Product genealogy (parent-child relationships for re-published products)
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    CheckConstraint,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.db.base_class import Base


class ProductVariant(Base):
    """
    Track product variants - different SKUs/EANs for the same physical product.
    
    Use cases:
    - Original product got "hijacked" by competitors, need to re-publish
    - Same product sold under different names/SKUs on MAIN vs FBE
    - Product variations (color, size) that are essentially the same item
    """
    
    __tablename__ = "product_variants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Variant group - all variants of the same physical product share this ID
    variant_group_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Product identification
    local_product_id = Column(Integer, ForeignKey("app.products.id"), nullable=True)
    emag_product_id = Column(UUID(as_uuid=True), ForeignKey("app.emag_products_v2.id"), nullable=True)
    
    # Product identifiers
    sku = Column(String(100), nullable=False, index=True)
    ean = Column(JSONB, nullable=True)  # Array of EAN codes
    part_number_key = Column(String(50), nullable=True, index=True)  # eMAG PNK
    
    # Variant metadata
    variant_type = Column(String(50), nullable=False)  # original, republished, competitor_hijacked, variation
    variant_reason = Column(Text, nullable=True)  # Why this variant was created
    is_primary = Column(Boolean, nullable=False, default=False)  # Is this the main/original variant?
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Account tracking
    account_type = Column(String(10), nullable=True)  # main, fbe, local
    
    # Parent-child relationship for re-published products
    parent_variant_id = Column(UUID(as_uuid=True), ForeignKey("app.product_variants.id"), nullable=True)
    
    # Competition tracking
    has_competitors = Column(Boolean, nullable=False, default=False)
    competitor_count = Column(Integer, nullable=True)  # From number_of_offers
    last_competitor_check = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deactivated_at = Column(DateTime, nullable=True)
    
    # Metadata
    notes = Column(Text, nullable=True)
    extra_data = Column(JSONB, nullable=True)  # Renamed from 'metadata' (reserved by SQLAlchemy)
    
    # Relationships
    parent_variant = relationship("ProductVariant", remote_side=[id], backref="child_variants")
    
    __table_args__ = (
        Index("idx_product_variants_group", "variant_group_id"),
        Index("idx_product_variants_sku", "sku"),
        Index("idx_product_variants_pnk", "part_number_key"),
        Index("idx_product_variants_active", "is_active"),
        Index("idx_product_variants_type", "variant_type"),
        CheckConstraint(
            "variant_type IN ('original', 'republished', 'competitor_hijacked', 'variation', 'test')",
            name="ck_product_variants_type"
        ),
        CheckConstraint(
            "account_type IN ('main', 'fbe', 'local', 'both') OR account_type IS NULL",
            name="ck_product_variants_account"
        ),
        {"schema": "app"}
    )


class ProductPNKTracking(Base):
    """
    Track part_number_key consistency between MAIN and FBE accounts.
    
    Since PNK should be identical between MAIN and FBE after attachment,
    this table helps identify inconsistencies and missing PNKs.
    """
    
    __tablename__ = "product_pnk_tracking"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Product identification
    sku = Column(String(100), nullable=False, index=True)
    
    # PNK values
    pnk_main = Column(String(50), nullable=True, index=True)
    pnk_fbe = Column(String(50), nullable=True, index=True)
    
    # Product IDs
    emag_main_id = Column(UUID(as_uuid=True), nullable=True)
    emag_fbe_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Consistency tracking
    is_consistent = Column(Boolean, nullable=False, default=True)  # PNK matches between MAIN and FBE
    has_main_pnk = Column(Boolean, nullable=False, default=False)
    has_fbe_pnk = Column(Boolean, nullable=False, default=False)
    
    # Status
    status = Column(String(50), nullable=False, default="pending")  # pending, consistent, inconsistent, missing
    
    # Timestamps
    first_detected = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_checked = Column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    
    # Resolution tracking
    resolution_action = Column(String(100), nullable=True)  # manual_fix, auto_sync, ignored
    resolution_notes = Column(Text, nullable=True)
    
    __table_args__ = (
        Index("idx_pnk_tracking_sku", "sku"),
        Index("idx_pnk_tracking_status", "status"),
        Index("idx_pnk_tracking_consistency", "is_consistent"),
        UniqueConstraint("sku", name="uq_pnk_tracking_sku"),
        CheckConstraint(
            "status IN ('pending', 'consistent', 'inconsistent', 'missing', 'resolved')",
            name="ck_pnk_tracking_status"
        ),
        {"schema": "app"}
    )


class ProductCompetitionLog(Base):
    """
    Log when competitors attach to your products (number_of_offers increases).
    
    This helps identify when you need to re-publish a product with a different
    SKU/EAN/name to avoid competition.
    """
    
    __tablename__ = "product_competition_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Product identification
    emag_product_id = Column(UUID(as_uuid=True), ForeignKey("app.emag_products_v2.id"), nullable=False)
    sku = Column(String(100), nullable=False, index=True)
    part_number_key = Column(String(50), nullable=True, index=True)
    account_type = Column(String(10), nullable=False)  # main or fbe
    
    # Competition metrics
    number_of_offers = Column(Integer, nullable=False)  # Total offers on this product
    your_rank = Column(Integer, nullable=True)  # Your buy_button_rank
    best_competitor_price = Column(Float, nullable=True)  # Lowest price from competitors
    your_price = Column(Float, nullable=True)
    
    # Detection
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    previous_offer_count = Column(Integer, nullable=True)
    new_competitors = Column(Integer, nullable=True)  # How many new competitors since last check
    
    # Status
    requires_action = Column(Boolean, nullable=False, default=False)  # Should you re-publish?
    action_taken = Column(String(100), nullable=True)  # republished, price_adjusted, ignored
    action_taken_at = Column(DateTime, nullable=True)
    
    # Metadata
    competitor_details = Column(JSONB, nullable=True)  # Additional competitor info
    notes = Column(Text, nullable=True)
    
    __table_args__ = (
        Index("idx_competition_log_product", "emag_product_id"),
        Index("idx_competition_log_sku", "sku"),
        Index("idx_competition_log_detected", "detected_at"),
        Index("idx_competition_log_action_required", "requires_action"),
        CheckConstraint(
            "account_type IN ('main', 'fbe')",
            name="ck_competition_log_account"
        ),
        {"schema": "app"}
    )


class ProductGenealogy(Base):
    """
    Track the complete history and relationships of product variants.
    
    This creates a family tree of products, showing:
    - Original product
    - Re-published variants (due to competition)
    - Related products (same physical item, different listing)
    """
    
    __tablename__ = "product_genealogy"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Family identification
    family_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # All related products share this
    family_name = Column(String(255), nullable=True)  # Human-readable family name
    
    # Product identification
    product_id = Column(UUID(as_uuid=True), nullable=False)  # Can be local or emag product
    product_type = Column(String(20), nullable=False)  # local, emag_main, emag_fbe
    sku = Column(String(100), nullable=False, index=True)
    
    # Genealogy
    generation = Column(Integer, nullable=False, default=1)  # 1=original, 2=first republish, etc.
    parent_id = Column(UUID(as_uuid=True), ForeignKey("app.product_genealogy.id"), nullable=True)
    is_root = Column(Boolean, nullable=False, default=False)  # Is this the original product?
    
    # Lifecycle
    lifecycle_stage = Column(String(50), nullable=False)  # active, superseded, retired, archived
    superseded_by_id = Column(UUID(as_uuid=True), ForeignKey("app.product_genealogy.id"), nullable=True)
    superseded_at = Column(DateTime, nullable=True)
    supersede_reason = Column(Text, nullable=True)  # Why was this product replaced?
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Metadata
    extra_data = Column(JSONB, nullable=True)  # Renamed from 'metadata' (reserved by SQLAlchemy)
    notes = Column(Text, nullable=True)
    
    # Relationships
    parent = relationship("ProductGenealogy", remote_side=[id], foreign_keys=[parent_id], backref="children")
    superseded_by = relationship("ProductGenealogy", remote_side=[id], foreign_keys=[superseded_by_id], backref="supersedes")
    
    __table_args__ = (
        Index("idx_genealogy_family", "family_id"),
        Index("idx_genealogy_sku", "sku"),
        Index("idx_genealogy_stage", "lifecycle_stage"),
        Index("idx_genealogy_root", "is_root"),
        CheckConstraint(
            "product_type IN ('local', 'emag_main', 'emag_fbe')",
            name="ck_genealogy_product_type"
        ),
        CheckConstraint(
            "lifecycle_stage IN ('active', 'superseded', 'retired', 'archived', 'draft')",
            name="ck_genealogy_lifecycle"
        ),
        CheckConstraint(
            "generation >= 1",
            name="ck_genealogy_generation"
        ),
        {"schema": "app"}
    )
