"""Request models for product offer operations."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class OfferStatus(str, Enum):
    """Status of a product offer."""

    NEW = "new"
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"


class PriceType(str, Enum):
    """Type of price for the offer."""

    RETAIL = "retail"
    SALE = "sale"
    WHOLESALE = "wholesale"


class ProductOfferBase(BaseModel):
    """Base model for product offer operations."""

    product_id: str = Field(
        ...,
        description="Unique identifier of the product in your system",
    )
    product_name: str = Field(..., max_length=255, description="Name of the product")
    part_number: Optional[str] = Field(
        None,
        max_length=100,
        description="Manufacturer part number",
    )
    description: Optional[str] = Field(None, description="Detailed product description")
    brand_id: int = Field(..., description="eMAG brand ID")
    brand_name: str = Field(..., max_length=100, description="Brand name")
    category_id: int = Field(..., description="eMAG category ID")
    images: List[str] = Field(default_factory=list, description="List of image URLs")
    status: OfferStatus = Field(default=OfferStatus.NEW, description="Offer status")

    class Config:
        """Pydantic config."""

        use_enum_values = True
        json_encoders = {OfferStatus: lambda v: v.value}


class ProductOfferCreate(ProductOfferBase):
    """Model for creating a new product offer."""

    price: float = Field(..., gt=0, description="Product price")
    sale_price: Optional[float] = Field(
        None,
        gt=0,
        description="Sale price if applicable",
    )
    vat_rate: float = Field(
        ...,
        gt=0,
        le=100,
        description="VAT rate as a percentage (e.g., 19.0)",
    )
    stock: int = Field(..., ge=0, description="Available stock quantity")
    handling_time: int = Field(..., ge=1, le=30, description="Handling time in days")
    warranty: int = Field(default=24, ge=0, description="Warranty period in months")

    @field_validator("sale_price")
    def validate_sale_price(cls, v, values):
        """Validate that sale price is less than regular price."""
        if v is not None and "price" in values.data and v >= values.data["price"]:
            raise ValueError("Sale price must be less than regular price")
        return v


class ProductOfferUpdate(BaseModel):
    """Model for updating an existing product offer."""

    price: Optional[float] = Field(None, gt=0, description="Updated price")
    sale_price: Optional[float] = Field(None, ge=0, description="Updated sale price")
    stock: Optional[int] = Field(None, ge=0, description="Updated stock quantity")
    status: Optional[OfferStatus] = Field(None, description="Updated status")
    handling_time: Optional[int] = Field(
        None,
        ge=1,
        le=30,
        description="Updated handling time",
    )

    class Config:
        """Pydantic config."""

        use_enum_values = True

    @field_validator("sale_price")
    def validate_sale_price(cls, v, values):
        """Validate that sale price is less than regular price."""
        if v is not None and "price" in values.data and v >= values.data["price"]:
            raise ValueError("Sale price must be less than regular price")
        return v


class ProductOfferBulkUpdate(BaseModel):
    """Model for bulk updating multiple product offers."""

    offers: List[Dict[str, Any]] = Field(
        ...,
        max_items=50,
        description="List of offer updates, max 50 items per request",
    )

    @field_validator("offers")
    def validate_offers(cls, v):
        """Validate that bulk update contains at most 50 items."""
        if len(v) > 50:
            raise ValueError("Bulk update is limited to 50 items per request")
        return v


class ProductOfferFilter(BaseModel):
    """Filter criteria for querying product offers."""

    status: Optional[OfferStatus] = None
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    in_stock: Optional[bool] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None

    class Config:
        """Pydantic config."""

        use_enum_values = True
