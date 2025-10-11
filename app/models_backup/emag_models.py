"""
eMAG Integration Models for MagFlow ERP.

This module defines SQLAlchemy models for eMAG marketplace integration,
including products, offers, orders, and synchronization tracking.
Follows eMAG API v4.4.9 specifications.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class EmagProductV2(Base):
    """eMAG product model with v4.4.9 fields."""

    __tablename__ = "emag_products_v2"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    emag_id = Column(String(50), nullable=True, index=True)  # eMAG internal ID
    sku = Column(String(100), nullable=False, index=True)  # part_number in eMAG
    name = Column(String(500), nullable=False)

    # Account and source tracking
    account_type = Column(String(10), nullable=False, default="main")  # main/fbe
    source_account = Column(String(50), nullable=True)

    # Basic product information
    description = Column(Text, nullable=True)
    brand = Column(String(200), nullable=True)
    manufacturer = Column(String(200), nullable=True)

    # Pricing and inventory
    price = Column(Float, nullable=True)
    currency = Column(String(3), nullable=False, default="RON")
    stock_quantity = Column(Integer, nullable=True, default=0)

    # Categories and classification
    category_id = Column(String(50), nullable=True)
    emag_category_id = Column(String(50), nullable=True)
    emag_category_name = Column(String(200), nullable=True)

    # Product status and availability
    is_active = Column(Boolean, nullable=False, default=True)
    status = Column(String(50), nullable=True)  # active, inactive, pending, etc.

    # Images and media
    images = Column(JSONB, nullable=True)  # List of image URLs
    images_overwrite = Column(Boolean, nullable=False, default=False)

    # eMAG specific fields (v4.4.8)
    green_tax = Column(Float, nullable=True)  # RO only, includes TVA
    supply_lead_time = Column(Integer, nullable=True)  # 2,3,5,7,14,30,60,90,120 days

    # GPSR (General Product Safety Regulation) fields
    safety_information = Column(Text, nullable=True)
    manufacturer_info = Column(JSONB, nullable=True)  # [{name, address, email}]
    eu_representative = Column(JSONB, nullable=True)  # [{name, address, email}]

    # Product characteristics and attributes
    emag_characteristics = Column(JSONB, nullable=True)
    attributes = Column(JSONB, nullable=True)
    specifications = Column(JSONB, nullable=True)

    # Sync and metadata
    sync_status = Column(String(50), nullable=False, default="pending")
    last_synced_at = Column(DateTime, nullable=True)
    sync_error = Column(Text, nullable=True)
    sync_attempts = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    emag_created_at = Column(DateTime, nullable=True)
    emag_modified_at = Column(DateTime, nullable=True)

    # Raw eMAG data for debugging
    raw_emag_data = Column(JSONB, nullable=True)

    # eMAG API v4.4.9 - Validation and Ownership
    validation_status = Column(Integer, nullable=True)  # 0-12 (see eMAG API docs)
    validation_status_description = Column(String(255), nullable=True)
    translation_validation_status = Column(Integer, nullable=True)
    ownership = Column(Integer, nullable=True)  # 1 = can modify, 2 = cannot modify

    # eMAG API v4.4.9 - Marketplace Competition
    number_of_offers = Column(Integer, nullable=True)  # How many sellers have offers
    buy_button_rank = Column(
        Integer, nullable=True
    )  # Rank in "Add to cart" competition
    best_offer_sale_price = Column(Float, nullable=True)  # Best price in marketplace
    best_offer_recommended_price = Column(Float, nullable=True)

    # eMAG API v4.4.9 - Advanced Stock
    general_stock = Column(Integer, nullable=True)  # Sum across all warehouses
    estimated_stock = Column(
        Integer, nullable=True
    )  # Reserves for unacknowledged orders

    # eMAG API v4.4.9 - Measurements (in mm and g as per API spec)
    length_mm = Column(Float, nullable=True)  # Length in millimeters
    width_mm = Column(Float, nullable=True)  # Width in millimeters
    height_mm = Column(Float, nullable=True)  # Height in millimeters
    weight_g = Column(Float, nullable=True)  # Weight in grams

    # eMAG API v4.4.9 - Genius Program
    genius_eligibility = Column(Integer, nullable=True)  # 0=not eligible, 1=eligible
    genius_eligibility_type = Column(Integer, nullable=True)  # 1=Full, 2=EasyBox, 3=HD
    genius_computed = Column(
        Integer, nullable=True
    )  # 0=not active, 1=Full, 2=EasyBox, 3=HD

    # eMAG API v4.4.9 - Product Family (for grouping variants)
    family_id = Column(Integer, nullable=True)  # Your internal family ID
    family_name = Column(String(255), nullable=True)  # Family name
    family_type_id = Column(Integer, nullable=True)  # eMAG family_type ID

    # eMAG API v4.4.9 - Part Number Key (for attaching to existing products)
    part_number_key = Column(String(50), nullable=True, index=True)  # eMAG product key

    # eMAG API v4.4.9 - Additional Product Fields from Section 8
    url = Column(String(1024), nullable=True)  # Product URL on seller website
    source_language = Column(
        String(10), nullable=True
    )  # Content language (en_GB, ro_RO, etc.)
    warranty = Column(Integer, nullable=True)  # Warranty in months
    vat_id = Column(Integer, nullable=True)  # VAT rate ID
    currency_type = Column(String(3), nullable=True)  # Alternative currency (EUR, PLN)
    force_images_download = Column(
        Boolean, nullable=False, default=False
    )  # Force image redownload
    attachments = Column(
        JSONB, nullable=True
    )  # Product attachments (manuals, certificates)

    # eMAG API v4.4.9 - Offer Validation Status
    offer_validation_status = Column(Integer, nullable=True)  # 1=Valid, 2=Invalid price
    offer_validation_status_description = Column(String(255), nullable=True)

    # eMAG API v4.4.9 - Documentation Errors
    doc_errors = Column(JSONB, nullable=True)  # Documentation validation errors

    # eMAG API v4.4.9 - Vendor Category
    vendor_category_id = Column(
        String(50), nullable=True
    )  # Seller internal category ID

    # eMAG API v4.4.9 - EAN Dedicated Field (Section 8.6.6)
    ean = Column(
        JSONB, nullable=True
    )  # Array of EAN codes for fast lookup and validation

    # eMAG API v4.4.9 - GPSR Presence Flags (Section 8.10.5)
    has_manufacturer_info = Column(
        Boolean, nullable=False, default=False
    )  # Manufacturer info present
    has_eu_representative = Column(
        Boolean, nullable=False, default=False
    )  # EU representative present

    # eMAG API v4.4.9 - Validation Errors Storage (Section 8.10.3)
    validation_errors = Column(
        JSONB, nullable=True
    )  # Array of validation error objects
    translation_validation_errors = Column(
        JSONB, nullable=True
    )  # Array of translation errors

    # eMAG API v4.4.9 - Image Validation (Section 8.6.3)
    main_image_url = Column(String(1024), nullable=True)  # Quick access to main image
    images_validated = Column(
        Boolean, nullable=False, default=False
    )  # Images passed validation

    # eMAG API v4.4.9 - Characteristic Validation (Section 8.6.4)
    characteristics_validated = Column(
        Boolean, nullable=False, default=False
    )  # Characteristics validated
    characteristics_validation_errors = Column(
        JSONB, nullable=True
    )  # Characteristic validation errors

    # Relationships
    offers = relationship(
        "EmagProductOfferV2", back_populates="product", cascade="all, delete-orphan"
    )

    # Indexes and constraints
    __table_args__ = (
        Index("idx_emag_products_sku_account", "sku", "account_type"),
        Index("idx_emag_products_emag_id", "emag_id"),
        Index("idx_emag_products_sync_status", "sync_status"),
        Index("idx_emag_products_last_synced", "last_synced_at"),
        Index("idx_emag_products_category", "emag_category_id"),
        Index("idx_emag_products_ean", "ean"),  # Fast EAN lookup
        Index(
            "idx_emag_products_part_number_key", "part_number_key"
        ),  # Fast part_number_key lookup
        Index(
            "idx_emag_products_validation", "validation_status"
        ),  # Filter by validation status
        UniqueConstraint("sku", "account_type", name="uq_emag_products_sku_account"),
        CheckConstraint(
            "account_type IN ('main', 'fbe')", name="ck_emag_products_account_type"
        ),
        CheckConstraint(
            "currency IN ('RON', 'EUR', 'USD')", name="ck_emag_products_currency"
        ),
        CheckConstraint(
            "supply_lead_time IN (2,3,5,7,14,30,60,90,120)",
            name="ck_emag_products_lead_time",
        ),
    )


class EmagProductOfferV2(Base):
    """eMAG product offer model."""

    __tablename__ = "emag_product_offers_v2"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    emag_offer_id = Column(String(50), nullable=True, index=True)
    product_id = Column(
        UUID(as_uuid=True), ForeignKey("emag_products_v2.id"), nullable=False
    )

    # Offer identification
    sku = Column(String(100), nullable=False, index=True)
    account_type = Column(String(10), nullable=False, default="main")

    # Pricing
    price = Column(Float, nullable=False)
    original_price = Column(Float, nullable=True)
    sale_price = Column(Float, nullable=True)
    currency = Column(String(3), nullable=False, default="RON")

    # Inventory
    stock = Column(Integer, nullable=False, default=0)
    reserved_stock = Column(Integer, nullable=False, default=0)
    available_stock = Column(Integer, nullable=False, default=0)

    # Offer status
    status = Column(String(50), nullable=False, default="active")
    is_available = Column(Boolean, nullable=False, default=True)

    # eMAG API v4.4.9 - Offer Validation
    offer_validation_status = Column(Integer, nullable=True)  # 1=Valid, 2=Invalid price
    offer_validation_status_description = Column(String(255), nullable=True)

    # eMAG API v4.4.9 - VAT and Warranty
    vat_id = Column(Integer, nullable=True)  # VAT rate ID
    warranty = Column(Integer, nullable=True)  # Warranty in months

    # Shipping and handling
    handling_time = Column(Integer, nullable=True)  # days
    shipping_weight = Column(Float, nullable=True)  # kg
    shipping_size = Column(JSONB, nullable=True)  # {length, width, height}

    # Marketplace specific
    marketplace_status = Column(String(50), nullable=True)
    visibility = Column(String(50), nullable=False, default="visible")

    # Sync tracking
    sync_status = Column(String(50), nullable=False, default="pending")
    last_synced_at = Column(DateTime, nullable=True)
    sync_error = Column(Text, nullable=True)
    sync_attempts = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    emag_created_at = Column(DateTime, nullable=True)
    emag_modified_at = Column(DateTime, nullable=True)

    # Raw eMAG data
    raw_emag_data = Column(JSONB, nullable=True)

    # Relationships
    product = relationship("EmagProductV2", back_populates="offers")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_emag_offers_sku_account", "sku", "account_type"),
        Index("idx_emag_offers_emag_id", "emag_offer_id"),
        Index("idx_emag_offers_sync_status", "sync_status"),
        Index("idx_emag_offers_status", "status"),
        Index("idx_emag_offers_last_synced", "last_synced_at"),
        UniqueConstraint("sku", "account_type", name="uq_emag_offers_sku_account"),
        CheckConstraint(
            "account_type IN ('main', 'fbe')", name="ck_emag_offers_account_type"
        ),
        CheckConstraint(
            "currency IN ('RON', 'EUR', 'USD')", name="ck_emag_offers_currency"
        ),
        CheckConstraint("stock >= 0", name="ck_emag_offers_stock_positive"),
    )


class EmagOrder(Base):
    """eMAG order model with complete v4.4.9 fields."""

    __tablename__ = "emag_orders"
    __table_args__ = {"schema": "app"}

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    emag_order_id = Column(Integer, nullable=False, index=True)
    account_type = Column(String(10), nullable=False, default="main")

    # Order status and type
    status = Column(
        Integer, nullable=False
    )  # 0=canceled, 1=new, 2=in_progress, 3=prepared, 4=finalized, 5=returned
    status_name = Column(String(50), nullable=True)
    type = Column(Integer, nullable=True)  # 2=FBE, 3=FBS
    is_complete = Column(Boolean, nullable=False, default=False)

    # Customer information
    customer_id = Column(Integer, nullable=True)
    customer_name = Column(String(200), nullable=True)
    customer_email = Column(String(200), nullable=True)
    customer_phone = Column(String(50), nullable=True)

    # Financial information
    total_amount = Column(Float, nullable=False, default=0.0)
    currency = Column(String(3), nullable=False, default="RON")

    # Payment information
    payment_method = Column(
        String(50), nullable=True
    )  # COD, bank_transfer, online_card
    payment_mode_id = Column(
        Integer, nullable=True
    )  # 1=COD, 2=bank_transfer, 3=card_online
    detailed_payment_method = Column(String(100), nullable=True)
    payment_status = Column(Integer, nullable=True)  # 0=not_paid, 1=paid
    cashed_co = Column(Float, nullable=True)  # card online amount
    cashed_cod = Column(Float, nullable=True)  # COD amount

    # Shipping information
    delivery_mode = Column(String(50), nullable=True)  # courier, pickup
    shipping_tax = Column(Float, nullable=True)
    shipping_tax_voucher_split = Column(
        JSONB, nullable=True
    )  # Voucher split for shipping
    shipping_address = Column(JSONB, nullable=True)
    billing_address = Column(JSONB, nullable=True)

    # Delivery details
    locker_id = Column(String(50), nullable=True)
    locker_name = Column(String(200), nullable=True)

    # AWB and tracking
    awb_number = Column(String(100), nullable=True)
    courier_name = Column(String(100), nullable=True)

    # Documents
    invoice_url = Column(Text, nullable=True)
    invoice_uploaded_at = Column(DateTime, nullable=True)

    # Order items and vouchers
    products = Column(JSONB, nullable=True)  # Order line items
    vouchers = Column(JSONB, nullable=True)  # Applied vouchers
    attachments = Column(JSONB, nullable=True)  # Invoices, warranties, etc.

    # Special flags
    is_storno = Column(Boolean, nullable=False, default=False)

    # Order lifecycle timestamps
    acknowledged_at = Column(DateTime, nullable=True)
    finalized_at = Column(DateTime, nullable=True)

    # Sync tracking
    sync_status = Column(String(50), nullable=False, default="pending")
    last_synced_at = Column(DateTime, nullable=True)
    sync_error = Column(Text, nullable=True)
    sync_attempts = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    order_date = Column(DateTime, nullable=True)  # eMAG order date
    emag_created_at = Column(DateTime, nullable=True)
    emag_modified_at = Column(DateTime, nullable=True)

    # Raw eMAG data
    raw_emag_data = Column(JSONB, nullable=True)

    # Indexes and constraints
    __table_args__ = (
        Index("idx_emag_orders_emag_id_account", "emag_order_id", "account_type"),
        Index("idx_emag_orders_account", "account_type"),
        Index("idx_emag_orders_status", "status"),
        Index("idx_emag_orders_sync_status", "sync_status"),
        Index("idx_emag_orders_order_date", "order_date"),
        Index("idx_emag_orders_customer_email", "customer_email"),
        UniqueConstraint(
            "emag_order_id", "account_type", name="uq_emag_orders_id_account"
        ),
        CheckConstraint(
            "account_type IN ('main', 'fbe')", name="ck_emag_orders_account_type"
        ),
        CheckConstraint("status IN (0,1,2,3,4,5)", name="ck_emag_orders_status"),
        CheckConstraint("type IN (2,3)", name="ck_emag_orders_type"),
        {"schema": "app"},
    )


class EmagSyncLog(Base):
    """eMAG synchronization log for tracking sync operations."""

    __tablename__ = "emag_sync_logs"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Sync operation details
    sync_type = Column(String(50), nullable=False)  # products, offers, orders
    account_type = Column(String(10), nullable=False)
    operation = Column(
        String(50), nullable=False
    )  # full_sync, incremental_sync, manual_sync

    # Sync parameters
    sync_params = Column(JSONB, nullable=True)  # max_pages, filters, etc.

    # Sync results
    status = Column(
        String(50), nullable=False, default="running"
    )  # running, completed, failed, partial
    total_items = Column(Integer, nullable=False, default=0)
    processed_items = Column(Integer, nullable=False, default=0)
    created_items = Column(Integer, nullable=False, default=0)
    updated_items = Column(Integer, nullable=False, default=0)
    failed_items = Column(Integer, nullable=False, default=0)

    # Error tracking
    errors = Column(JSONB, nullable=True)  # List of errors
    warnings = Column(JSONB, nullable=True)  # List of warnings

    # Performance metrics
    duration_seconds = Column(Float, nullable=True)
    pages_processed = Column(Integer, nullable=False, default=0)
    api_requests_made = Column(Integer, nullable=False, default=0)
    rate_limit_hits = Column(Integer, nullable=False, default=0)

    # Timestamps
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Additional metadata
    triggered_by = Column(String(100), nullable=True)  # user_id, scheduler, api
    sync_version = Column(String(20), nullable=True)  # API version used

    # Standard timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Indexes
    __table_args__ = (
        Index("idx_emag_sync_logs_type_account", "sync_type", "account_type"),
        Index("idx_emag_sync_logs_status", "status"),
        Index("idx_emag_sync_logs_started_at", "started_at"),
        CheckConstraint(
            "account_type IN ('main', 'fbe')", name="ck_emag_sync_logs_account_type"
        ),
        CheckConstraint(
            "sync_type IN ('products', 'offers', 'orders')",
            name="ck_emag_sync_logs_sync_type",
        ),
        CheckConstraint(
            "status IN ('running', 'completed', 'failed', 'partial')",
            name="ck_emag_sync_logs_status",
        ),
    )


class EmagCategory(Base):
    """eMAG category model with characteristics and family types."""

    __tablename__ = "emag_categories"

    # Primary identification
    id = Column(Integer, primary_key=True)  # eMAG category ID
    name = Column(String(255), nullable=False)

    # Category properties
    is_allowed = Column(Integer, nullable=False, default=0)  # 0/1 - seller can post
    parent_id = Column(Integer, nullable=True)
    is_ean_mandatory = Column(Integer, nullable=False, default=0)  # 0/1
    is_warranty_mandatory = Column(Integer, nullable=False, default=0)  # 0/1

    # Characteristics and family types (JSONB for flexibility)
    characteristics = Column(JSONB, nullable=True)  # List of characteristic objects
    family_types = Column(JSONB, nullable=True)  # List of family type objects

    # eMAG API v4.4.9 - Detailed characteristic info (Section 8.3.3)
    characteristics_detailed = Column(
        JSONB, nullable=True
    )  # Full characteristic objects with type_id, allow_new_value, tags

    # eMAG API v4.4.9 - Family type details (Section 8.3.5)
    family_types_detailed = Column(
        JSONB, nullable=True
    )  # Full family type objects with characteristic_family_type_id, is_foldable

    # Metadata
    language = Column(String(5), nullable=False, default="ro")  # ro, en, hu, bg, etc.

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_synced_at = Column(DateTime, nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_emag_categories_parent", "parent_id"),
        Index("idx_emag_categories_allowed", "is_allowed"),
        Index("idx_emag_categories_name", "name"),
    )


class EmagVatRate(Base):
    """eMAG VAT rate model."""

    __tablename__ = "emag_vat_rates"

    # Primary identification
    id = Column(Integer, primary_key=True)  # eMAG VAT ID
    name = Column(String(100), nullable=False)
    rate = Column(Float, nullable=False)  # VAT percentage

    # Metadata
    country = Column(String(2), nullable=False, default="RO")  # RO, BG, HU
    is_active = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_synced_at = Column(DateTime, nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_emag_vat_country", "country"),
        Index("idx_emag_vat_active", "is_active"),
    )


class EmagHandlingTime(Base):
    """eMAG handling time values model."""

    __tablename__ = "emag_handling_times"

    # Primary identification
    id = Column(Integer, primary_key=True)  # eMAG handling time ID
    value = Column(Integer, nullable=False)  # Days
    name = Column(String(100), nullable=False)

    # Metadata
    is_active = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_synced_at = Column(DateTime, nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_emag_handling_time_value", "value"),
        Index("idx_emag_handling_time_active", "is_active"),
    )


class EmagSyncProgress(Base):
    """Real-time sync progress tracking."""

    __tablename__ = "emag_sync_progress"

    # Explicitly exclude created_at inherited from Base (table doesn't have this column)
    created_at = None  # type: ignore

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_log_id = Column(
        UUID(as_uuid=True), ForeignKey("emag_sync_logs.id"), nullable=False
    )

    # Progress details
    current_page = Column(Integer, nullable=False, default=1)
    total_pages = Column(Integer, nullable=True)
    current_item = Column(Integer, nullable=False, default=0)
    total_items = Column(Integer, nullable=True)

    # Progress percentage
    percentage_complete = Column(Float, nullable=False, default=0.0)

    # Current operation
    current_operation = Column(String(200), nullable=True)
    current_sku = Column(String(100), nullable=True)

    # Performance metrics
    items_per_second = Column(Float, nullable=True)
    estimated_completion = Column(DateTime, nullable=True)

    # Status
    is_active = Column(Boolean, nullable=False, default=True)

    # Timestamps
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    sync_log = relationship("EmagSyncLog")

    # Indexes
    __table_args__ = (
        Index("idx_emag_sync_progress_log_id", "sync_log_id"),
        Index("idx_emag_sync_progress_active", "is_active"),
        CheckConstraint(
            "percentage_complete >= 0 AND percentage_complete <= 100",
            name="ck_emag_sync_progress_percentage",
        ),
    )
