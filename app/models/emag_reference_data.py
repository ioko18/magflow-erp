"""
eMAG Reference Data Models

Models for caching eMAG reference data (categories, VAT rates, handling times).
This data changes infrequently and is cached to improve performance.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base_class import Base


class EmagCategory(Base):
    """
    eMAG Category cache table.

    Stores category information including characteristics and family types.
    Cached for 24 hours to reduce API calls.
    """

    __tablename__ = "emag_categories"
    __table_args__ = (
        Index("idx_emag_categories_is_allowed", "is_allowed"),
        Index("idx_emag_categories_parent_id", "parent_id"),
        Index("idx_emag_categories_language", "language"),
        {"schema": "app"},
    )

    # Primary key - eMAG category ID
    id = Column(Integer, primary_key=True, autoincrement=False)

    # Basic category info
    name = Column(String(255), nullable=False)
    is_allowed = Column(
        Integer,
        nullable=False,
        default=0,
        comment="1 if seller can post in this category",
    )
    parent_id = Column(Integer, nullable=True, comment="Parent category ID")

    # Mandatory fields flags
    is_ean_mandatory = Column(Integer, nullable=False, default=0)
    is_warranty_mandatory = Column(Integer, nullable=False, default=0)

    # Complex data stored as JSONB
    characteristics = Column(
        JSONB, nullable=True, comment="Category characteristics with mandatory flags"
    )
    family_types = Column(
        JSONB, nullable=True, comment="Family types for product variants"
    )

    # Language and metadata
    language = Column(
        String(5),
        nullable=False,
        default="ro",
        comment="Language code: en, ro, hu, bg, pl, gr, de",
    )

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None))
    updated_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    last_synced_at = Column(
        DateTime, nullable=True, comment="Last time synced from eMAG API"
    )

    def __repr__(self):
        return f"<EmagCategory(id={self.id}, name='{self.name}', is_allowed={self.is_allowed})>"


class EmagVatRate(Base):
    """
    eMAG VAT Rate cache table.

    Stores available VAT rates from eMAG.
    Cached for 7 days as this data rarely changes.
    """

    __tablename__ = "emag_vat_rates"
    __table_args__ = (
        Index("idx_emag_vat_rates_is_active", "is_active"),
        Index("idx_emag_vat_rates_country", "country"),
        {"schema": "app"},
    )

    # Primary key - eMAG VAT rate ID
    id = Column(Integer, primary_key=True, autoincrement=False)

    # VAT rate info
    name = Column(
        String(100), nullable=False, comment="VAT rate name (e.g., 'Standard Rate 19%')"
    )
    rate = Column(
        Float, nullable=False, comment="VAT rate as decimal (e.g., 0.19 for 19%)"
    )
    country = Column(String(2), nullable=False, default="RO", comment="Country code")

    # Status
    is_active = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None))
    updated_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    last_synced_at = Column(
        DateTime, nullable=True, comment="Last time synced from eMAG API"
    )

    def __repr__(self):
        return f"<EmagVatRate(id={self.id}, name='{self.name}', rate={self.rate})>"


class EmagHandlingTime(Base):
    """
    eMAG Handling Time cache table.

    Stores available handling time values from eMAG.
    Cached for 7 days as this data rarely changes.
    """

    __tablename__ = "emag_handling_times"
    __table_args__ = (
        Index("idx_emag_handling_times_value", "value"),
        Index("idx_emag_handling_times_is_active", "is_active"),
        {"schema": "app"},
    )

    # Primary key - eMAG handling time ID
    id = Column(Integer, primary_key=True, autoincrement=False)

    # Handling time info
    value = Column(
        Integer, nullable=False, comment="Number of days from order to dispatch"
    )
    name = Column(String(100), nullable=False, comment="Handling time name")

    # Status
    is_active = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None))
    updated_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    last_synced_at = Column(
        DateTime, nullable=True, comment="Last time synced from eMAG API"
    )

    def __repr__(self):
        return (
            f"<EmagHandlingTime(id={self.id}, value={self.value}, name='{self.name}')>"
        )
