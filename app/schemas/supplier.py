"""Pydantic schemas for supplier management."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class CurrencyEnum(str, Enum):
    """Supported currencies."""

    USD = "USD"
    CNY = "CNY"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"


class SupplierBase(BaseModel):
    """Base supplier schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Supplier name")
    country: str = Field(
        default="China", max_length=100, description="Supplier country"
    )
    contact_person: str | None = Field(
        None, max_length=255, description="Contact person name"
    )
    email: EmailStr | None = Field(None, description="Contact email")
    phone: str | None = Field(None, max_length=50, description="Contact phone")
    website: str | None = Field(None, max_length=500, description="Supplier website")

    lead_time_days: int = Field(
        default=30, ge=1, le=365, description="Lead time in days"
    )
    min_order_value: float = Field(default=0.0, ge=0, description="Minimum order value")
    min_order_qty: int = Field(default=1, ge=1, description="Minimum order quantity")
    currency: CurrencyEnum = Field(
        default=CurrencyEnum.USD, description="Currency for pricing"
    )
    payment_terms: str = Field(
        default="30 days", max_length=255, description="Payment terms"
    )

    notes: str | None = Field(None, description="Additional notes")
    is_active: bool = Field(default=True, description="Whether supplier is active")


class SupplierCreate(SupplierBase):
    """Schema for creating a new supplier."""

    pass


class SupplierUpdate(BaseModel):
    """Schema for updating a supplier - all fields optional."""

    name: str | None = Field(None, min_length=1, max_length=255)
    country: str | None = Field(None, max_length=100)
    contact_person: str | None = Field(None, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    website: str | None = Field(None, max_length=500)

    lead_time_days: int | None = Field(None, ge=1, le=365)
    min_order_value: float | None = Field(None, ge=0)
    min_order_qty: int | None = Field(None, ge=1)
    currency: CurrencyEnum | None = None
    payment_terms: str | None = Field(None, max_length=255)

    notes: str | None = None
    is_active: bool | None = None


class SupplierResponse(SupplierBase):
    """Schema for supplier response."""

    id: int
    rating: float = Field(default=5.0, ge=0, le=5)
    total_orders: int = Field(default=0, ge=0)
    on_time_delivery_rate: float = Field(default=0.0, ge=0, le=100)
    quality_score: float = Field(default=5.0, ge=0, le=5)
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class SupplierListResponse(BaseModel):
    """Schema for paginated supplier list response."""

    suppliers: list[SupplierResponse]
    total: int
    skip: int
    limit: int
    has_more: bool


class SupplierStatistics(BaseModel):
    """Schema for supplier statistics."""

    total_suppliers: int
    active_suppliers: int
    suppliers_by_country: dict
    average_rating: float
    chinese_suppliers: int
    international_suppliers: int
