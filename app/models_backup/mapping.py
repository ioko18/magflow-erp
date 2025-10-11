"""Database models for eMAG integration mappings."""

from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class MappingStatus(str, Enum):
    """Status of a mapping entry."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    DEPRECATED = "deprecated"


class MappingType(str, Enum):
    """Types of mappings supported."""

    PRODUCT_ID = "product_id"
    CATEGORY_ID = "category_id"
    BRAND_ID = "brand_id"
    CHARACTERISTIC_ID = "characteristic_id"


class ProductMapping(Base, TimestampMixin):
    """Mapping between internal product ID and eMAG product ID."""

    __tablename__ = "emag_product_mappings"
    __table_args__ = {"schema": "app"}

    id = Column(Integer, primary_key=True, index=True)
    internal_id = Column(String(100), nullable=False, index=True)
    emag_id = Column(String(100), nullable=False, index=True)
    emag_offer_id = Column(Integer, nullable=True, index=True)
    category_id = Column(
        Integer,
        ForeignKey("app.emag_category_mappings.id"),
        nullable=True,
    )
    brand_id = Column(Integer, ForeignKey("app.emag_brand_mappings.id"), nullable=True)
    status = Column(
        SQLEnum(MappingStatus),
        default=MappingStatus.ACTIVE,
        nullable=False,
    )
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    sync_errors = Column(JSON, default=list, nullable=False)
    metadata_ = Column("metadata", JSONB, default=dict, nullable=False)

    # Relationships
    field_mappings = relationship(
        "ProductFieldMapping",
        back_populates="product_mapping",
        cascade="all, delete-orphan",
    )
    sync_history = relationship(
        "SyncHistory",
        back_populates="product_mapping",
        cascade="all, delete-orphan",
    )
    category = relationship("CategoryMapping", back_populates="products")
    brand = relationship("BrandMapping", back_populates="products")

    def __repr__(self):
        return f"<ProductMapping {self.internal_id} -> {self.emag_id}>"


class CategoryMapping(Base, TimestampMixin):
    """Mapping between internal category ID and eMAG category ID."""

    __tablename__ = "emag_category_mappings"
    __table_args__ = {"schema": "app"}

    id = Column(Integer, primary_key=True, index=True)
    internal_id = Column(String(100), nullable=False, index=True)
    emag_id = Column(Integer, nullable=False, index=True)
    internal_name = Column(String(255), nullable=False)
    emag_name = Column(String(255), nullable=False)
    status = Column(
        SQLEnum(MappingStatus),
        default=MappingStatus.ACTIVE,
        nullable=False,
    )
    parent_id = Column(
        Integer,
        ForeignKey("app.emag_category_mappings.id"),
        nullable=True,
    )
    metadata_ = Column("metadata", JSONB, default=dict, nullable=False)

    # Relationships
    parent = relationship("CategoryMapping", remote_side=[id], backref="children")
    products = relationship("ProductMapping", back_populates="category", lazy="dynamic")

    def __repr__(self):
        return f"<CategoryMapping {self.internal_name} -> {self.emag_name}>"


class BrandMapping(Base, TimestampMixin):
    """Mapping between internal brand ID and eMAG brand ID."""

    __tablename__ = "emag_brand_mappings"
    __table_args__ = {"schema": "app"}

    id = Column(Integer, primary_key=True, index=True)
    internal_id = Column(String(100), nullable=False, index=True)
    emag_id = Column(Integer, nullable=False, index=True)
    internal_name = Column(String(255), nullable=False)
    emag_name = Column(String(255), nullable=False)
    status = Column(
        SQLEnum(MappingStatus),
        default=MappingStatus.ACTIVE,
        nullable=False,
    )
    metadata_ = Column("metadata", JSONB, default=dict, nullable=False)

    # Relationships
    products = relationship("ProductMapping", back_populates="brand", lazy="dynamic")

    def __repr__(self):
        return f"<BrandMapping {self.internal_name} -> {self.emag_name}>"


class CharacteristicMapping(Base, TimestampMixin):
    """Mapping between internal characteristic and eMAG characteristic."""

    __tablename__ = "emag_characteristic_mappings"
    __table_args__ = {"schema": "app"}

    id = Column(Integer, primary_key=True, index=True)
    internal_id = Column(String(100), nullable=False, index=True)
    emag_id = Column(Integer, nullable=False, index=True)
    internal_name = Column(String(255), nullable=False)
    emag_name = Column(String(255), nullable=False)
    category_id = Column(Integer, nullable=False, index=True)
    status = Column(
        SQLEnum(MappingStatus),
        default=MappingStatus.ACTIVE,
        nullable=False,
    )
    metadata_ = Column("metadata", JSONB, default=dict, nullable=False)

    def __repr__(self):
        return f"<CharacteristicMapping {self.internal_name} -> {self.emag_name}>"


class ProductFieldMapping(Base, TimestampMixin):
    """Mapping configuration for product fields."""

    __tablename__ = "emag_field_mappings"
    __table_args__ = {"schema": "app"}

    id = Column(Integer, primary_key=True, index=True)
    product_mapping_id = Column(
        Integer,
        ForeignKey("app.emag_product_mappings.id"),
        nullable=False,
    )
    internal_field = Column(String(100), nullable=False, index=True)
    emag_field = Column(String(100), nullable=False, index=True)
    transform_function = Column(String(255), nullable=True)
    default_value = Column(Text, nullable=True)
    is_required = Column(Boolean, default=True, nullable=False)
    validation_rules = Column(JSONB, default=dict, nullable=False)
    metadata_ = Column("metadata", JSONB, default=dict, nullable=False)

    # Relationships
    product_mapping = relationship("ProductMapping", back_populates="field_mappings")

    def __repr__(self):
        return f"<ProductFieldMapping {self.internal_field} -> {self.emag_field}>"


class SyncHistory(Base, TimestampMixin):
    """Tracks sync operations for auditing and monitoring."""

    __tablename__ = "emag_sync_history"
    __table_args__ = {"schema": "app"}

    id = Column(Integer, primary_key=True, index=True)
    product_mapping_id = Column(
        Integer,
        ForeignKey("app.emag_product_mappings.id"),
        nullable=True,
    )
    operation = Column(
        String(50),
        nullable=False,
    )  # e.g., 'create', 'update', 'delete', 'sync'
    status = Column(String(50), nullable=False)  # 'success', 'partial', 'failed'
    items_processed = Column(Integer, default=0, nullable=False)
    items_succeeded = Column(Integer, default=0, nullable=False)
    items_failed = Column(Integer, default=0, nullable=False)
    duration_seconds = Column(Float, nullable=True)
    error_count = Column(Integer, default=0, nullable=False)
    errors = Column(JSON, default=list, nullable=False)
    metadata_ = Column("metadata", JSONB, default=dict, nullable=False)

    # Relationships
    product_mapping = relationship("ProductMapping", back_populates="sync_history")

    def __repr__(self):
        return f"<SyncHistory {self.operation} - {self.status}>"


class MappingConfiguration(Base, TimestampMixin):
    """Stores configuration for mapping operations."""

    __tablename__ = "emag_mapping_configs"
    __table_args__ = {"schema": "app"}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    config = Column(JSONB, nullable=False)  # Stores the full configuration
    is_active = Column(Boolean, default=True, nullable=False)
    version = Column(String(50), nullable=False, default="1.0.0")
    description = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSONB, default=dict, nullable=False)

    def __repr__(self):
        return f"<MappingConfiguration {self.name} v{self.version}>"
