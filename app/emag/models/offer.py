from __future__ import annotations

from sqlalchemy import JSON, Column, DateTime, Integer, Numeric, String, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class EmagOffer(Base):
    """SQLAlchemy model representing an eMAG product offer.

    The table stores the raw payload for debugging and the most important
    fields required by the ERP (price, stock, brand, etc.).
    """

    __tablename__ = "emag_offers"

    # Primary key – eMAG product ID (string)
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    brand = Column(String, nullable=True)
    category = Column(String, nullable=True)
    price = Column(Numeric(10, 2), nullable=True)
    sale_price = Column(Numeric(10, 2), nullable=True)
    stock = Column(Integer, nullable=True)
    warranty_months = Column(Integer, nullable=True)
    ean = Column(String, nullable=True)
    raw_payload = Column(JSON, nullable=False)
    last_synced = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
