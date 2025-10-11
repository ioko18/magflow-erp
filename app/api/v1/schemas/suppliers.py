"""Pydantic schemas for supplier management API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SupplierBase(BaseModel):
    """Base schema for supplier data."""

    name: str = Field(..., min_length=1, max_length=255)
    country: str = Field(default="China", min_length=2, max_length=100)
    contact_person: str | None = Field(None, max_length=255)
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    website: str | None = Field(None, max_length=500)

    lead_time_days: int = Field(default=30, ge=1, le=365)
    min_order_value: float = Field(default=0.0, ge=0)
    min_order_qty: int = Field(default=1, ge=1)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    payment_terms: str = Field(default="30 days", max_length=255)

    specializations: dict[str, Any] | None = None
    product_categories: list[str] | None = None

    notes: str | None = None
    tags: list[str] | None = None


class SupplierCreate(SupplierBase):
    """Schema for creating a new supplier."""

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if v and "@" not in v:
            raise ValueError("Invalid email format")
        return v


class SupplierUpdate(BaseModel):
    """Schema for updating supplier data."""

    name: str | None = Field(None, min_length=1, max_length=255)
    country: str | None = Field(None, min_length=2, max_length=100)
    contact_person: str | None = Field(None, max_length=255)
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    website: str | None = Field(None, max_length=500)

    lead_time_days: int | None = Field(None, ge=1, le=365)
    min_order_value: float | None = Field(None, ge=0)
    min_order_qty: int | None = Field(None, ge=1)
    currency: str | None = Field(None, min_length=3, max_length=3)
    payment_terms: str | None = Field(None, max_length=255)

    specializations: dict[str, Any] | None = None
    product_categories: list[str] | None = None

    rating: float | None = Field(None, ge=0.0, le=5.0)
    is_active: bool | None = None
    notes: str | None = None
    tags: list[str] | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if v and "@" not in v:
            raise ValueError("Invalid email format")
        return v


class SupplierResponse(SupplierBase):
    """Schema for supplier response data."""

    id: int
    rating: float = 5.0
    total_orders: int = 0
    on_time_delivery_rate: float = 0.0
    quality_score: float = 5.0
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class SupplierProductBase(BaseModel):
    """Base schema for supplier-product mappings."""

    supplier_product_name: str = Field(..., max_length=1000)
    supplier_product_url: str = Field(..., max_length=1000)
    supplier_image_url: str = Field(..., max_length=1000)
    supplier_price: float = Field(..., ge=0)
    supplier_currency: str = Field(default="CNY", min_length=3, max_length=3)
    supplier_specifications: dict[str, Any] | None = None

    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    manual_confirmed: bool = False


class SupplierProductCreate(SupplierProductBase):
    """Schema for creating supplier-product mappings."""

    local_product_id: int


class SupplierProductResponse(SupplierProductBase):
    """Schema for supplier-product response data."""

    id: int
    supplier_id: int
    local_product_id: int
    confirmed_by: int | None = None
    confirmed_at: datetime | None = None
    is_active: bool = True
    last_price_update: datetime | None = None
    price_history: list[dict[str, Any]] | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class PurchaseOrderBase(BaseModel):
    """Base schema for purchase orders."""

    status: str = Field(
        default="draft", regex="^(draft|sent|confirmed|shipped|delivered|cancelled)$"
    )
    expected_delivery_date: datetime | None = None
    total_value: float = Field(default=0.0, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    exchange_rate: float = Field(default=1.0, ge=0)
    order_items: list[dict[str, Any]] | None = None
    supplier_confirmation: str | None = Field(None, max_length=1000)
    internal_notes: str | None = None
    attachments: list[str] | None = None


class PurchaseOrderCreate(PurchaseOrderBase):
    """Schema for creating purchase orders."""

    supplier_id: int


class PurchaseOrderResponse(PurchaseOrderBase):
    """Schema for purchase order response data."""

    id: int
    order_number: str
    supplier_id: int
    order_date: datetime
    actual_delivery_date: datetime | None = None
    quality_check_passed: bool | None = None
    quality_notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class PurchaseOrderItemBase(BaseModel):
    """Base schema for purchase order items."""

    quantity_ordered: int = Field(..., gt=0)
    quantity_received: int | None = Field(None, ge=0)
    unit_price: float = Field(..., ge=0)
    total_price: float = Field(..., ge=0)
    expected_delivery_date: datetime | None = None
    actual_delivery_date: datetime | None = None
    quality_status: str = Field(
        default="pending", regex="^(pending|passed|failed|partial)$"
    )
    quality_notes: str | None = None


class PurchaseOrderItemCreate(PurchaseOrderItemBase):
    """Schema for creating purchase order items."""

    supplier_product_id: int | None = None
    local_product_id: int


class PurchaseOrderItemResponse(PurchaseOrderItemBase):
    """Schema for purchase order item response data."""

    id: int
    purchase_order_id: int
    supplier_product_id: int | None = None
    local_product_id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class SupplierPerformanceBase(BaseModel):
    """Base schema for supplier performance records."""

    metric_type: str = Field(..., min_length=1, max_length=50)
    metric_value: float = Field(...)
    order_id: int | None = None
    notes: str | None = Field(None, max_length=500)


class SupplierPerformanceResponse(SupplierPerformanceBase):
    """Schema for supplier performance response data."""

    id: int
    supplier_id: int
    created_at: datetime | None = None

    class Config:
        from_attributes = True


# Analytics and reporting schemas
class SupplierAnalyticsResponse(BaseModel):
    """Schema for supplier analytics data."""

    supplier_id: int
    total_orders: int
    total_value: float
    avg_order_value: float
    on_time_delivery_rate: float
    avg_lead_time: float
    quality_score: float
    last_order_date: datetime | None = None
    performance_trend: list[dict[str, Any]]

    class Config:
        from_attributes = True


class SupplierComparisonResponse(BaseModel):
    """Schema for comparing suppliers."""

    product_id: int
    suppliers: list[dict[str, Any]]
    best_supplier: dict[str, Any]
    price_range: dict[str, float]
    delivery_time_range: dict[str, int]

    class Config:
        from_attributes = True
