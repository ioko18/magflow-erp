"""RMA (Returns Management) models for MagFlow ERP."""

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


class ReturnStatus(str, enum.Enum):
    """Status of a return request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ReturnReason(str, enum.Enum):
    """Reason for return request."""

    DEFECTIVE_PRODUCT = "defective_product"
    WRONG_ITEM = "wrong_item"
    DAMAGED_IN_TRANSIT = "damaged_in_transit"
    CUSTOMER_DISSATISFACTION = "customer_dissatisfaction"
    LATE_DELIVERY = "late_delivery"
    OTHER = "other"


class RefundMethod(str, enum.Enum):
    """Method for processing refunds."""

    ORIGINAL_PAYMENT = "original_payment"
    STORE_CREDIT = "store_credit"
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"


class EmagReturnStatus(str, enum.Enum):
    """eMAG-specific return status."""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ReturnRequest(Base, TimestampMixin):
    """Return request model for managing product returns."""

    __tablename__ = "return_requests"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    return_number: Mapped[str] = mapped_column(
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
    customer_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Return details
    status: Mapped[ReturnStatus] = mapped_column(
        SQLEnum(ReturnStatus),
        default=ReturnStatus.PENDING,
    )
    reason: Mapped[ReturnReason] = mapped_column(SQLEnum(ReturnReason), nullable=False)
    reason_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Items being returned
    items: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )  # JSON string of items

    # Refund information
    refund_amount: Mapped[float] = mapped_column(Float, default=0.0)
    refund_method: Mapped[RefundMethod] = mapped_column(
        SQLEnum(RefundMethod),
        default=RefundMethod.ORIGINAL_PAYMENT,
    )
    refund_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    refund_processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    # eMAG integration
    emag_return_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    emag_status: Mapped[Optional[EmagReturnStatus]] = mapped_column(
        SQLEnum(EmagReturnStatus),
        nullable=True,
    )
    account_type: Mapped[str] = mapped_column(String(10), default="main")  # main/fbe

    # Processing information
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

    # Notes and attachments
    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    customer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    return_items: Mapped[List["ReturnItem"]] = relationship(
        "ReturnItem",
        back_populates="return_request",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ReturnRequest {self.return_number}: {self.status}>"


class ReturnItem(Base, TimestampMixin):
    """Individual items within a return request."""

    __tablename__ = "return_items"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    return_request_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.return_requests.id"),
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

    # Condition
    condition: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # new, used, damaged
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Status
    status: Mapped[ReturnStatus] = mapped_column(
        SQLEnum(ReturnStatus),
        default=ReturnStatus.PENDING,
    )
    approved_quantity: Mapped[int] = mapped_column(Integer, default=0)
    rejected_quantity: Mapped[int] = mapped_column(Integer, default=0)

    # Refund
    refund_amount: Mapped[float] = mapped_column(Float, default=0.0)
    refund_processed: Mapped[bool] = mapped_column(Boolean, default=False)

    # eMAG integration
    emag_item_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    return_request: Mapped["ReturnRequest"] = relationship(
        "ReturnRequest",
        back_populates="return_items",
    )

    def __repr__(self) -> str:
        return f"<ReturnItem {self.sku}: {self.quantity} units>"


class RefundTransaction(Base, TimestampMixin):
    """Tracks refund transactions for returns."""

    __tablename__ = "refund_transactions"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    transaction_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    # Related entities
    return_request_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("app.return_requests.id"),
        nullable=True,
    )
    order_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Transaction details
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RON")
    method: Mapped[RefundMethod] = mapped_column(SQLEnum(RefundMethod), nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )  # pending, processing, completed, failed
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Payment details
    payment_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gateway_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<RefundTransaction {self.transaction_id}: {self.amount} {self.currency}>"
        )


class EmagReturnIntegration(Base, TimestampMixin):
    """Tracks integration with eMAG RMA system."""

    __tablename__ = "emag_return_integrations"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    return_request_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.return_requests.id"),
        nullable=False,
    )

    # eMAG RMA details
    emag_return_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    emag_status: Mapped[EmagReturnStatus] = mapped_column(
        SQLEnum(EmagReturnStatus),
        nullable=False,
    )

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
        return f"<EmagReturnIntegration {self.emag_return_id}: {self.emag_status}>"
