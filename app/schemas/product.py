from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


class CategorySummary(BaseModel):
    id: int = Field(..., description="Category identifier")
    name: str = Field(..., description="Category name")

    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    """Base product schema with common fields."""

    # Basic Information
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    sku: str = Field(
        ..., min_length=1, max_length=100, description="Stock Keeping Unit (unique)"
    )
    description: Optional[str] = Field(None, description="Product description")
    short_description: Optional[str] = Field(None, max_length=500, description="Short product description")
    brand: Optional[str] = Field(None, max_length=100, description="Product brand")
    manufacturer: Optional[str] = Field(None, max_length=100, description="Product manufacturer")

    # Pricing
    base_price: Optional[Decimal] = Field(
        default=None,
        ge=Decimal(0),
        le=Decimal("999999.99"),
        description="Product base price",
        validation_alias=AliasChoices("base_price", "price"),
    )
    recommended_price: Optional[Decimal] = Field(
        default=None,
        ge=Decimal(0),
        le=Decimal("999999.99"),
        description="Recommended retail price",
    )
    currency: Optional[str] = Field(
        default="RON",
        min_length=3,
        max_length=3,
        description="ISO currency code",
    )

    # Physical Properties
    weight_kg: Optional[Decimal] = Field(
        default=None,
        ge=Decimal(0),
        le=Decimal("9999.99"),
        description="Product weight in kilograms",
    )
    length_cm: Optional[Decimal] = Field(
        default=None,
        ge=Decimal(0),
        le=Decimal("9999.99"),
        description="Product length in centimeters",
    )
    width_cm: Optional[Decimal] = Field(
        default=None,
        ge=Decimal(0),
        le=Decimal("9999.99"),
        description="Product width in centimeters",
    )
    height_cm: Optional[Decimal] = Field(
        default=None,
        ge=Decimal(0),
        le=Decimal("9999.99"),
        description="Product height in centimeters",
    )

    # Status
    is_active: Optional[bool] = Field(True, description="Whether the product is active")
    is_discontinued: Optional[bool] = Field(False, description="Whether the product is discontinued")

    # eMAG Specific Fields
    ean: Optional[str] = Field(None, max_length=18, description="European Article Number")
    emag_category_id: Optional[int] = Field(None, description="eMAG category ID")
    emag_brand_id: Optional[int] = Field(None, description="eMAG brand ID")
    emag_warranty_months: Optional[int] = Field(
        None,
        ge=0,
        le=240,
        description="Warranty period in months",
    )
    emag_part_number_key: Optional[str] = Field(
        None,
        max_length=50,
        description="eMAG unique product identifier",
    )

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> str:
        """Validate currency code."""
        if v is None:
            return "RON"
        return v.upper()

    @field_validator('sku')
    @classmethod
    def validate_sku(cls, v: str) -> str:
        """Validate SKU format."""
        if not v or not v.strip():
            raise ValueError("SKU cannot be empty")
        # Allow alphanumeric, hyphens, and underscores
        if not all(c.isalnum() or c in '-_' for c in v):
            raise ValueError("SKU can only contain alphanumeric characters, hyphens, and underscores")
        return v.strip().upper()


class ProductCreate(ProductBase):
    """Schema for creating a new product."""

    category_ids: List[int] = Field(
        default_factory=list,
        description="Categories to attach to the product",
    )
    characteristics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Structured product characteristics (key-value pairs)",
    )
    images: Optional[List[str]] = Field(
        default_factory=list,
        description="Product image URLs",
    )
    attachments: Optional[List[str]] = Field(
        default_factory=list,
        description="Product attachment URLs (manuals, certificates, etc.)",
    )

    # Auto-publish to eMAG option
    auto_publish_emag: Optional[bool] = Field(
        default=False,
        description="Automatically publish to eMAG after creation",
    )

    @model_validator(mode='after')
    def validate_emag_fields(self) -> 'ProductCreate':
        """Validate eMAG-specific fields if auto-publish is enabled."""
        if self.auto_publish_emag:
            if not self.emag_category_id:
                raise ValueError("eMAG category ID is required for auto-publish")
            if not self.base_price or self.base_price <= 0:
                raise ValueError("Valid base price is required for auto-publish")
            if not self.description or len(self.description.strip()) < 10:
                raise ValueError("Description (min 10 chars) is required for auto-publish")
        return self


