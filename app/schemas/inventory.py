"""Pydantic schemas for inventory management."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class WarehouseStatus(str, Enum):
    """Warehouse status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class WarehouseBase(BaseModel):
    """Base warehouse schema."""

    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=50)
    country: Optional[str] = Field(None, max_length=50)
    is_active: bool = True


class WarehouseCreate(WarehouseBase):
    """Schema for creating a warehouse."""


class WarehouseUpdate(BaseModel):
    """Schema for updating a warehouse."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=1, max_length=20)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=50)
    country: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class WarehouseInDBBase(WarehouseBase):
    """Base schema for warehouse data in database."""

    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Warehouse(WarehouseInDBBase):
    """Schema for warehouse data returned to clients."""


class InventoryItemBase(BaseModel):
    """Base inventory item schema."""

    product_id: int
    warehouse_id: int
    quantity: int = 0
    reserved_quantity: int = 0
    available_quantity: int = 0
    minimum_stock: int = 0
    maximum_stock: Optional[int] = None
    reorder_point: int = 0
    unit_cost: Optional[float] = None
    location: Optional[str] = Field(None, max_length=100)
    batch_number: Optional[str] = Field(None, max_length=50)
    expiry_date: Optional[datetime] = None
    is_active: bool = True


class InventoryItemCreate(InventoryItemBase):
    """Schema for creating an inventory item."""


class InventoryItemUpdate(BaseModel):
    """Schema for updating an inventory item."""

    quantity: Optional[int] = None
    reserved_quantity: Optional[int] = None
    minimum_stock: Optional[int] = None
    maximum_stock: Optional[int] = None
    reorder_point: Optional[int] = None
    unit_cost: Optional[float] = None
    location: Optional[str] = Field(None, max_length=100)
    batch_number: Optional[str] = Field(None, max_length=50)
    expiry_date: Optional[datetime] = None
    is_active: Optional[bool] = None


class InventoryItemInDBBase(InventoryItemBase):
    """Base schema for inventory item data in database."""

    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class InventoryItem(InventoryItemInDBBase):
    """Schema for inventory item data returned to clients."""

    warehouse: Optional[Warehouse] = None


class StockMovementType(str, Enum):
    """Stock movement type enumeration."""

    IN = "in"
    OUT = "out"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"


class StockMovementBase(BaseModel):
    """Base stock movement schema."""

    inventory_item_id: int
    warehouse_id: int
    movement_type: StockMovementType
    quantity: int
    reference_type: Optional[str] = Field(None, max_length=50)
    reference_id: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    unit_cost: Optional[float] = None
    total_value: Optional[float] = None


class StockMovementCreate(StockMovementBase):
    """Schema for creating a stock movement."""


class StockMovementInDBBase(StockMovementBase):
    """Base schema for stock movement data in database."""

    id: Optional[int] = None
    previous_quantity: Optional[int] = None
    new_quantity: Optional[int] = None
    performed_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StockMovement(StockMovementInDBBase):
    """Schema for stock movement data returned to clients."""


class StockReservationBase(BaseModel):
    """Base stock reservation schema."""

    inventory_item_id: int
    order_id: Optional[str] = Field(None, max_length=100)
    quantity: int
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None


class StockReservationCreate(StockReservationBase):
    """Schema for creating a stock reservation."""

    reserved_at: Optional[datetime] = None


class StockReservationUpdate(BaseModel):
    """Schema for updating a stock reservation."""

    quantity: Optional[int] = None
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class StockReservationInDBBase(StockReservationBase):
    """Base schema for stock reservation data in database."""

    id: Optional[int] = None
    reserved_at: Optional[datetime] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StockReservation(StockReservationInDBBase):
    """Schema for stock reservation data returned to clients."""


class StockTransferStatus(str, Enum):
    """Stock transfer status enumeration."""

    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class StockTransferBase(BaseModel):
    """Base stock transfer schema."""

    from_warehouse_id: int
    to_warehouse_id: int
    inventory_item_id: int
    quantity: int
    expected_arrival_date: Optional[datetime] = None
    tracking_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class StockTransferCreate(StockTransferBase):
    """Schema for creating a stock transfer."""

    transfer_date: Optional[datetime] = None


class StockTransferUpdate(BaseModel):
    """Schema for updating a stock transfer."""

    quantity: Optional[int] = None
    expected_arrival_date: Optional[datetime] = None
    tracking_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    status: Optional[StockTransferStatus] = None
    approved_by: Optional[int] = None


class StockTransferInDBBase(StockTransferBase):
    """Base schema for stock transfer data in database."""

    id: Optional[int] = None
    transfer_number: Optional[str] = None
    transfer_date: Optional[datetime] = None
    status: StockTransferStatus = StockTransferStatus.PENDING
    created_by: Optional[int] = None
    approved_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StockTransfer(StockTransferInDBBase):
    """Schema for stock transfer data returned to clients."""

    from_warehouse: Optional[Warehouse] = None
    to_warehouse: Optional[Warehouse] = None


# Response schemas
class InventorySummary(BaseModel):
    """Summary of inventory status."""

    total_items: int
    total_value: float
    low_stock_items: int
    out_of_stock_items: int
    items_to_reorder: int


class StockLevel(BaseModel):
    """Stock level information."""

    inventory_item_id: int
    product_id: int
    warehouse_id: int
    warehouse_name: str
    current_stock: int
    reserved_stock: int
    available_stock: int
    minimum_stock: int
    reorder_point: int
    status: str  # in_stock, low_stock, out_of_stock, overstock
