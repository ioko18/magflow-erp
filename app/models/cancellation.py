"""Order Cancellation models for MagFlow ERP."""

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class CancellationStatus(str, enum.Enum):
    """Status of a cancellation request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CancellationReason(str, enum.Enum):
    """Reason for order cancellation."""

    CUSTOMER_REQUEST = "customer_request"
    PAYMENT_FAILED = "payment_failed"
    INVENTORY_UNAVAILABLE = "inventory_unavailable"
    SHIPPING_DELAY = "shipping_delay"
    FRAUD_SUSPECTED = "fraud_suspected"
    ADMINISTRATIVE = "administrative"
    OTHER = "other"


class RefundStatus(str, enum.Enum):
    """Status of refund processing."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class CancellationRequest(Base, TimestampMixin):
    """Order cancellation request model."""

    __tablename__ = "cancellation_requests"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cancellation_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    # Order information
    order_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    emag_order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Customer information
    customer_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Cancellation details
    status: Mapped[CancellationStatus] = mapped_column(
        SQLEnum(CancellationStatus),
        default=CancellationStatus.PENDING,
    )
    reason: Mapped[CancellationReason] = mapped_column(
        SQLEnum(CancellationReason),
        nullable=False,
    )
    reason_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Financial information
    cancellation_fee: Mapped[float] = mapped_column(Float, default=0.0)
    refund_amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="RON")

    # Refund processing
    refund_status: Mapped[RefundStatus] = mapped_column(
        SQLEnum(RefundStatus),
        default=RefundStatus.PENDING,
    )
    refund_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    refund_processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    # Stock restoration
    stock_restored: Mapped[bool] = mapped_column(Boolean, default=False)
    stock_restored_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    # eMAG integration
    emag_cancellation_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    account_type: Mapped[str] = mapped_column(String(10), default="main")  # main/fbe

    # Processing information
    requested_by: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )  # user_id or customer_id
    approved_by: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )  # user_id
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    processed_by: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )  # user_id
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Notes and communication
    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    customer_communication: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Items affected by cancellation
    affected_items: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )  # JSON string of items

    # Relationships
    cancellation_items: Mapped[List["CancellationItem"]] = relationship(
        "CancellationItem",
        back_populates="cancellation_request",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<CancellationRequest {self.cancellation_number}: {self.status}>"


class CancellationItem(Base, TimestampMixin):
    """Individual items affected by order cancellation."""

    __tablename__ = "cancellation_items"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cancellation_request_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.cancellation_requests.id"),
        nullable=False,
    )

    # Item details
    product_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Pricing
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)

    # Stock restoration
    stock_to_restore: Mapped[int] = mapped_column(Integer, default=0)
    stock_restored: Mapped[bool] = mapped_column(Boolean, default=False)

    # Cancellation details
    cancellation_reason: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    refund_amount: Mapped[float] = mapped_column(Float, default=0.0)

    # eMAG integration
    emag_item_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    cancellation_request: Mapped["CancellationRequest"] = relationship(
        "CancellationRequest",
        back_populates="cancellation_items",
    )

    def __repr__(self) -> str:
        return f"<CancellationItem {self.sku}: {self.quantity} units>"


class CancellationRefund(Base, TimestampMixin):
    """Tracks refunds processed for cancellations."""

    __tablename__ = "cancellation_refunds"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    refund_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    # Related entities
    cancellation_request_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("app.cancellation_requests.id"),
        nullable=True,
    )
    order_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Refund details
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RON")
    refund_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # original_payment, store_credit, etc.

    # Payment information
    payment_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gateway_transaction_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )  # pending, processing, completed, failed
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Additional information
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gateway_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<CancellationRefund {self.refund_id}: {self.amount} {self.currency}>"


class EmagCancellationIntegration(Base, TimestampMixin):
    """Tracks integration with eMAG cancellation system."""

    __tablename__ = "emag_cancellation_integrations"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cancellation_request_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.cancellation_requests.id"),
        nullable=False,
    )

    # eMAG cancellation details
    emag_cancellation_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    emag_status: Mapped[str] = mapped_column(String(50), nullable=False)

    # Sync information
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sync_attempts: Mapped[int] = mapped_column(Integer, default=0)

    # eMAG response data
    emag_response: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )  # JSON response from eMAG
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Account type
    account_type: Mapped[str] = mapped_column(String(10), default="main")  # main/fbe

    def __repr__(self) -> str:
        return f"<EmagCancellationIntegration {self.emag_cancellation_id}: {self.emag_status}>"
