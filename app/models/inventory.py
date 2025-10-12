"""Inventory Management models."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.product import Product

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class Warehouse(Base, TimestampMixin):
    """Warehouse model for inventory management."""

    __tablename__ = "warehouses"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(50), nullable=True)
    country: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True)

    # Relationships
    inventory_items: Mapped[list["InventoryItem"]] = relationship(
        "InventoryItem",
        back_populates="warehouse",
    )
    stock_movements: Mapped[list["StockMovement"]] = relationship(
        "StockMovement",
        back_populates="warehouse",
    )

    def __repr__(self) -> str:
        return f"<Warehouse {self.name} ({self.code})>"


class InventoryItem(Base, TimestampMixin):
    """Inventory item model for tracking stock levels."""

    __tablename__ = "inventory_items"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.products.id"),
        nullable=False,
        index=True,
    )
    warehouse_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.warehouses.id"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    reserved_quantity: Mapped[int] = mapped_column(Integer, default=0)
    available_quantity: Mapped[int] = mapped_column(Integer, default=0)
    minimum_stock: Mapped[int] = mapped_column(Integer, default=0)
    maximum_stock: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reorder_point: Mapped[int] = mapped_column(Integer, default=0)
    manual_reorder_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    batch_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True)

    # Relationships
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="inventory_items",
    )
    warehouse: Mapped["Warehouse"] = relationship(
        "Warehouse",
        back_populates="inventory_items",
    )
    stock_movements: Mapped[list["StockMovement"]] = relationship(
        "StockMovement",
        back_populates="inventory_item",
    )

    def __repr__(self) -> str:
        return f"<InventoryItem product:{self.product_id} warehouse:{self.warehouse_id} qty:{self.quantity}>"


class StockMovement(Base, TimestampMixin):
    """Stock movement model for tracking inventory changes."""

    __tablename__ = "stock_movements"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    inventory_item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.inventory_items.id"),
        nullable=False,
        index=True,
    )
    warehouse_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.warehouses.id"),
        nullable=False,
        index=True,
    )
    movement_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # in, out, transfer, adjustment
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    new_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # order, purchase, adjustment
    reference_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )  # user_id
    unit_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    inventory_item: Mapped["InventoryItem"] = relationship(
        "InventoryItem",
        back_populates="stock_movements",
    )
    warehouse: Mapped["Warehouse"] = relationship(
        "Warehouse",
        back_populates="stock_movements",
    )

    def __repr__(self) -> str:
        return f"<StockMovement {self.movement_type} qty:{self.quantity}>"


class StockReservation(Base, TimestampMixin):
    """Stock reservation model for order fulfillment."""

    __tablename__ = "stock_reservations"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    inventory_item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.inventory_items.id"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )  # sales order ID
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    inventory_item: Mapped["InventoryItem"] = relationship("InventoryItem")

    def __repr__(self) -> str:
        return f"<StockReservation order:{self.order_id} qty:{self.quantity}>"


class StockTransfer(Base, TimestampMixin):
    """Stock transfer model for moving inventory between warehouses."""

    __tablename__ = "stock_transfers"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    transfer_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )
    from_warehouse_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.warehouses.id"),
        nullable=False,
        index=True,
    )
    to_warehouse_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.warehouses.id"),
        nullable=False,
        index=True,
    )
    inventory_item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("app.inventory_items.id"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    transfer_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expected_arrival_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
    )  # pending, in_transit, completed, cancelled
    tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    from_warehouse: Mapped["Warehouse"] = relationship(
        "Warehouse",
        foreign_keys=[from_warehouse_id],
    )
    to_warehouse: Mapped["Warehouse"] = relationship(
        "Warehouse",
        foreign_keys=[to_warehouse_id],
    )
    inventory_item: Mapped["InventoryItem"] = relationship("InventoryItem")

    def __repr__(self) -> str:
        return f"<StockTransfer {self.transfer_number} {self.from_warehouse_id}->{self.to_warehouse_id}>"
