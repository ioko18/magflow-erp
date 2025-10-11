"""Product history tracking models for audit and change tracking."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.user import User

from app.db.base_class import Base


class ProductSKUHistory(Base):
    """Track SKU changes for products.

    This model maintains a complete history of SKU changes for audit purposes.
    Whenever a product's SKU is changed, the old SKU is recorded here.
    """

    __tablename__ = "product_sku_history"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Product reference
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the product",
    )

    # SKU tracking
    old_sku: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="Previous SKU value"
    )
    new_sku: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="New SKU value"
    )

    # Change metadata
    changed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="When the change occurred",
    )
    changed_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("app.users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who made the change",
    )
    change_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Reason for the change (optional)"
    )

    # Additional context
    ip_address: Mapped[str | None] = mapped_column(
        String(45), nullable=True, comment="IP address of the user who made the change"
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="User agent string"
    )

    # Relationships
    product: Mapped["Product"] = relationship(
        "Product", back_populates="sku_history", lazy="selectin"
    )
    changed_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[changed_by_id], lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<ProductSKUHistory product_id={self.product_id} {self.old_sku} -> {self.new_sku}>"


class ProductChangeLog(Base):
    """Track all changes to product fields for comprehensive audit trail.

    This model records all field changes for products, not just SKU changes.
    Useful for compliance, debugging, and understanding product evolution.
    """

    __tablename__ = "product_change_log"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Product reference
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the product",
    )

    # Field tracking
    field_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Name of the field that changed",
    )
    old_value: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Previous value (JSON for complex types)"
    )
    new_value: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="New value (JSON for complex types)"
    )

    # Change metadata
    changed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="When the change occurred",
    )
    changed_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("app.users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who made the change",
    )
    change_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="update",
        comment="Type of change: create, update, delete",
    )

    # Additional context
    ip_address: Mapped[str | None] = mapped_column(
        String(45), nullable=True, comment="IP address of the user who made the change"
    )

    # Relationships
    product: Mapped["Product"] = relationship(
        "Product", back_populates="change_logs", lazy="selectin"
    )
    changed_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[changed_by_id], lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<ProductChangeLog product_id={self.product_id} field={self.field_name}>"
        )