class ProductUpdate(BaseModel):
    """Schema for updating an existing product."""

    # Basic Information
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Product name",
    )
    sku: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Stock Keeping Unit",
    )
    description: Optional[str] = Field(None, description="Product description")
    short_description: Optional[str] = Field(None, max_length=500, description="Short product description")
    brand: Optional[str] = Field(None, max_length=100, description="Product brand")
    manufacturer: Optional[str] = Field(None, max_length=100, description="Product manufacturer")

    # Pricing
    base_price: Optional[Decimal] = Field(
        default=None,
        ge=Decimal(0),
        le=Decimal("999999.99"),
        description="Product base price",
        validation_alias=AliasChoices("base_price", "price"),
    )
    recommended_price: Optional[Decimal] = Field(
        default=None,
        ge=Decimal(0),
        le=Decimal("999999.99"),
        description="Recommended retail price",
    )
    currency: Optional[str] = Field(
        None,
        min_length=3,
        max_length=3,
        description="ISO currency code",
    )

    # Physical Properties
    weight_kg: Optional[Decimal] = Field(None, ge=Decimal(0), description="Product weight in kilograms")
    length_cm: Optional[Decimal] = Field(None, ge=Decimal(0), description="Product length in centimeters")
    width_cm: Optional[Decimal] = Field(None, ge=Decimal(0), description="Product width in centimeters")
    height_cm: Optional[Decimal] = Field(None, ge=Decimal(0), description="Product height in centimeters")

    # Status
    is_active: Optional[bool] = Field(None, description="Whether the product is active")
    is_discontinued: Optional[bool] = Field(None, description="Whether the product is discontinued")

    # eMAG Specific
    ean: Optional[str] = Field(None, max_length=18, description="European Article Number")
    emag_category_id: Optional[int] = Field(None, description="eMAG category ID")
    emag_brand_id: Optional[int] = Field(None, description="eMAG brand ID")
    emag_warranty_months: Optional[int] = Field(None, ge=0, le=240, description="Warranty period in months")

    # Metadata
    category_ids: Optional[List[int]] = Field(None, description="Categories to attach to the product")
    characteristics: Optional[Dict[str, Any]] = Field(None, description="Product characteristics")
    images: Optional[List[str]] = Field(None, description="Product image URLs")
    attachments: Optional[List[str]] = Field(None, description="Product attachment URLs")

    # Sync to eMAG option
    sync_to_emag: Optional[bool] = Field(
        default=False,
        description="Sync changes to eMAG after update",
    )

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        """Validate currency code."""
        if v is not None:
            return v.upper()
        return v

    @field_validator('sku')
    @classmethod
    def validate_sku(cls, v: Optional[str]) -> Optional[str]:
        """Validate SKU format."""
        if v is not None:
            if not v.strip():
                raise ValueError("SKU cannot be empty")
            if not all(c.isalnum() or c in '-_' for c in v):
                raise ValueError("SKU can only contain alphanumeric characters, hyphens, and underscores")
            return v.strip().upper()
        return v


class ProductResponse(BaseModel):
    """Schema for product response."""

    id: int
    name: str
    sku: str
    description: Optional[str] = None
    short_description: Optional[str] = None
    brand: Optional[str] = None
    manufacturer: Optional[str] = None

    # Pricing
    base_price: Optional[Decimal] = Field(
        default=None,
        description="Product base price",
        validation_alias=AliasChoices("base_price", "price"),
    )
    recommended_price: Optional[Decimal] = None
    currency: Optional[str] = Field(default="RON", description="ISO currency code")

    # Physical Properties
    weight_kg: Optional[Decimal] = None
    length_cm: Optional[Decimal] = None
    width_cm: Optional[Decimal] = None
    height_cm: Optional[Decimal] = None

    # Status
    is_active: bool = Field(..., description="Whether the product is active")
    is_discontinued: bool = Field(default=False, description="Whether the product is discontinued")

    # eMAG Fields
    ean: Optional[str] = None
    emag_category_id: Optional[int] = None
    emag_brand_id: Optional[int] = None
    emag_warranty_months: Optional[int] = None
    emag_part_number_key: Optional[str] = None

    # Metadata
    characteristics: Optional[Dict[str, Any]] = None
    images: Optional[List[str]] = None
    attachments: Optional[List[str]] = None

    # Relationships
    categories: List[CategorySummary] = Field(
        default_factory=list,
        description="Associated categories",
    )

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ProductListResponse(BaseModel):
    """Schema for paginated product list response."""

    products: List[ProductResponse]
    total: int
    limit: int
    offset: int


class ProductBulkCreate(BaseModel):
    """Schema for bulk product creation."""

    products: List[ProductCreate] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of products to create (max 100)",
    )


class ProductBulkCreateResponse(BaseModel):
    """Schema for bulk product creation response."""

    created: List[ProductResponse] = Field(default_factory=list, description="Successfully created products")
    failed: List[Dict[str, Any]] = Field(default_factory=list, description="Failed products with error messages")
    total_created: int = Field(default=0, description="Total number of products created")
    total_failed: int = Field(default=0, description="Total number of products that failed")


class ProductValidationResult(BaseModel):
    """Schema for product validation result."""

    is_valid: bool = Field(..., description="Whether the product is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    emag_ready: bool = Field(default=False, description="Whether the product is ready for eMAG")
    missing_fields: List[str] = Field(default_factory=list, description="Missing required fields for eMAG")
