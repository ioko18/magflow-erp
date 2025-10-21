"""Pydantic schemas for supplier product management (1688.com integration)."""

from datetime import datetime

from pydantic import BaseModel, Field


class SupplierProductBase(BaseModel):
    """Base schema for supplier product (1688.com mapping)."""

    supplier_product_name: str = Field(
        ...,
        max_length=1000,
        description="Product name from 1688.com",
    )
    supplier_product_url: str = Field(
        ...,
        max_length=1000,
        description="1688.com product URL",
    )
    supplier_image_url: str = Field(
        ...,
        max_length=1000,
        description="Product image URL",
    )
    supplier_price: float = Field(
        ...,
        gt=0,
        description="Price in supplier currency",
    )
    supplier_currency: str = Field(
        default="CNY",
        max_length=3,
        description="Currency code",
    )


class SupplierProductCreate(SupplierProductBase):
    """Schema for creating a supplier product mapping."""

    supplier_id: int = Field(..., description="Supplier ID")
    local_product_id: int | None = Field(
        None,
        description="Local product ID if matched",
    )
    supplier_product_chinese_name: str | None = Field(
        None,
        max_length=500,
        description="Chinese name",
    )
    supplier_product_specification: str | None = Field(
        None,
        max_length=1000,
        description="Product specifications",
    )
    confidence_score: float = Field(
        default=0.0,
        ge=0,
        le=1,
        description="Matching confidence (0-1)",
    )
    manual_confirmed: bool = Field(
        default=False,
        description="Manual confirmation status",
    )
    is_active: bool = Field(
        default=True,
        description="Active status",
    )
    import_source: str | None = Field(
        default="manual",
        max_length=50,
        description="Import source",
    )


class SupplierProductUpdate(BaseModel):
    """Schema for updating a supplier product - all fields optional."""

    supplier_product_name: str | None = Field(None, max_length=1000)
    supplier_product_chinese_name: str | None = Field(None, max_length=500)
    supplier_product_specification: str | None = Field(None, max_length=1000)
    supplier_product_url: str | None = Field(None, max_length=1000)
    supplier_image_url: str | None = Field(None, max_length=1000)
    supplier_price: float | None = Field(None, gt=0)
    supplier_currency: str | None = Field(None, max_length=3)
    local_product_id: int | None = None
    confidence_score: float | None = Field(None, ge=0, le=1)
    manual_confirmed: bool | None = None
    is_active: bool | None = None


class LocalProductInfo(BaseModel):
    """Embedded local product information."""

    id: int
    name: str
    sku: str
    brand: str | None = None
    image_url: str | None = None
    chinese_name: str | None = None
    category: str | None = None

    class Config:
        from_attributes = True


class SupplierProductResponse(SupplierProductBase):
    """Schema for supplier product response."""

    id: int
    supplier_id: int
    supplier_name: str | None = None
    supplier_product_chinese_name: str | None = None
    supplier_product_specification: str | None = None
    local_product_id: int | None = None
    local_product: LocalProductInfo | None = None
    confidence_score: float = Field(default=0.0, ge=0, le=1)
    manual_confirmed: bool = Field(default=False)
    is_active: bool = Field(default=True)
    import_source: str | None = None
    last_price_update: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class SupplierProductListResponse(BaseModel):
    """Schema for paginated supplier product list response."""

    products: list[SupplierProductResponse]
    total: int
    skip: int
    limit: int
    has_more: bool


class SupplierProductStatistics(BaseModel):
    """Schema for supplier product statistics."""

    total_products: int
    confirmed_products: int
    pending_products: int
    active_products: int
    average_confidence: float
    confirmation_rate: float


class ChineseNameUpdate(BaseModel):
    """Schema for updating Chinese name."""

    chinese_name: str = Field(
        ...,
        max_length=500,
        description="Chinese name to set",
    )


class SpecificationUpdate(BaseModel):
    """Schema for updating specification."""

    specification: str = Field(
        ...,
        max_length=1000,
        description="Specification to set",
    )


class URLUpdate(BaseModel):
    """Schema for updating product URL."""

    url: str = Field(
        ...,
        max_length=1000,
        description="Product URL to set",
    )


class PriceUpdate(BaseModel):
    """Schema for updating product price."""

    price: float = Field(
        ...,
        gt=0,
        description="New price",
    )
    currency: str | None = Field(
        None,
        max_length=3,
        description="Currency code",
    )


class SupplierChange(BaseModel):
    """Schema for changing supplier."""

    new_supplier_id: int = Field(..., description="New supplier ID")


class MatchingUpdate(BaseModel):
    """Schema for updating product matching."""

    local_product_id: int | None = Field(
        None,
        description="Local product ID to match",
    )
    confidence_score: float | None = Field(
        None,
        ge=0,
        le=1,
        description="Confidence score",
    )
    manual_confirmed: bool | None = Field(
        None,
        description="Manual confirmation status",
    )
